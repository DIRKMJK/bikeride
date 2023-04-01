The bikeride package is a tool for analysing gps files of bicycle rides. It creates segments, and for each segment it stores data like length, duration, and the direction you’re heading. If you provide a csv file with weather data, it will add weather data to the segments and calculate the direction of the wind relative to the direction of the bicycle. It calculates summary statistics for the entire ride and it will let you plot a ride or segments of a ride on a map.

The package was created for analysing bicycle rides (more specifically: for an [analysis of wind and cycling speed][article]), but you can also use it for other activity types.

# Caveats

- This package is work in progress. It may contain errors. More functionality may be added. Methods for calculations may change.
- This package was developed using `.fit` files created by a Garmin bicycle computer and `.gpx` files exported from Strava. Files created in a different manner may result in errors. If you let me know, I’ll try to fix them.
- During a bicycle ride, you can pause recording. Pauses may not be handled properly by the `bikeride` package. A pragmatic workaround may be to filter out segments with extreme long durations or low speeds.
- There may be differences in how bicycle computers record data. Many Garmin devices let you choose between [smart recording][smart] and recording every second. I haven’t tested every second recording, but this may lead to large errors in direction, relative wind direction and gradient (in fact, data for gradients may show large errors even with ‘smart’ recording).
- At this point, the difference between horizontal distance and distance traveled hasn’t been taken into account. As a result, on a hilly ride, `length_recorded` may be a bit longer than `length_calculated` (which is based on gps coordinates).

# Installation

```
pip install pybikeride
```

# Examples

## Create a BikeRide object

```python
from bikeride import BikeRide

ride = BikeRide('../data/ride.fit')
```

The filetype will be guessed from the filename extension. You can override this by passing a `filetype` parameter. Currently `fit` and `gpx` files are supported.

You can access the records and the segments created from them using `ride.records` and `ride.segments`. If you store the records or segments in a dataframe, you can easily plot characteristics of your ride. For example, if you want to take a quick look where you had a headwind:

```python
import pandas as pd

sgms = pd.DataFrame(ride.segments)
sgms = sgms.set_index('distance_recorded_start')
sgms.twa.apply(abs).plot()
```

Note that the example above only works if you’ve passed weather data to the BikeRide object.

## Add weather data

You can add weather data to the BikeRide object by passing a path to a csv file with weather data, which should use a comma as a separator.

```python
ride = BikeRide('../data/ride.fit', path_weather='../data/weather.csv')
```

The csv file may contain the following columns:

- date: yyyymmdd (required)
- hour: hh
- minute: mm
- wind_speed: wind speed in m/s
- wind_direction: wind direction in degrees
- temperature

Note that date and time must be UTC.

You can include additional columns as you please. The data from these additional columns will be added to segment data, but not by default to the ride summary (see below, Ride summary).

Here‘s an example of what a weather file might look like:

```
date,hour,wind_direction,wind_speed,temperature,precipitation_duration
20210108,8,10,1.0,2.7,0.0
20210108,9,30,2.0,3.6,0.0
20210108,10,50,3.0,3.8,0.0
20210108,11,50,3.0,3.9,0.0
20210108,12,80,2.0,3.4,0.0
20210108,13,30,1.0,4.8,0.0
20210108,14,20,2.0,2.9,0.0
20210108,15,340,1.0,2.0,0.0
20210108,16,320,1.0,1.1,0.0
```

## Truncate ride

If you want to analyse only a part of the ride, as defined by a starting and end point, you can pass a `limits` parameter to the BikeRide object. This is a list or tuple containing start location, end location and a threshold distance in metres. The threshold distance is used to determine whether the route passed the start or end point.

```python
limits = [[52.293875, 4.8914030000000004], [52.287667999999996, 4.91561], 100]
ride = BikeRide('../data/ride.fit', limits=limits)
```

If you pass `limits` to the BikeRide object, a property `ride.forward` will be set which is `True` if you rode the route from the start to the end position; and `False` if you rode it in the opposite direction.

## Ride summary

The `ride.summary` property contains summary statistics and metadata for the ride. Depending on what data is stored in the original gps file and in the weather file, the summary may include the following data:

- filename
- sport: activity type
- timestamp_start: start of first segment
- timestamp_end: end of last segment
- lat_start: latitude of start point
- lon_start: longitude of start point
- direction: direction from start point to median of coordinates of records (degrees)
- length_recorded: length of the ride based on distance recorded by the bicycle computer (m)
- length_calculated: sum of the lengths of segments as calculated from coordinates for start and end location (m). If your device records distance based on wheel revolutions, then `length_calculated` may be less accurate than `length_recorded`. Further, `length_calculated` doesn’t take vertical distance into account
- duration: total duration of the ride (s)
- speed_from_length_recorded: `length_recorded` / `duration` (m/s)
- speed_from_length_calculated: `length_calculated` / `duration` (m/s)
- wind_speed: weighted average wind speed (from weather csv)
- wind_direction: weighted average wind direction (from weather csv)
- temperature: weighted average temperature (from weather csv)
- total ascent: sum of positive ascents of segments (m). No smoothing applied
- total descent: sum of negative ascents of segments (m). No smoothing applied
- created_by: device used to record activity (Garmin), or author (gpx)
- errors: errors that may have occurred while parsing the file

When you create a BikeRide object, you can pass a parameter `additional_vars`, which should be a list of variable names that you want to be included in the summary. For example, you could pass `additional_vars=['hourly_precipitation_amount', 'air_pressure']`, provided those variables are in your weather data. If the data is numeric, the weighted average will be used in the ride summary; otherwise the value of the first segment.

If you store multiple rides in a list, then you can create a dataframe containing the summaries for these rides:

```python
from pathlib import Path
import pandas as pd

rides = [BikeRide(path) for path in DIR_FIT.glob('*.fit')]
df = pd.DataFrame([ride.summary for ride in rides])
```

One use for this would be to create an overview of rides from a Strava bulk export.  Using `lat_start`, `lon_start` and `direction`, you could filter rides by where you went. Or you could use weather variables to identify your worst-weather rides.

You can also use the `get_summary` method to calculate summary stats for a subset of the segments. For example, if you want to analyse the segments where you had a headwind (of course, this only works if the BikeRide object contains wind direction data):

```python
mask = [sgm['twa_rounded_abs'] == 0 for sgm in ride.segments]
ride.get_summary(mask=mask)
```

## Plot a ride or segments of a ride

In a Jupyter notebook, you can plot a ride using the `ipyleaflet` package. You can pass a `zoom` parameter to change the initial zoom level.

```python
ride.plot()
```

You can also plot a selection of segments by passing a mask or a list of `segment_ids`. For example, if you want to plot the segments where you had a headwind (of course, this only works if the BikeRide object contains wind direction data):

```python
mask = [sgm['twa_rounded_abs'] == 0 for sgm in ride.segments]
ride.plot(mask=mask)
```

## Plot multiple rides

The `plot_rides` function lets you plot multiple rides. If you set the `how` parameter to `direction`, it plots lines from the starting points to the median positions of the rides.

```python
from bikeride import plot_rides

plot_rides(rides, how='direction')
```

If you want to compare the route of two or more rides, you can set `how` to `ride`.  Of course, if you plot a larger number of rides, the map may become messy.

## Download weather data

You can use the `get_weather` function to download historical weather data for a specified location:

```python
from bikeride import get_weather

lat = 52.318
lon = 4.790
api_key = 'xxx'
start = '20100101'
end = '20210902'

df = get_weather('knmi', lat, lon, start, end)
df = get_weather('oikolab', lat, lon, start, end, api_key)
```

Currently, two sources can be used:

- The Dutch meteorological institute KNMI, which provides data from weather stations in the Netherlands. No need to pass an api key. Note that there is an unspecified maximum amount of data that can be requested in one call; it appears that you will hit this maximum if you request over ten years of data at a time.
- Oikolab, which provides global data. Information about how their data is generated can be found [here][oikolab]. In order to get oikolab data you need to request an api key; oikolab currently offers a pay-as-you-go plan which will let you download 5,000 units per month for free, with one unit corresponding to one month of data for one variable at one location.


# Todo

- Perhaps add an option to create cleaned-up ride stats, disregarding outlier segments

[smart]:https://support.garmin.com/en-US/?faq=s4w6kZmbmK0P6l20SgpW28
[article]:https://dirkmjk.nl/en/439/wind-crosswinds-and-bicycle-speed
[oikolab]:https://docs.oikolab.com/#5-frequently-asked-questions
