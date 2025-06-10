import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
import warnings
from services.loadDataFirebaseServices import get_weather_data
warnings.filterwarnings('ignore')

class WeatherPredictor:
    def __init__(self, model_path='data/models/rain/rain_model.pkl'):
        """Load model"""
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        self.model = data['model']
        self.scaler = data['scaler']
        self.selector = data['selector']
        self.feature_cols = data['feature_cols']
        self.threshold = data['threshold']
    
    def create_features(self, df):
        """Tạo features"""
        # Time features
        df['hour_sin'] = np.sin(2 * np.pi * df.index.hour / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df.index.hour / 24)
        df['month_sin'] = np.sin(2 * np.pi * df.index.month / 12)
        df['month_cos'] = np.cos(2 * np.pi * df.index.month / 12)
        
        # Pressure & temp changes
        for lag in [1, 3, 6, 12]:
            df[f'pressure_{lag}h'] = df['PS'].diff(lag)
        for lag in [1, 3, 6]:
            df[f'temp_{lag}h'] = df['T2M'].diff(lag)
            df[f'humidity_{lag}h'] = df['QV2M'].diff(lag)
        
        # Atmospheric indicators
        df['dew_point'] = df['T2M'] - ((100 - df['QV2M']) / 5)
        df['temp_dew_diff'] = df['T2M'] - df['dew_point']
        df['is_daytime'] = (df['ALLSKY_SFC_PAR_TOT'] > 10).astype(int)
        
        # Rolling stats & lag
        for param in ['T2M', 'QV2M', 'PS']:
            df[f'{param}_mean_6h'] = df[param].rolling(6).mean()
            df[f'{param}_mean_24h'] = df[param].rolling(24).mean()
            df[f'{param}_lag_24h'] = df[param].shift(24)
        
        return df
    
    def get_firebase_data(self):
        df = get_weather_data()
        
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
    
    def predict_24h(self):
        print("🔮 Dự báo 24h...")
        
        # Lấy dữ liệu
        recent_data = self.get_firebase_data()
        df = self.create_features(recent_data)
        df.dropna(inplace=True)
        
        latest = df.iloc[-1]
        start_time = df.index[-1] + timedelta(hours=1)
        
        predictions = []
        
        for hour in range(24):
            pred_time = start_time + timedelta(hours=hour)
            
            # Update time features
            input_data = latest[self.feature_cols].copy()
            input_data['hour_sin'] = np.sin(2 * np.pi * pred_time.hour / 24)
            input_data['hour_cos'] = np.cos(2 * np.pi * pred_time.hour / 24)
            input_data['month_sin'] = np.sin(2 * np.pi * pred_time.month / 12)
            input_data['month_cos'] = np.cos(2 * np.pi * pred_time.month / 12)
            
            # Predict
            input_scaled = self.scaler.transform([input_data])
            input_selected = self.selector.transform(input_scaled)
            prob = self.model.predict_proba(input_selected)[0, 1]
            
            predictions.append({
                'time': pred_time.strftime('%Y-%m-%d %H:%M:%S'),
                'hour': hour + 1,
                'probability': round(prob * 100, 1),
                'prediction': 'RAIN' if prob > self.threshold else 'No Rain'
            })
        
        print(f"✅ Hoàn thành dự báo 24h: {len(predictions)} giờ")
        return predictions
    
    def predict_7days(self):
        print("📅 Dự báo 7 ngày...")
        
        # Lấy dữ liệu
        recent_data = self.get_firebase_data()
        df = self.create_features(recent_data)
        df.dropna(inplace=True)
        
        latest = df.iloc[-1]
        start_time = df.index[-1] + timedelta(hours=1)
        
        daily_probs = {}
        
        # Predict 168 hours (7 days)
        for hour in range(168):
            pred_time = start_time + timedelta(hours=hour)
            date = pred_time.date()
            
            # Update time features
            input_data = latest[self.feature_cols].copy()
            input_data['hour_sin'] = np.sin(2 * np.pi * pred_time.hour / 24)
            input_data['hour_cos'] = np.cos(2 * np.pi * pred_time.hour / 24)
            input_data['month_sin'] = np.sin(2 * np.pi * pred_time.month / 12)
            input_data['month_cos'] = np.cos(2 * np.pi * pred_time.month / 12)
            
            # Predict
            input_scaled = self.scaler.transform([input_data])
            input_selected = self.selector.transform(input_scaled)
            prob = self.model.predict_proba(input_selected)[0, 1] * 100
            
            if date not in daily_probs:
                daily_probs[date] = []
            daily_probs[date].append(prob)
        
        # Aggregate by day
        forecast = []
        for date, probs in daily_probs.items():
            avg_prob = np.mean(probs)
            max_prob = np.max(probs)
            
            if max_prob > 70:
                weather = "🌧️ Rainy"
            elif max_prob > 40:
                weather = "⛅ Cloudy"
            else:
                weather = "☀️ Sunny"
            # chỉnh sửa dữ liệu in ra màn hình 
            forecast.append({
                'date': date.strftime('%Y-%m-%d (%a)'),
                'probability': round(avg_prob, 1),
                'max_probability': round(max_prob, 1),
                'weather': weather
            })
        
        print(f"✅ Hoàn thành dự báo 7 ngày: {len(forecast)} ngày")
        return forecast

# ============ FUNCTIONS CHO FOLDER KHÁC GỌI ============
#  Lấy dữ liệu dự báo 24h
def get_24h_forecast():
    try:
        predictor = WeatherPredictor()
        return predictor.predict_24h()
    except Exception as e:
        print(f"❌ Lỗi dự báo 24h: {e}")
        return []
# Lấy dữ liệu 7 ngày
def get_7day_forecast():
    try:
        predictor = WeatherPredictor()
        return predictor.predict_7days()
    except Exception as e:
        print(f"❌ Lỗi dự báo 7 ngày: {e}")
        return []
# lấy dữ liệu cả 24h và 7day7day
def get_weather_summary():
    try:
        predictor = WeatherPredictor()
        
        return {
            'forecast_24h': predictor.predict_24h(),
            'forecast_7days': predictor.predict_7days(),
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"❌ Lỗi tổng hợp: {e}")
        return {
            'forecast_24h': [],
            'forecast_7days': [],
            'error': str(e)
        }