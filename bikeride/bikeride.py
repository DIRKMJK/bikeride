"""Analyse and plot bicycle rides from gps files"""

import math
from pathlib import Path, PosixPath
import numpy as np
import dateutil.parser
import pandas as pd
import geopy.distance
from fitparse import FitFile
from bs4 import BeautifulSoup as bs
from ipyleaflet import Map, Polyline


class BikeRide():
    """Process and store records, segments and metadata from gps file.
    Optionally add data from weather file.
    """
    def __init__(self, path_ride, path_weather=None, limits=None, filetype=None,
                 additional_vars=None):
        """
        :param path_ride: path to gps file
        :param path_weather: path to csv file containing weather data (see )
        :param limits: list or tuple containing start location, end location
            and max distance (m) from location, if subset of ride is to be
            extracted. E.g. [(lat, lon), (lat, lon), 100]
        :param filetype: filetype of gps file. Only relevant if the filetype
            does not correspond to the suffix of the path_ride.
        :param additional_vars: additional variables to be included in ride
            summary.
        """
        self.path_ride = path_ride
        self.path_weather = path_weather
        self.limits = limits
        self.filetype = filetype
        self.additional_vars = additional_vars
        self.sport = None
        self.records, self.forward, self.limits_found = self.get_records()
        self.weather = self.read_weather_file()
        self.segments = self.records_to_segments()
        self.median_position = self.get_median_position()
        self.summary = self.get_summary()


    def to_degree(self, semicircles):
        """Convert semicircles to degrees"""
        return semicircles * (180 / (2**31))


    # from: https://github.com/gboeing/osmnx/
    def get_bearing(self, origin_point, destination_point):
        """Calculate the bearing between two lat-lon points."""
        lat1 = math.radians(origin_point[0])
        lat2 = math.radians(destination_point[0])
        diff_lng = math.radians(destination_point[1] - origin_point[1])

        x = math.sin(diff_lng) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2)
        y -= (math.sin(lat1) * math.cos(lat2) * math.cos(diff_lng))
        initial_bearing = math.atan2(x, y)

        initial_bearing = math.degrees(initial_bearing)
        bearing = (initial_bearing + 360) % 360

        return bearing


    def get_twa(self, heading, wind_direction):
        """Calculate true wind angle."""
        twa = (360 + (wind_direction - heading)) % 360
        if twa > 180:
            return twa - 360
        return twa


    def process_fit_record(self, record):
        """Extract data from record from fit file."""
        processed_record = {}
        for record_data in record:
            value = record_data.value
            name = record_data.name
            if name == 'position_lat':
                processed_record['lat'] = self.to_degree(value)
            if name == 'position_long':
                processed_record['lon'] = self.to_degree(value)
            processed_record[record_data.name] = record_data.value
        return processed_record


    def fit_path_to_records(self):
        """Extract data from .fit file."""
        try:
            fitfile = FitFile(str(self.path_ride))
            try:
                session = fitfile.get_messages('session')
                session_data = list(session)[0].get_values()
                sport = session_data['sport']
                self.sport = sport
            except (KeyError, IndexError):
                pass
            records = fitfile.get_messages('record')
            records = [self.process_fit_record(r) for r in records]
            records = [r for r in records if 'lat' in r]
            return records
        except:
            return []


    def trackpoint_to_record(self, trkpt):
        """Create record from trackpoint."""
        record = {
            'lat': float(trkpt.get('lat')),
            'lon': float(trkpt.get('lon')),
            'timestamp': dateutil.parser.parse(trkpt.find('time').text)
        }
        elevation = trkpt.find('ele')
        if elevation:
            record['altitude'] = float(elevation.text)
        temperature = trkpt.find('gpxtpx:atemp')
        if temperature:
            record['temperature_recorded'] = float(temperature.text)
        cadence = trkpt.find('gpxtpx:cad')
        if cadence:
            record['cadence'] = float(cadence.text)
        return record


    def gpx_path_to_records(self):
        """Extract data from .gpx file."""
        gpxfile = self.path_ride.read_text()
        soup = bs(gpxfile, 'lxml')
        trackpoints = soup.find_all('trkpt')
        return [self.trackpoint_to_record(trkpt) for trkpt in trackpoints]


    def truncate(self, records):
        """Try to extract section of route between start and end point."""
        start, end, threshold = self.limits
        min_dist_start = math.inf
        min_dist_end = math.inf
        limit_idx = [None, None]
        for i, record in enumerate(records):
            current = [record['lat'], record['lon']]
            dist_start = geopy.distance.distance(current, start).m
            if dist_start < min_dist_start:
                limit_idx[0] = i
                min_dist_start = dist_start
            dist_end = geopy.distance.distance(current, end).m
            if dist_end < min_dist_end:
                limit_idx[1] = i
                min_dist_end = dist_end
        limits_found = (
            (min_dist_start < threshold) &
            (min_dist_end < threshold)
        )
        if limits_found:
            forward = limit_idx[1] > limit_idx[0]
            if forward:
                records = records[limit_idx[0]: limit_idx[1]]
            else:
                records = records[limit_idx[1]: limit_idx[0]]
        else:
            forward = None
        return records, limits_found, forward


    def get_records(self):
        """Extract records from gps file."""
        if not isinstance(self.path_ride, PosixPath):
            self.path_ride = Path(self.path_ride)
        path_ride = self.path_ride
        if not self.filetype:
            self.filetype = path_ride.suffix
        self.filetype = self.filetype.lower().replace('.', '')
        if self.filetype == 'fit':
            records = self.fit_path_to_records()
        elif self.filetype == 'gpx':
            records = self.gpx_path_to_records()
        else:
            raise Exception('Filetype {} not implemented'.format(self.filetype))
        limits_found = None
        forward = None
        if self.limits:
            records, limits_found, forward = self.truncate(records)
            if not limits_found:
                message = 'Start or end point not found for {}'
                message = message.format(path_ride.name)
                print(message)
        return records, forward, limits_found


    def get_median_position(self):
        """Calculate median coordinates for ride."""
        median_lat = np.median([rec['lat'] for rec in self.records])
        median_lon = np.median([rec['lon'] for rec in self.records])
        return (median_lat, median_lon)


    def read_weather_file(self):
        """Read data from csv containing weather data."""
        if not self.path_weather:
            return None
        weather = pd.read_csv(self.path_weather)
        dt_vars = [
            var for var in ['date', 'hour', 'minute']
            if var in list(weather.columns)
        ]
        weather = weather.sort_values(by=dt_vars)
        return weather


    def add_weather(self, segment):
        """Add weather data to segment."""
        weather = self.weather
        timestamp = segment['timestamp_start']

        date = int(timestamp.strftime('%Y%m%d'))
        hour = int(timestamp.strftime('%H'))
        minute = int(timestamp.strftime('%S'))
        if 'minute' in weather.columns:
            subset_weather = weather[
                (weather.date == date) &
                (weather.hour == hour) &
                (weather.minute == minute)
            ]
        elif 'hour' in weather.columns:
            t1 = timestamp + pd.Timedelta(hours=1)
            h1 = int(t1.strftime('%H'))
            subset_weather = weather[
                (weather.date == date) &
                (weather.hour.isin([hour, h1]))
            ]
        else:
            subset_weather = weather[
                (weather.date == date)
            ]
        if subset_weather.empty:
            return segment
        if 'hour' in weather.columns and 'minute' not in weather.columns:
            for col in weather.columns:
                if col.startswith('Unnamed'):
                    continue
                values = list(subset_weather[col])
                try:
                    value = (60 - minute) * values[0] + minute * values[-1]
                    value /= 60
                except TypeError:
                    value = values[0]
                segment[col] = value
        else:
            for _, row in subset_weather.iterrows():
                for col in weather.columns:
                    segment[col] = row[col]
                break
        if 'wind_direction' in segment:
            wind_direction = segment['wind_direction']
            heading = segment['heading']
            twa = self.get_twa(heading, wind_direction)
            segment['twa'] = twa
            segment['twa_rounded_abs'] = abs(10 * round(segment['twa'] / 10))
            if 'wind_speed' in segment:
                headwind = segment['wind_speed'] * math.cos(math.radians(twa))
                segment['headwind'] = headwind
        return segment


    def records_to_segments(self):
        """Create segments from pairs of records."""
        segments = []
        records = self.records
        for i in range(len(records) - 1):
            start = records[i]
            end = records[i + 1]
            pos_start = (start['lat'], start['lon'])
            pos_end = (end['lat'], end['lon'])
            timestamp_start = start['timestamp']
            timestamp_end = end['timestamp']
            duration = (timestamp_end - timestamp_start).seconds
            length_calculated = geopy.distance.distance(pos_start, pos_end).m

            segment = {
                'id': i,
                'lat_start': start['lat'],
                'lon_start': start['lon'],
                'lat_end': end['lat'],
                'lon_end': end['lon'],
                'duration': duration,
                'length_calculated': length_calculated,
                'heading': self.get_bearing(pos_start, pos_end),
                'timestamp_start': timestamp_start,
                'timestamp_end': timestamp_end
            }
            if 'distance' in start and 'distance' in end:
                segment['distance_recorded_start'] = start['distance']
                segment['distance_recorded_end'] = end['distance']
                segment['length_recorded'] = end['distance'] - start['distance']
            if 'temperature' in start:
                segment['temp_recorded_start'] = start['temperature']
            if 'speed' in start:
                segment['speed_recorded_start'] = start['speed']
            if 'speed' in end:
                segment['speed_recorded_end'] = end['speed']
            if 'altitude' in start:
                segment['altitude_start'] = start['altitude']
            if 'altitude' in end:
                segment['altitude_end'] = end['altitude']
            if 'altitude' in start and 'altitude' in end:
                segment['ascent'] = end['altitude'] - start['altitude']
                if segment['length_calculated'] > 0:
                    segment['gradient'] = 100 * segment['ascent']
                    segment['gradient'] /= segment['length_calculated']
            if self.path_weather:
                segment = self.add_weather(segment)
            segments.append(segment)
        return segments


    def get_summary(self, mask=None):
        """Return dict with summary stats and metadata.

        Summary may be for entire ride or for subset of ride segments.
        :params mask: list of booleans to determine which segments to use for
            calculating stats
        """
        segments = self.segments
        if not segments:
            return 'No segments found'
        if mask:
            segments = [sgm for i, sgm in enumerate(segments) if mask[i]]
        length_calculated = sum([sgm['length_calculated'] for sgm in segments])
        duration = sum([sgm['duration'] for sgm in segments])
        try:
            speed_from_length_calculated = length_calculated / duration
        except ZeroDivisionError:
            print('Duration is zero for {}'.format(self.path_ride.name))
            speed_from_length_calculated = None
        first_sgm = segments[0]
        last_sgm = segments[-1]
        lat_start = first_sgm['lat_start']
        lon_start = first_sgm['lon_start']
        direction = self.get_bearing(
            (lat_start, lon_start), self.median_position
        )
        summary = {
            'filename': self.path_ride.name,
            'sport': self.sport,
            'timestamp_start' : first_sgm['timestamp_start'],
            'timestamp_end': last_sgm['timestamp_end'],
            'lat_start': lat_start,
            'lon_start': lon_start,
            'direction': direction,
            'length_calculated': length_calculated,
            'duration': duration,
            'speed_from_length_calculated': speed_from_length_calculated,
        }
        try:
            length_recorded = sum([sgm['length_recorded'] for sgm in segments])
            summary['length_recorded'] = length_recorded
            summary['speed_from_length_recorded'] = length_recorded / duration
        except KeyError:
            pass
        if self.limits:
            summary['forward'] = self.forward
        try:
            summary['temperature'] = sum([
                sgm['temperature'] * sgm['duration'] for sgm in segments
            ]) / duration
        except KeyError:
            pass
        try:
            summary['wind_speed'] = sum([
                sgm['wind_speed'] * sgm['duration'] for sgm in segments
            ]) / duration
        except KeyError:
            pass
        try:
            summary['wind_direction'] = sum([
                sgm['wind_direction'] * sgm['duration'] for sgm in segments
            ]) / duration
        except KeyError:
            pass
        try:
            summary['total_ascent'] = sum(
                [sgm['ascent'] for sgm in segments if sgm['ascent'] > 0]
            )
        except KeyError:
            pass
        try:
            summary['total_descent'] = sum(
                [sgm['ascent'] for sgm in segments if sgm['ascent'] < 0]
            )
        except KeyError:
            pass
        if self.additional_vars:
            for var in self.additional_vars:
                if var not in self.segments[0]:
                    continue
                numeric_values = [
                    sgm[var] * sgm['duration']
                    for sgm in segments
                    if isinstance(sgm[var], (int, float))
                ]
                if numeric_values:
                    value = sum(numeric_values) / duration
                else:
                    value = segments[0][var]
                summary[var] = value

        return summary


    def plot(self, mask=None, segment_ids=None, zoom=12):
        """Plot ride segments on map in Jupyter Notebook

        :params mask: list of booleans to select which segments of the ride
            to map
        :params segment_ids: index or list of segment ids to select which
            segments of the ride to map
        :params zoom: initial zoom level
        """
        if mask and segment_ids:
            raise Exception('Pass either a mask or a list of ids, not both')
        segments = self.segments
        if mask:
            segments = [sgm for i, sgm in enumerate(segments) if mask[i]]
        elif segment_ids:
            if not isinstance(segment_ids, list):
                segment_ids = [segment_ids]
            segments = [sgm for sgm in segments if sgm['id'] in segment_ids]
        lats_start = [sgm['lat_start'] for sgm in segments]
        lons_start = [sgm['lon_start'] for sgm in segments]
        lats_end = [sgm['lat_end'] for sgm in segments]
        lons_end = [sgm['lon_end'] for sgm in segments]
        median_lat = np.median(lats_start + lats_end)
        median_lon = np.median(lons_start + lons_end)
        map = Map(center=(median_lat, median_lon), zoom=zoom)
        if mask or segment_ids:
            for sgm in segments:
                position_start = (sgm['lat_start'], sgm['lon_start'])
                position_end = (sgm['lat_end'], sgm['lon_end'])
                poly_line = Polyline(
                    locations=(position_start, position_end),
                    color="red",
                    fill=False,
                    weight=3
                )
                map.add_layer(poly_line)
        else:
            positions = [
                (sgm['lat_start'], sgm['lon_start'])
                for sgm in segments
            ]
            positions.append((segments[-1]['lat_end'], segments[-1]['lon_end']))
            poly_line = Polyline(
                locations=positions,
                color="red",
                fill=False,
                weight=3
            )
            map.add_layer(poly_line)
        return map
