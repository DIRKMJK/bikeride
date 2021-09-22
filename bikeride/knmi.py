"""Download hourly weather data from Royal Dutch Meteorological Institute"""

import math
import requests
import pandas as pd


URL = 'https://www.daggegevens.knmi.nl/klimatologie/uurgegevens'
RENAME_COLS = {
    '# STN': 'station',
    'YYYYMMDD': 'date',
    'H': 'hour',
    'DD': 'wind_direction',
    'FH': 'wind_speed_hr',
    'FF': 'wind_speed',
    'FX': 'maximum_wind_gust',
    'T': 'temperature',
    'T10N': '',
    'TD': '',
    'SQ': 'sunshine_duration',
    'Q': '',
    'DR': 'precipitation_duration',
    'RH': 'hourly_precipitation_amount',
    'P': 'air_pressure',
    'VV': '',
    'N': 'cloud_cover',
    'U': 'relative_atmospheric_humidity',
    'WW': '',
    'IX': '',
    'M': 'fog',
    'R': 'rainfall',
    'S': 'snow',
    'O': 'thunder',
    'Y': 'ice_formation',
}
ADJUST = [
    'wind_speed',
    'wind_speed_hr',
    'maximum_wind_gust',
    'temperature',
    'sunshine_duration',
    'precipitation_duration',
    'hourly_precipitation_amount',
]

STATIONS = [
    (209, 4.518, 52.465, 'IJmond'),
    (210, 4.430, 52.171, 'Valkenburg Zh'),
    (215, 4.437, 52.141, 'Voorschoten'),
    (225, 4.555, 52.463, 'IJmuiden'),
    (235, 4.781, 52.928, 'De Kooy'),
    (240, 4.790, 52.318, 'Schiphol'),
    (242, 4.921, 53.241, 'Vlieland'),
    (248, 5.174, 52.634, 'Wijdenes'),
    (249, 4.979, 52.644, 'Berkhout'),
    (251, 5.346, 53.392, 'Hoorn Terschelling'),
    (257, 4.603, 52.506, 'Wijk aan Zee'),
    (258, 5.401, 52.649, 'Houtribdijk'),
    (260, 5.180, 52.100, 'De Bilt'),
    (265, 5.274, 52.130, 'Soesterberg'),
    (267, 5.384, 52.898, 'Stavoren'),
    (269, 5.520, 52.458, 'Lelystad'),
    (270, 5.752, 53.224, 'Leeuwarden'),
    (273, 5.888, 52.703, 'Marknesse'),
    (275, 5.873, 52.056, 'Deelen'),
    (277, 6.200, 53.413, 'Lauwersoog'),
    (278, 6.259, 52.435, 'Heino'),
    (279, 6.574, 52.750, 'Hoogeveen'),
    (280, 6.585, 53.125, 'Eelde'),
    (283, 6.657, 52.069, 'Hupsel'),
    (285, 6.399, 53.575, 'Huibertgat'),
    (286, 7.150, 53.196, 'Nieuw Beerta'),
    (290, 6.891, 52.274, 'Twenthe'),
    (308, 3.379, 51.381, 'Cadzand'),
    (310, 3.596, 51.442, 'Vlissingen'),
    (311, 3.672, 51.379, 'Hoofdplaat'),
    (312, 3.622, 51.768, 'Oosterschelde'),
    (313, 3.242, 51.505, 'Vlakte van De Raan'),
    (315, 3.998, 51.447, 'Hansweert'),
    (316, 3.694, 51.657, 'Schaar'),
    (319, 3.861, 51.226, 'Westdorpe'),
    (323, 3.884, 51.527, 'Wilhelminadorp'),
    (324, 4.006, 51.596, 'Stavenisse'),
    (330, 4.122, 51.992, 'Hoek van Holland'),
    (331, 4.193, 51.480, 'Tholen'),
    (340, 4.342, 51.449, 'Woensdrecht'),
    (343, 4.313, 51.893, 'Rotterdam Geulhaven'),
    (344, 4.447, 51.962, 'Rotterdam'),
    (348, 4.926, 51.970, 'Cabauw Mast'),
    (350, 4.936, 51.566, 'Gilze-Rijen'),
    (356, 5.146, 51.859, 'Herwijnen'),
    (370, 5.377, 51.451, 'Eindhoven'),
    (375, 5.707, 51.659, 'Volkel'),
    (377, 5.763, 51.198, 'Ell'),
    (380, 5.762, 50.906, 'Maastricht'),
    (391, 6.197, 51.498, 'Arcen'),
]


def get_station(lat_loc, lon_loc):
    """Find nearest station for location"""
    shortest_distance = math.inf
    for station_id, lon_st, lat_st, station_name in STATIONS:
        x = lon_st - lon_loc
        y = lat_st - lat_loc
        distance = math.sqrt(x**2 + y**2)
        if distance < shortest_distance:
            nearest_station = station_id, station_name, lat_st, lon_st
            shortest_distance = distance
    return nearest_station


def process_knmi(text):
    """Process response text from KNMI"""
    lines = text.split('\n')
    colnames = []
    rows = []
    for line in lines:
        if line.startswith('# STN,YYYYMMDD'):
            colnames = line.split(',')
        if not colnames:
            continue
        if not line.startswith('#'):
            values = [v.strip() for v in line.split(',')]
            if len(values) != len(colnames):
                continue
            row = {k: values[i] for i, k in enumerate(colnames)}
            rows.append(row)
    df = pd.DataFrame(rows)
    df.columns = [c.strip() for c in df.columns]
    rename_cols = {k: v for k, v in RENAME_COLS.items() if v != ''}
    df = df.rename(columns=rename_cols)
    for var in ADJUST:
        df[var] = df[var].apply(int)
        df[var] /= 10
    df['air_pressure'] = 100 * df.air_pressure.apply(float)
    return df


def get_knmi(lat, lon, start, end):
    """Download hourly weather data from KNMI"""
    station_id, station_name, lat, lon = get_station(lat, lon)
    print(f'Using station {station_id} {station_name} {lat},{lon}')
    data = f'start={start}01&end={end}24&stns={station_id}'
    r = requests.post(URL, data=data)
    text = r.text
    return process_knmi(text)
