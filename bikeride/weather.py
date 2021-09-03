"""Download hourly weather data"""

from bikeride.knmi import get_knmi
from bikeride.oikolab import get_oikolab


def get_weather(source, lat, lon, start, end=None, api_key=None, vars=None):
    """Download hourly weather data for location
    :param source: source to get data from
    :param lat: latitude for location
    :param lon: longitude for location
    :param start: first date of date range to request data for
    :param end: last date of date range to request data for (defaults to start)
    :param api_key: api key for weather data provider (if applicable)
    :param vars: variables to be included
    """
    if not end:
        end = start
    if source.lower() == 'knmi':
        return get_knmi(lat, lon, start, end)
    if source.lower() == 'oikolab':
        return get_oikolab(lat, lon, start, end, api_key, vars)
    return None
