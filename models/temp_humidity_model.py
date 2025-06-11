from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from services.loadDataFirebaseServices import get_weather_data
from sklearn.preprocessing import StandardScaler

def prepare_dataframe(data):
    df_all = data
    if df_all.empty:
        return None

    df_all['thoigian'] = pd.to_datetime(df_all[['YEAR', 'MO', 'DY', 'HR']].rename(
        columns={'YEAR': 'year', 'MO': 'month', 'DY': 'day', 'HR': 'hour'}))
    df_all.set_index('thoigian', inplace=True)

    df_all['hour_sin'] = np.sin(2 * np.pi * df_all.index.hour / 24)
    df_all['hour_cos'] = np.cos(2 * np.pi * df_all.index.hour / 24)
    df_all['month_sin'] = np.sin(2 * np.pi * df_all.index.month / 12)
    df_all['month_cos'] = np.cos(2 * np.pi * df_all.index.month / 12)

    return df_all

def predict_weather(df, model, input_features, output_features, input_steps, output_steps):
    data = df[input_features].values
    if data.shape[0] < input_steps:
        raise ValueError(f"Không đủ {input_steps} giờ dữ liệu")

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data)

    X_input = np.expand_dims(data_scaled[-input_steps:], axis=0)
    y_pred = model.predict(X_input)
    y_pred = y_pred.reshape(output_steps, len(output_features))

    dummy = np.zeros((output_steps, len(input_features)))
    dummy[:, :len(output_features)] = y_pred
    y_pred_inv = scaler.inverse_transform(dummy)[:, :len(output_features)]

    last_time = df.index[-1]
    future_times = [last_time + timedelta(hours=i + 1) for i in range(output_steps)]

    results = {
        time.strftime('%Y-%m-%d %H:%M:%S'): {
            feat: round(float(val), 2)
            for feat, val in zip(output_features, values)
        }
        for time, values in zip(future_times, y_pred_inv)
    }

    return results

def convert_24h_output(prediction_dict):
    forecast = []
    for i, (timestamp, values) in enumerate(prediction_dict.items()):
        date_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        forecast.append({
            'time': date_obj,
            'temp': values['T2M'],
        })
    return forecast

def convert_7d_output(prediction_dict):
    df = pd.DataFrame([
        {"time": datetime.strptime(k, "%Y-%m-%d %H:%M:%S"), "temp": v["T2M"]}
        for k, v in prediction_dict.items()
    ])
    df['date'] = df['time'].dt.strftime("%Y-%m-%d")

    daily = df.groupby("date")["temp"].agg(temp_max='max', temp_min='min').reset_index()

    forecast = []
    for _, row in daily.iterrows():
        forecast.append({
            'date': row['date'],
            'temp_max': round(row['temp_max'], 2),
            'temp_min': round(row['temp_min'], 2)
        })
    return forecast

def forecast_24h(model_24h, data):
    df_all = prepare_dataframe(data)
    if df_all is None or len(df_all) < 72:
        return {"error": "Không đủ dữ liệu cho 24h"}

    input_features = ['T2M', 'QV2M', 'PRECTOTCORR', 'PS', 'ALLSKY_SFC_PAR_TOT',
                      'hour_sin', 'hour_cos', 'month_sin', 'month_cos']
    output_features = ['T2M', 'QV2M']

    df_24h = df_all.tail(72)
    pred_24h = predict_weather(df_24h, model_24h, input_features, output_features, 72, 24)
    return convert_24h_output(pred_24h)


def forecast_7d(model_7d,data):
    df_all = prepare_dataframe(data)
    if df_all is None or len(df_all) < 168:
        return {"error": "Không đủ dữ liệu cho 7 ngày"}

    input_features = ['T2M', 'QV2M', 'PRECTOTCORR', 'PS', 'ALLSKY_SFC_PAR_TOT',
                      'hour_sin', 'hour_cos', 'month_sin', 'month_cos']
    output_features = ['T2M', 'QV2M']

    df_7d = df_all.tail(168)
    pred_7d = predict_weather(df_7d, model_7d, input_features, output_features, 168, 168)
    return convert_7d_output(pred_7d)
