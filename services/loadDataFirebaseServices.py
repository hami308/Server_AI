import requests
import pandas as pd
from datetime import datetime
import os
import json
from config.server_config import FIREBASE_PATHS
 # Cấu hình firebase
base_url = os.getenv("FIREBASE_DATABASE_URL", "https://weather2-b2bc4-default-rtdb.firebaseio.com")
auth = os.getenv("FIREBASE_AUTH","MWgOuA7M7wkxdVvHXs25RFTFz6Lj3ARVeeKO7JgA")

def get_weather_data():
    print("Đang lấy dữ liệu từ firebase ...")

    # Lấy dữ liệu từ firebase
    temp_data = requests.get(f"{base_url}{FIREBASE_PATHS['data_temp']}.json?auth={auth}").json() or {}
    humidity_data = requests.get(f"{base_url}{FIREBASE_PATHS['data_humidity']}.json?auth={auth}").json() or {}
    other_data = requests.get(f"{base_url}{FIREBASE_PATHS['data_other']}.json?auth={auth}").json() or {}
    weather_data = requests.get(f"{base_url}{FIREBASE_PATHS['weather_data']}.json?auth={auth}").json() or {}

    # Xử lý trường hợp weather_data là đối tượng đơn
    if isinstance(weather_data, dict) and 'last_update' in weather_data:
        weather_data = {'current': weather_data}

    print(f"Dữ liệu đã lấy về: {len(temp_data)} temp, {len(humidity_data)} humidity, {len(other_data)} other, {len(weather_data)} weather")

    combined = {}

    # Xử lý dữ liệu nhiệt độ
    for key, val in temp_data.items():
        if not isinstance(val, dict) or 'temp' not in val:
            continue
        try:
            ts = key.replace("-temp","")
            dt = datetime.strptime(ts,"%Y%m%d%H%M%S")
            time_key = dt.strftime("%Y%m%d%H")
            combined[time_key] = combined.get(time_key, {})
            combined[time_key].update({
                'YEAR': dt.year, 'MO': dt.month, 'DY': dt.day, 'HR': dt.hour,
                'T2M': val['temp']
            })
        except:
            continue

    # Xử lý dữ liệu độ ẩm
    for key, val in humidity_data.items():
        if not isinstance(val, dict) or 'humidity' not in val:
            continue
        try:
            ts = key.replace("-humidity", "")
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            time_key = dt.strftime("%Y%m%d%H")
            if time_key in combined:
                combined[time_key]['QV2M'] = val['humidity']
        except:
            continue

    # Xử lý dữ liệu khác
    for key, val in other_data.items():
        if not isinstance(val, dict):
            continue
        try:
            ts = key.replace("-other", "")
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            time_key = dt.strftime("%Y%m%d%H")
            if time_key in combined:
                combined[time_key].update({
                    'PRECTOTCORR': val.get('PRECTOTCORR'),
                    'PS': val.get('PS'),
                    'ALLSKY_SFC_PAR_TOT': val.get('ALLSKY_SFC_PAR_TOT')
                })
        except:
            continue

    # Xử lý dữ liệu thời tiết hiện tại
    if isinstance(weather_data, dict):
        for key, val in weather_data.items():
            if not isinstance(val, dict) or 'last_update' not in val:
                continue
            try:
                dt = datetime.strptime(val['last_update'], "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(minute=0, second=0)  # Làm tròn phút giây về 0
                time_key = dt.strftime("%Y%m%d%H")
                
                if time_key not in combined:
                    combined[time_key] = {
                        'YEAR': dt.year, 'MO': dt.month, 'DY': dt.day, 'HR': dt.hour
                    }
                
                # Cập nhật với giá trị từ weather_data
                if 'temperature' in val and isinstance(val['temperature'], (int, float)):
                    combined[time_key]['T2M'] = val['temperature']
                if 'humidity' in val and isinstance(val['humidity'], (int, float)):
                    combined[time_key]['QV2M'] = val['humidity']
                if 'ALLSKY_SFC_PAR_TOT' in val and isinstance(val['ALLSKY_SFC_PAR_TOT'], (int, float)):
                    combined[time_key]['ALLSKY_SFC_PAR_TOT'] = val['ALLSKY_SFC_PAR_TOT']
                if 'PRECTOTCORR' in val and isinstance(val['PRECTOTCORR'], (int, float)):
                    combined[time_key]['PRECTOTCORR'] = val['PRECTOTCORR']
                if 'pressure' in val and isinstance(val['pressure'], (int, float)):
                    combined[time_key]['PS'] = val['pressure'] * 100  # Chuyển đổi hPa sang Pa
            except:
                continue

    # Tạo DataFrame
    records = [data for data in combined.values() if len(data) == 9]
    df = pd.DataFrame(records)
        
    if df.empty:
        print("⚠️ Không có dữ liệu!")
        return df
        
    # Sắp xếp và định thứ tự cột
    df = df.sort_values(['YEAR', 'MO', 'DY', 'HR'])
    column_order = ['YEAR', 'MO', 'DY', 'HR', 'QV2M', 'PRECTOTCORR', 'PS', 'T2M', 'ALLSKY_SFC_PAR_TOT']
    df = df[column_order]
        
    print(f" Trả về {len(df)} records với 9 columns")
    return df
def delete_data_from_firebase( node):
    url = f"{base_url}/{node}.json?auth={auth}"
    resp = requests.delete(url)
    resp.raise_for_status()
    return resp.json()

def push_data_to_firebase( node, data):
    # Xóa dữ liệu cũ trước
    delete_data_from_firebase(node)

    url = f"{base_url}/{node}.json?auth={auth}"
    headers = {'Content-Type': 'application/json'}
    resp = requests.patch(url, data=json.dumps(data), headers=headers)
    resp.raise_for_status()
    return resp.json()