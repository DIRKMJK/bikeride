"""Plot rides"""

from ipyleaflet import Map, Polyline
import pandas as pd
import numpy as np

PALETTE = ['#1f78b4','#33a02c'] # from ColorBrewer


def plot_rides(rides, how='direction', zoom=10, palette=None):
    """Plot list of rides on map
    :params rides: list of BikeRide objects
    :params how: if 'direction' plot line from start to median position; if
        'ride' plot entire ride
    :params zoom: initial zoom level
    :params palette: colours to use if plotting rides
    """
    if not palette:
        palette = PALETTE
    median_lat = np.median([ride.median_position[0] for ride in rides])
    median_lon = np.median([ride.median_position[1] for ride in rides])
    m = Map(center=(median_lat, median_lon), zoom=zoom)
    if how == 'direction':
        summaries = pd.DataFrame([
            ride.summary for ride in rides
            if not isinstance(ride.summary, str)
        ])
        positions_start = zip(summaries.lat_start, summaries.lon_start)
        median_positions = [ride.median_position for ride in rides]
        for pos_start, median_pos in zip(positions_start, median_positions):
            poly_line = Polyline(
                locations=(pos_start, median_pos),
                color="red" ,
                fill=False,
                weight=1
            )
            m.add_layer(poly_line)
    elif how == 'ride':
        for i, ride in enumerate(rides):
            colour = palette[i % len(palette)]
            locations = [(rec['lat'], rec['lon']) for rec in ride.records]
            poly_line = Polyline(
                locations=locations,
                color=colour,
                fill=False,
                weight=3
            )
            m.add_layer(poly_line)
    return m
