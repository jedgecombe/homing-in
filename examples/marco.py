import logging

import pandas as pd

from homing_in.search_constructor import SearchConstructor
from homing_in.crawlers import Crawler
from homing_in.mapper import Mapper
from homing_in.travel_time import travel_time
from homing_in.scorer import Scorer

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d - %(name)s:%(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


CANARY_WHARF = (51.50374735798869, -0.01959085464477539)  # canary wharf
ANGEL = (51.53517798749436, -0.10459542274475098)  # flight centre, angel

DEPARTURE_TIME_MORN = '2019/08/17 08:00:00'

TRANSPORT_MODE = 'TRANSIT'

FILENAME = 'output/marco_results.csv'

SCORE_MAPPING = {
    'beds': {
        '1': 0,
        '2': 0,
        '3': 0,
        '4': 0,
        'other': 0
    },
    'tenure': {
        'Freehold': 0,
        'Share of Freehold': 0,
        'Leasehold': 0,
        '-': 0,
        'other': 0
    },
    'price': {
        'max_desired': 1700,
        'score_per_under': 1.25,
        'score_per_over': -2.5,
        'units': 100
    },
    'travel_time': {
        'ideal_minutes': 20,
        'bad_minutes': 45,
        'ideal_score': 10,
        'over_ideal_cost': - 10/(45-20),
        'over_bad_cost': - 10/(45-20)*2
    }
}


URL = 'https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=STATION%5E5792&maxBedrooms=2&minBedrooms=2&maxPrice=2000&minPrice=1250&radius=5.0&propertyTypes=flat&primaryDisplayPropertyType=flats&maxDaysSinceAdded=3&includeLetAgreed=false&mustHave=&dontShow=&furnishTypes=&keywords='

# construct initial search url
uc = SearchConstructor(url_type='fixed').create()
uc.search(URL)

# scrape rightmove
# rm = Crawler(uc).create()
# rm_data = rm.scrape(max_pages=42)
# rm_data.to_csv(FILENAME, index=False)

# travel time
# rm_data = pd.read_csv(FILENAME)
# rm_data['travel_time_cw'] = rm_data.apply(lambda x: travel_time(
#     start_coords=(x['latitude'], x['longitude']),
#     end_coords=CANARY_WHARF,
#     departure_time=DEPARTURE_TIME_MORN,
#     mode=TRANSPORT_MODE
# ), axis=1)
# rm_data['travel_time_angel'] = rm_data.apply(lambda x: travel_time(
#     start_coords=(x['latitude'], x['longitude']),
#     end_coords=ANGEL,
#     departure_time=DEPARTURE_TIME_MORN,
#     mode=TRANSPORT_MODE
# ), axis=1)
# rm_data.to_csv(FILENAME, index=False)

# # run scoring
rm_data = pd.read_csv(FILENAME)
rm_data['beds'] = rm_data['beds'].astype(str)
rm_data['bedroom_score'] = rm_data.apply(lambda x: Scorer.value_map(x['beds'], SCORE_MAPPING['beds']), axis=1)
rm_data['tenure_score'] = rm_data.apply(lambda x: Scorer.value_map(x['tenure'], SCORE_MAPPING['tenure']), axis=1)
rm_data['price_score'] = rm_data.apply(lambda x: Scorer.price(x['price'], SCORE_MAPPING['price']['max_desired'],
                                                              SCORE_MAPPING['price']['score_per_under'],
                                                              SCORE_MAPPING['price']['score_per_over'],
                                                              SCORE_MAPPING['price']['units']
                                                              ), axis=1)
rm_data['travel_time_cw_score'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_cw'],
    ideal_minutes=SCORE_MAPPING['travel_time']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time']['over_bad_cost']
), axis=1)
rm_data['travel_time_angel_score'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_angel'],
    ideal_minutes=SCORE_MAPPING['travel_time']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time']['over_bad_cost']
), axis=1)/2
rm_data['total_score'] = rm_data[['bedroom_score', 'tenure_score', 'price_score',
                                  'travel_time_angel_score', 'travel_time_cw_score']].sum(axis=1)
rm_data.to_csv(FILENAME, index=False)

# map
m = Mapper(FILENAME)
m.create_map_with_points('output/reference.csv')
m.save_map(FILENAME.replace('csv', 'html'))
