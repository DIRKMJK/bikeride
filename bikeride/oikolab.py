"""Download hourly weather data from oikolab"""

import json
import requests
import pandas as pd


URL = 'https://api.oikolab.com/weather'
DEFAULT_VARS = [
    'temperature',
    'wind_speed',
    '10m_wind_gust',
    'wind_direction',
    'total_precipitation',
    'surface_pressure',
]


def format_date(date):
    """Format date string"""
    if date.isnumeric():
        date = f'{date[:4]}-{date[4:6]}-{date[6:]}'
    return date


def get_oikolab(lat, lon, start, end, api_key, variables, freq):
    """Download hourly weather data from oikolab"""
    if not variables:
        variables = DEFAULT_VARS
    r = requests.get(
        URL,
        params={
            'param': variables,
            'start': format_date(start),
            'end': format_date(end),
            'lat': lat,
            'lon': lon,
            'api-key': api_key,
            'freq': freq
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
