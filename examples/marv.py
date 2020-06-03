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
STRAND = (51.51412426735259, 0.11815667152404787)  # strand
CP = (51.415401341306435, -0.07308483123779297)  # CP

DEPARTURE_TIME_MORN = '2019/07/17 08:00:00'
DEPARTURE_TIME_EVE = '2019/07/17 18:00:00'
DEPARTURE_TIME_LATE = '2019/07/19 22:00:00'

TRANSPORT_MODE = 'TRANSIT'

FILENAME = 'output/results.csv'

SCORE_MAPPING = {
    'beds': {
        '1': -10,
        '2': 0,
        '3': 5,
        '4': 5,
        'other': -20
    },
    'tenure': {
        'Freehold': 3,
        'Share of Freehold': 3,
        'Leasehold': 0,
        '-': 0,
        'other': 0
    },
    'price': {
        'max_desired': 650000,
        'score_per_under': 0.25,
        'score_per_over': -1.0,
        'units': 10000
    },
    'travel_time': {
        'ideal_minutes': 25,
        'bad_minutes': 45,
        'ideal_score': 10,
        'over_ideal_cost': - 10/(45-25),
        'over_bad_cost': - 10/(45-25)*2
    },
    'travel_time_2': {
        'ideal_minutes': 40,
        'bad_minutes': 55,
        'ideal_score': 10,
        'over_ideal_cost': - 10/(55-40),
        'over_bad_cost': - 10/(55-40)*2
    }
}


URL = 'https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=STATION%5E5792&maxBedrooms=3&minBedrooms=2&maxPrice=700000&minPrice=550000&radius=10.0&propertyTypes=&maxDaysSinceAdded=14&includeSSTC=false&mustHave=&dontShow=&furnishTypes=&keywords='

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
# rm_data['travel_time_from_strand'] = rm_data.apply(lambda x: travel_time(
#     start_coords=STRAND,
#     end_coords=(x['latitude'], x['longitude']),
#     departure_time=DEPARTURE_TIME_LATE,
#     mode=TRANSPORT_MODE
# ), axis=1)
# rm_data['travel_time_cp'] = rm_data.apply(lambda x: travel_time(
#     start_coords=(x['latitude'], x['longitude']),
#     end_coords=CP,
#     departure_time=DEPARTURE_TIME_EVE,
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
                                                              SCORE_MAPPING['price']['units']), axis=1)
rm_data['tt_score_cw'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_cw'],
    ideal_minutes=SCORE_MAPPING['travel_time']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time']['over_bad_cost']
), axis=1)
rm_data['tt_score_from_strand'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_from_strand'],
    ideal_minutes=SCORE_MAPPING['travel_time_2']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time_2']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time_2']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time_2']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time_2']['over_bad_cost']
), axis=1)
rm_data['tt_score_cp'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_cp'],
    ideal_minutes=SCORE_MAPPING['travel_time']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time']['over_bad_cost']
), axis=1)/2
rm_data['total_score'] = rm_data[['bedroom_score', 'tenure_score', 'price_score',
                                  'tt_score_cw', 'tt_score_from_strand', 'tt_score_cp']].sum(axis=1)
rm_data.to_csv(FILENAME, index=False)

# map
m = Mapper(FILENAME)
m.create_map_with_points('output/reference.csv')
m.save_map(FILENAME.replace('csv', 'html'))
