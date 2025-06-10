from flask import Flask, render_template
from services.loadDataFirebaseServices import get_weather_data
from models.rain_model import get_24h_forecast, get_7day_forecast, get_weather_summary
from config.server_config import FIREBASE_PATHS
import threading
import time
import requests
import os
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# hàm dự bào thời tiết
def du_bao():
    """Chạy dự báo thời tiết"""
    try:
        logger.info("🔮 Bắt đầu dự báo...")
        # dự báo % xảy ra mưa
        data = get_weather_summary()
        
        if data and 'error' not in data:
            gio_mua = len([f for f in data['forecast_24h'] if f.get('prediction') == 'RAIN'])
            ngay_mua = len([f for f in data['forecast_7days'] if '🌧️' in f.get('weather', '')])
            
            logger.info(f"✅ Dự báo xong lúc {datetime.now().strftime('%H:%M:%S')}")
            logger.info(f"   📊 24h: {gio_mua}/{len(data['forecast_24h'])} giờ có mưa")
            logger.info(f"   📅 7 ngày: {ngay_mua}/{len(data['forecast_7days'])} ngày mưa")
        else:
            logger.error("❌ Dự báo thất bại")
    except Exception as e:
        logger.error(f"❌ Lỗi dự báo: {e}")

def lap_du_bao():
    """Lặp dự báo mỗi 1 phút"""
    logger.info("🚀 Bắt đầu dự báo tự động mỗi 1 phút")
    du_bao()  # Chạy lần đầu
    
    while True:
        time.sleep(60)  # Đợi 1 phút
        du_bao()

def tu_ping():
    """Tự ping để không ngủ (chỉ trên Render)"""
    if not os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
        return
    
    url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/health"
    logger.info(f"🔄 Tự ping mỗi 10 phút đến: {url}")
    
    while True:
        time.sleep(10 * 60)  # Đợi 10 phút
        try:
            res = requests.get(url, timeout=30)
            time_str = datetime.now().strftime('%H:%M:%S')
            if res.status_code == 200:
                logger.info(f"✅ Ping OK: {res.status_code} lúc {time_str}")
            else:
                logger.warning(f"⚠️ Ping warning: {res.status_code} lúc {time_str}")
        except Exception as e:
            logger.error(f"❌ Ping lỗi: {e}")

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