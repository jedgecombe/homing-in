import calendar
import json
import logging
import os
import urllib.error
import urllib.request
import time

from dotenv import load_dotenv, find_dotenv
import numpy as np

load_dotenv(find_dotenv())
GOOGLE_API_KEY = os.environ.get('GOOGLE_API')

logger = logging.getLogger(__name__)


def travel_time(start_coords: tuple, end_coords: tuple, departure_time: str, mode: str):
    travel_modes = ['DRIVING', 'BICYCLING', 'TRANSIT', 'WALKING']
    assert mode in travel_modes, f'mode must be one of the following: {travel_modes} (chosen: {mode})'
    start_lat, start_long = start_coords
    end_lat, end_long = end_coords
    start_coords_str = f'{start_lat},{start_long}'
    end_coords_str = f'{end_lat},{end_long}'
    depart_time = calendar.timegm(time.strptime(departure_time, '%Y/%m/%d %H:%M:%S'))
    full_url = (
        f'https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins={start_coords_str}&'
        f'destinations={end_coords_str}&mode={mode}&departure_time={depart_time}&key={GOOGLE_API_KEY}')
    logger.debug('calling: %s' % full_url)
    out = np.nan
    try:
        result = urllib.request.urlopen(full_url)
        response = json.load(result)
        if response['status'] == 'OVER_QUERY_LIMIT':
            logger.error('OVER QUERY LIMIT')
        else:
            try:
                minutes = round(response['rows'][0]['elements'][0]['duration']['value'] / 60, 0)
                out = minutes
            except KeyError:
                pass
    except urllib.error.HTTPError or urllib.error.URLError as e:
        logger.error(f'ERROR({e.errno}): {e.strerror}')
    return out


