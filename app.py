from flask import Flask, render_template
from services.loadDataFirebaseServices import push_data_to_firebase, get_weather_data
from models.rain_model import get_24h_forecast, get_7day_forecast, get_weather_summary
from config.server_config import FIREBASE_PATHS
import threading
import time
import requests
import os
from datetime import datetime
import logging
from tensorflow.keras.models import load_model
from models.rain_model import get_24h_forecast as rain_24h, get_7day_forecast as rain_7d
from models.temp_humidity_model import forecast_24h as temp_24h, forecast_7d as temp_7d
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
model_24h = load_model("D:\\SERVER_DBTT\\best_model.keras")
model_7d = load_model("D:\\SERVER_DBTT\\best_model_7d.keras")

def du_bao(data):
    print("Bắt đầu dự báo")

    temp_forecast_24h = temp_24h(model_24h,data)
    temp_forecast_7d = temp_7d(model_7d,data)
    rain_forecast_24h = rain_24h(data)
    rain_forecast_7d = rain_7d(data)

    # Gộp dữ liệu 
    rain_24h_dict = {
        datetime.strptime(entry['time'], '%Y-%m-%d %H:%M:%S'): entry['probability']
        for entry in rain_forecast_24h
    }

    merged_24h = []
    for entry in temp_forecast_24h:
        time = entry['time']
        rain_prob = rain_24h_dict.get(time, 0.0)
        merged_24h.append({
            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'temp': round(entry['temp'], 2),
            'rain_probability': round(rain_prob, 1)
        })

    rain_7d_dict = {
        entry['date']: entry['max_probability']
        for entry in rain_forecast_7d
    }

    merged_7d = []
    for entry in temp_forecast_7d:
        date = entry['date']
        rain_prob = rain_7d_dict.get(date, 0.0)
        merged_7d.append({
            'date': date,
            'temp_max': entry['temp_max'],
            'temp_min': entry['temp_min'],
            'max_rain_probability': round(rain_prob, 1)
        })
    push_forecast_to_firebase(merged_24h, merged_7d)
    return {
        'forecast_24h': merged_24h,
        'forecast_7d': merged_7d
    }
def push_forecast_to_firebase(merged_24h, merged_7d):
    data_24h = {
        entry['time']: {
            'temp': entry['temp'],
            'rain': entry['rain_probability']
        }
        for entry in merged_24h
    }
    data_7d = {
        entry['date']: {
            'temp_max': entry['temp_max'],
            'temp_min': entry['temp_min'],
            'rain': entry['max_rain_probability']
        }
        for entry in merged_7d
    }
    push_data_to_firebase("weather_24h", data_24h)
    print("Đã đẩy dữ liệu 24h lên Firebase")

    push_data_to_firebase("weather_7d", data_7d)
    print("Đã đẩy dữ liệu 7 ngày lên Firebase")

# hàm dự báo thời tiết với hiển thị chi tiết
# def du_bao():
#     """Chạy dự báo thời tiết"""
#     try:
#         logger.info("🔮 Bắt đầu dự báo...")
#         # dự báo % xảy ra mưa
#         data = get_weather_summary()
                
#         if data and 'error' not in data:
#             gio_mua = len([f for f in data['forecast_24h'] if f.get('prediction') == 'RAIN'])
#             ngay_mua = len([f for f in data['forecast_7days'] if '🌧️' in f.get('weather', '')])
                        
#             logger.info(f"✅ Dự báo xong lúc {datetime.now().strftime('%H:%M:%S')}")
#             logger.info(f"   📊 24h: {gio_mua}/{len(data['forecast_24h'])} giờ có mưa")
#             logger.info(f"   📅 7 ngày: {ngay_mua}/{len(data['forecast_7days'])} ngày mưa")
            
#             # ========== HIỂN THỊ CHI TIẾT DỰ BÁO 24H ==========
#             print("\n" + "="*50)
#             print("🔮 DỰ BÁO 24H TIẾP THEO")
#             print("="*50)
#             print(f"{'Thời gian':<20} {'Xác suất':<10} {'Dự báo'}")
#             print("-"*45)
            
#             for forecast in data['forecast_24h'][:12]:  # Hiển thị 12h đầu
#                 time_str = datetime.strptime(forecast['time'], '%Y-%m-%d %H:%M:%S').strftime('%m/%d %H:%M')
#                 prob = forecast['probability']
#                 pred = "🌧️ Mưa" if forecast['prediction'] == 'RAIN' else "☀️ Khô"
#                 print(f"{time_str:<20} {prob:>5.1f}%     {pred}")
            
#             if len(data['forecast_24h']) > 12:
#                 print(f"... và {len(data['forecast_24h']) - 12} giờ nữa")
            
#             # ========== HIỂN THỊ DỰ BÁO 7 NGÀY ==========
#             print("\n" + "="*50)
#             print("📅 DỰ BÁO 7 NGÀY")
#             print("="*50)
#             print(f"{'Ngày':<15} {'Xác suất':<10} {'Max':<8} {'Thời tiết'}")
#             print("-"*50)
            
#             for forecast in data['forecast_7days']:
#                 date_str = datetime.strptime(forecast['date'][:10], '%Y-%m-%d').strftime('%m/%d (%a)')
#                 avg_prob = forecast['probability']
#                 max_prob = forecast['max_probability']
#                 weather = forecast['weather']
#                 print(f"{date_str:<15} {avg_prob:>5.1f}%     {max_prob:>5.1f}%  {weather}")
            
#             # ========== TỔNG KẾT ==========
#             print("\n" + "="*50)
#             print("📊 TỔNG KẾT")
#             print("="*50)
            
#             # Thống kê 24h
#             probs_24h = [f['probability'] for f in data['forecast_24h']]
#             avg_24h = sum(probs_24h) / len(probs_24h)
#             max_24h = max(probs_24h)
            
#             print(f"📈 24h tiếp theo:")
#             print(f"   Trung bình: {avg_24h:.1f}%")
#             print(f"   Cao nhất: {max_24h:.1f}%")
#             print(f"   Giờ có mưa: {gio_mua}/{len(data['forecast_24h'])}")
            
#             # Thống kê 7 ngày
#             probs_7d = [f['max_probability'] for f in data['forecast_7days']]
#             avg_7d = sum(probs_7d) / len(probs_7d)
#             max_7d = max(probs_7d)
            
#             print(f"📅 7 ngày tới:")
#             print(f"   Trung bình: {avg_7d:.1f}%")
#             print(f"   Cao nhất: {max_7d:.1f}%")
#             print(f"   Ngày mưa: {ngay_mua}/{len(data['forecast_7days'])}")
            
#             # Lời khuyên
#             print(f"\n💡 KHUYẾN NGHỊ:")
#             if max_24h > 70:
#                 print("   🌧️ Khả năng mưa cao - nên mang ô!")
#             elif max_24h > 40:
#                 print("   ⛅ Có thể mưa - chuẩn bị ô phòng khi")
#             else:
#                 print("   ☀️ Thời tiết khô ráo - không cần ô")
                
#             print("="*50 + "\n")
            
#         else:
#             logger.error("❌ Dự báo thất bại")
#             if 'error' in data:
#                 print(f"❌ Lỗi: {data['error']}")
                
#     except Exception as e:
#         logger.error(f"❌ Lỗi dự báo: {e}")
#         print(f"❌ Exception: {e}")

def lap_du_bao():
    """Lặp dự báo mỗi 1 phút"""
    logger.info("Bắt đầu dự báo tự động mỗi 1 phút")
    
    while True:
        data = get_weather_data()
        du_bao(data)
        time.sleep(60)  # Đợi 1 phút
def tu_ping():
    """Tự ping để không ngủ (chỉ trên Render)"""
    if not os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
        return
    
    url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/health"
    logger.info(f"Tự ping mỗi 10 phút đến: {url}")
    
    while True:
        time.sleep(10 * 60)  # Đợi 10 phút
        try:
            res = requests.get(url, timeout=30)
            time_str = datetime.now().strftime('%H:%M:%S')
            if res.status_code == 200:
                logger.info(f"Ping OK: {res.status_code} lúc {time_str}")
            else:
                logger.warning(f"Ping warning: {res.status_code} lúc {time_str}")
        except Exception as e:
            logger.error(f"Ping lỗi: {e}")

# Khởi động các thread nền
threading.Thread(target=lap_du_bao, daemon=True).start()
threading.Thread(target=tu_ping, daemon=True).start()

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/health")
def health():
    return f"OK - {datetime.now().strftime('%H:%M:%S')}"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Khởi động app cổng {port}")
    logger.info("🔮 Dự báo tự động mỗi 1 phút")
    logger.info("🔄 Tự ping mỗi 14 phút (chỉ trên Render)")
    
    app.run(host='0.0.0.0', port=port, debug=False)