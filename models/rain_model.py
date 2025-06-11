import pandas as pd
import numpy as np
import pickle
import joblib
from datetime import datetime, timedelta
import warnings
from services.loadDataFirebaseServices import get_weather_data
warnings.filterwarnings('ignore')

class WeatherPredictor:
    def __init__(self, model_path='data/models/rain/rain_model.pkl'):
        # Load model with joblib (for new optimized models)
        try:
            data = joblib.load(model_path)
        except:
            # Fallback to pickle for old models
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
        
        self.model = data['model']
        self.selected_features = data['selected_features']
        self.threshold = data['threshold']
        self.rain_threshold = data.get('rain_threshold', 0.5)
        
        # Legacy fields for old models (if exists)
        self.scaler = data.get('scaler', None)
        self.selector = data.get('selector', None)
        self.feature_cols = data.get('feature_cols', self.selected_features)
    
    def create_features(self, df):
        """Tạo đặc trưng - BỘ ĐẶC TRƯNG ĐẦY ĐỦ cho model mới"""
        
        # ===== ĐẶC TRƯNG THỜI GIAN =====
        # Biến đổi thời gian thành sin/cos để bắt chu kỳ 24h và 12 tháng
        df['hour_sin'] = np.sin(2 * np.pi * df.index.hour / 24)       # Chu kỳ 24h: 0h=6h=12h=18h
        df['hour_cos'] = np.cos(2 * np.pi * df.index.hour / 24)       # Phân biệt sáng/chiều
        df['month_sin'] = np.sin(2 * np.pi * df.index.month / 12)     # Chu kỳ 12 tháng
        df['month_cos'] = np.cos(2 * np.pi * df.index.month / 12)     # Phân biệt mùa
        
        # ===== MÙA VỤ THỜI TIẾT =====
        # Xác định mùa mưa bão theo khí hậu Đà Nẵng
        df['is_monsoon'] = ((df.index.month >= 9) & (df.index.month <= 12)).astype(int)        # Mùa mưa: Tháng 9-12
        df['is_typhoon_season'] = ((df.index.month >= 6) & (df.index.month <= 11)).astype(int) # Mùa bão: Tháng 6-11

        # ===== ĐẶC TRƯNG ĐỘ ẨM VÀ ÁP SUẤT =====
        # Phân tích xu hướng thay đổi theo nhiều khoảng thời gian
        for lag in [1, 3, 6, 12, 24]:
            # Độ ẩm cao (>85%) là dấu hiệu mưa sắp tới
            df[f'high_humidity_{lag}h'] = (df['QV2M'].shift(lag) > 85).astype(int)
            # Áp suất giảm mạnh (>0.5 hPa) báo hiệu thời tiết xấu
            df[f'pressure_drop_{lag}h'] = (df['PS'].diff(lag) < -0.5).astype(int)
            # Tốc độ thay đổi áp suất
            df[f'pressure_{lag}h'] = df['PS'].diff(lag)
        
        # ===== ĐẶC TRƯNG NHIỆT ĐỘ VÀ ĐỘ ẨM =====
        # Xu hướng thay đổi ngắn hạn (1-12h)
        for lag in [1, 3, 6, 12]:
            df[f'temp_{lag}h'] = df['T2M'].diff(lag)      # Tốc độ thay đổi nhiệt độ
            df[f'humidity_{lag}h'] = df['QV2M'].diff(lag)  # Tốc độ thay đổi độ ẩm
        
        # ===== CHỈ SỐ KHÍ QUYỂN =====
        # Công thức tính điểm sương gần đúng
        df['dew_point'] = df['T2M'] - ((100 - df['QV2M']) / 5)        # Điểm sương (°C)
        df['temp_dew_diff'] = df['T2M'] - df['dew_point']             # Chênh lệch nhiệt độ - điểm sương
        df['is_daytime'] = (df['ALLSKY_SFC_PAR_TOT'] > 10).astype(int) # Ban ngày: bức xạ mặt trời > 10
        
        # ===== ĐIỀU KIỆN THUẬN LỢI CHO MƯA =====
        # Kết hợp 3 yếu tố: độ ẩm cao + nhiệt độ gần điểm sương + áp suất giảm
        df['rain_conditions'] = (
            (df['QV2M'] > 80) &               # Độ ẩm > 80%
            (df['temp_dew_diff'] < 3) &       # Chênh lệch T-Td < 3°C (gần bão hòa)
            (df['PS'].diff(6) < -0.3)         # Áp suất giảm > 0.3 hPa trong 6h
        ).astype(int)
        
        # ===== THỐNG KÊ TRƯỢT =====
        # Trung bình và độ biến động trong các khoảng thời gian khác nhau
        for param in ['T2M', 'QV2M', 'PS']:
            df[f'{param}_mean_6h'] = df[param].rolling(6).mean()   # Trung bình 6h (xu hướng ngắn hạn)
            df[f'{param}_mean_24h'] = df[param].rolling(24).mean() # Trung bình 24h (xu hướng hàng ngày)
            df[f'{param}_std_6h'] = df[param].rolling(6).std()     # Độ biến động 6h (tính ổn định)
        
        # ===== ĐẶC TRƯNG TRỄ =====
        # So sánh với các thời điểm trước đó
        for param in ['T2M', 'QV2M', 'PS']:
            for lag in [12, 24]:
                df[f'{param}_lag_{lag}h'] = df[param].shift(lag)   # Giá trị cách đây 12h, 24h
        
        # ===== ĐẶC TRƯNG TƯƠNG TÁC =====
        # Kết hợp nhiều yếu tố để tạo thông tin mới
        df['temp_humidity_interaction'] = df['T2M'] * df['QV2M']   # Nhiệt độ × Độ ẩm (chỉ số khó chịu)
        df['pressure_temp_interaction'] = df['PS'] * df['T2M']     # Áp suất × Nhiệt độ (ổn định khí quyển)
        
        return df
    
    def get_firebase_data(self,dulieu):
        df = dulieu 
        # Tạo datetime index
        df['datetime'] = pd.to_datetime(
            df['YEAR'].astype(str) + '-' + 
            df['MO'].astype(str).str.zfill(2) + '-' + 
            df['DY'].astype(str).str.zfill(2) + ' ' + 
            df['HR'].astype(str).str.zfill(2) + ':00:00'
        )
        df.set_index('datetime', inplace=True)
        
        # Lấy 72h gần nhất
        recent_data = df.tail(72)[['QV2M', 'PRECTOTCORR', 'PS', 'T2M', 'ALLSKY_SFC_PAR_TOT']]
        return recent_data
    
    def predict_24h(self,dulieu):
        # Lấy dữ liệu
        recent_data = self.get_firebase_data(dulieu)
        df = self.create_features(recent_data)
        df.dropna(inplace=True)
        
        latest = df.iloc[-1]
        start_time = df.index[-1] + timedelta(hours=1)
        
        predictions = []
        
        for hour in range(24):
            pred_time = start_time + timedelta(hours=hour)
            
            # ===== TẠO ĐẶC TRƯNG DỰ BÁO - PHƯƠNG PHÁP TRỰC TIẾP =====
            input_features = {}
            
            # Đặc trưng thời gian (thay đổi theo từng giờ dự báo)
            input_features['hour_sin'] = np.sin(2 * np.pi * pred_time.hour / 24)              # Chu kỳ giờ
            input_features['hour_cos'] = np.cos(2 * np.pi * pred_time.hour / 24)              # Phân biệt AM/PM
            input_features['month_sin'] = np.sin(2 * np.pi * pred_time.month / 12)            # Chu kỳ tháng
            input_features['month_cos'] = np.cos(2 * np.pi * pred_time.month / 12)            # Phân biệt mùa
            input_features['is_monsoon'] = int((pred_time.month >= 9) & (pred_time.month <= 12))      # Mùa mưa
            input_features['is_typhoon_season'] = int((pred_time.month >= 6) & (pred_time.month <= 11)) # Mùa bão
            input_features['is_daytime'] = int(6 <= pred_time.hour <= 18)                     # Ban ngày/đêm
            
            # Sử dụng dữ liệu thời tiết gần nhất làm nền
            for col in self.selected_features:
                if col not in input_features:
                    input_features[col] = latest.get(col, 0)  # Lấy từ dữ liệu cuối hoặc mặc định = 0
            
            # Dự đoán trực tiếp với các đặc trưng đã chọn - TỐI ƯU HÓA
            input_array = np.array([input_features.get(col, 0) for col in self.selected_features]).reshape(1, -1)
            prob = self.model.predict_proba(input_array)[0, 1]  # Xác suất mưa (0-1)
            
            predictions.append({
                'time': pred_time.strftime('%Y-%m-%d %H:%M:%S'),
                'hour': hour + 1,
                'probability': round(prob * 100, 1),
                'prediction': 'RAIN' if prob > self.threshold else 'No Rain'
            })
        
        return predictions
    
    def predict_7days(self,dulieu):        
        # Lấy dữ liệu
        recent_data = self.get_firebase_data(dulieu)
        df = self.create_features(recent_data)
        df.dropna(inplace=True)
        
        start_time = df.index[-1] + timedelta(hours=1)
        daily_probs = {}
        
        # Dự báo 168 giờ (7 ngày × 24 giờ/ngày)
        for hour in range(168):
            pred_time = start_time + timedelta(hours=hour)
            date = pred_time.date()
            
            # Sử dụng dữ liệu nền khác nhau để tạo biến động tự nhiên
            if hour < 24:
                base_data = df.iloc[-1]   # Dữ liệu gần nhất (24h đầu)
            elif hour < 48:
                base_data = df.iloc[-6]   # Cách đây 6h (ngày thứ 2)
            else:
                base_data = df.iloc[-12]  # Cách đây 12h (các ngày sau)
            
            # ===== TẠO ĐẶC TRƯNG DỰ BÁO - PHƯƠNG PHÁP TRỰC TIẾP =====
            input_features = {}
            
            # Đặc trưng thời gian (thay đổi theo từng giờ dự báo)
            input_features['hour_sin'] = np.sin(2 * np.pi * pred_time.hour / 24)
            input_features['hour_cos'] = np.cos(2 * np.pi * pred_time.hour / 24)
            input_features['month_sin'] = np.sin(2 * np.pi * pred_time.month / 12)
            input_features['month_cos'] = np.cos(2 * np.pi * pred_time.month / 12)
            input_features['is_monsoon'] = int((pred_time.month >= 9) & (pred_time.month <= 12))
            input_features['is_typhoon_season'] = int((pred_time.month >= 6) & (pred_time.month <= 11))
            input_features['is_daytime'] = int(6 <= pred_time.hour <= 18)
            
            # Sử dụng dữ liệu nền với biến động nhỏ cho dự báo xa
            for col in self.selected_features:
                if col not in input_features:
                    base_val = base_data.get(col, 0)
                    # Thêm biến động nhỏ cho dự báo xa (>48h) để tránh quá cứng nhắc
                    if hour > 48 and 'mean' in col:
                        variation = np.random.normal(0, 0.02)  # Biến động ±2%
                        input_features[col] = base_val * (1 + variation)
                    else:
                        input_features[col] = base_val
            
            # Dự đoán trực tiếp với các đặc trưng đã chọn - TỐI ƯU HÓA
            input_array = np.array([input_features.get(col, 0) for col in self.selected_features]).reshape(1, -1)
            prob = self.model.predict_proba(input_array)[0, 1] * 100  # Chuyển sang %
            
            if date not in daily_probs:
                daily_probs[date] = []
            daily_probs[date].append(prob)
        
        # Tổng hợp theo ngày
        forecast = []
        for date, probs in daily_probs.items():
            avg_prob = np.mean(probs)  # Xác suất trung bình trong ngày
            max_prob = np.max(probs)   # Xác suất cao nhất trong ngày
            
            # Phân loại thời tiết dựa trên xác suất cao nhất
            if max_prob > 70:
                weather = "🌧️ Rainy"     # Mưa chắc chắn
            elif max_prob > 40:
                weather = "⛅ Cloudy"    # Có thể mưa
            else:
                weather = "☀️ Sunny"     # Nắng ráo
            
            forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'probability': round(avg_prob, 1),
                'max_probability': round(max_prob, 1),
                'weather': weather
            })
        return forecast

# ============ FUNCTIONS CHO FOLDER KHÁC GỌI ============
def get_24h_forecast(dulieu):
    try:
        predictor = WeatherPredictor()
        return predictor.predict_24h(dulieu)
    except Exception as e:
        print(f"❌ Lỗi dự báo 24h: {e}")
        return []

def get_7day_forecast(dulieu):
    try:
        predictor = WeatherPredictor()
        return predictor.predict_7days(dulieu)
    except Exception as e:
        print(f"❌ Lỗi dự báo 7 ngày: {e}")
        return []

def get_weather_summary(dulieu):
    try:
        predictor = WeatherPredictor()
        
        return {
            'forecast_24h': predictor.predict_24h(dulieu),
            'forecast_7days': predictor.predict_7days(dulieu),
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"❌ Lỗi tổng hợp: {e}")
        return {
            'forecast_24h': [],
            'forecast_7days': [],
            'error': str(e)
        }