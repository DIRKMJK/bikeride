"""Download hourly weather data from oikolab"""

import json
import requests
import pandas as pd

URL = 'https://api.oikolab.com/weather'
DEFAULT_VARS = [
    'temperature',
    'wind_speed',
    'wind_gust',
    'wind_direction',
    'total_precipitation',
    'surface_pressure',
]


def get_oikolab(lat, lon, start, end, api_key, vars):
    """Download hourly weather data from oikolab"""
    if not vars:
        vars = DEFAULT_VARS
    r = requests.get(
        URL,
        params={
            'param': vars,
            'start': start,
            'end': end,
            'lat': lat,
            'lon': lon,
            'api-key': api_key
        }
    )
    weather_data = json.loads(r.json()['data'])
    df = pd.DataFrame(
        index=pd.to_datetime(weather_data['index'], unit='s'),
        data=weather_data['data'],
        columns=weather_data['columns']
    )
    df = df.rename(columns={
        'temperature (degC)': 'temperature',
        'wind_direction (deg)': 'wind_direction',
        'wind_speed (m/s)': 'wind_speed'
    })
    df['date'] = df.index.map(lambda x: x.strftime('%Y%m%d'))
    df['hour'] = df.index.map(lambda x: x.strftime('%H'))
    return df
