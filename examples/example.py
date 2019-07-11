import logging

import pandas as pd

from marvy_yardy.search_constructors import SearchConstructor
from marvy_yardy.crawlers import Crawler
from marvy_yardy.mapper import Mapper
from marvy_yardy.travel_time import travel_time
from marvy_yardy.scorer import Scorer

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d - %(name)s:%(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


DEST_COORDS = (51.50374735798869, -0.01959085464477539)  # canary wharf
DEST_COORDS_2 = (51.51412426735259, 0.11815667152404787) # strand

DEPARTURE_TIME = '2019/07/17 08:00:00'
DEPARTURE_TIME_2 = '2019/07/19 22:00:00'

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
        'score_per_ten_thousand_under': 0.25,
        'score_per_ten_thousand_over': -1.0
    },
    'travel_time': {
        'ideal_minutes': 30,
        'bad_minutes': 55,
        'ideal_score': 10,
        'over_ideal_cost': -0.4,
        'over_bad_cost': -0.8
    },
    'travel_time_2': {
        'ideal_minutes': 40,
        'bad_minutes': 55,
        'ideal_score': 10,
        'over_ideal_cost': -0.66,
        'over_bad_cost': -1
    }
}


URL = 'https://www.rightmove.co.uk/property-for-sale/find.html?searchType=SALE&locationIdentifier=STATION%5E4514&insId=2&radius=3.0&minPrice=550000&maxPrice=650000&minBedrooms=2&maxBedrooms=3&displayPropertyType=&maxDaysSinceAdded=&_includeSSTC=on&sortByPriceDescending=&primaryDisplayPropertyType=&secondaryDisplayPropertyType=&oldDisplayPropertyType=&oldPrimaryDisplayPropertyType=&newHome=&auction=false'

# construct initial search url
uc = SearchConstructor(url_type='fixed').create()
uc.search(URL)

# scrape rightmove
rm = Crawler(uc).create()
rm_data = rm.scrape(max_pages=35)
rm_data.to_csv(FILENAME, index=False)

# travel time
rm_data = pd.read_csv(FILENAME)
rm_data['travel_time_loc1'] = rm_data.apply(lambda x: travel_time(
    start_coords=(x['latitude'], x['longitude']),
    end_coords=DEST_COORDS,
    departure_time=DEPARTURE_TIME,
    mode=TRANSPORT_MODE
), axis=1)
rm_data['travel_time_loc2'] = rm_data.apply(lambda x: travel_time(
    start_coords=DEST_COORDS_2,
    end_coords=(x['latitude'], x['longitude']),
    departure_time=DEPARTURE_TIME_2,
    mode=TRANSPORT_MODE
), axis=1)
rm_data.to_csv(FILENAME, index=False)

# # run scoring
rm_data = pd.read_csv(FILENAME)
rm_data['beds'] = rm_data['beds'].astype(str)
rm_data['bedroom_score'] = rm_data.apply(lambda x: Scorer.value_map(x['beds'], SCORE_MAPPING['beds']), axis=1)
rm_data['tenure_score'] = rm_data.apply(lambda x: Scorer.value_map(x['tenure'], SCORE_MAPPING['tenure']), axis=1)
rm_data['price_score'] = rm_data.apply(lambda x: Scorer.price(x['price'], SCORE_MAPPING['price']['max_desired'],
                                                              SCORE_MAPPING['price']['score_per_ten_thousand_under'],
                                                              SCORE_MAPPING['price']['score_per_ten_thousand_over']
                                                              ), axis=1)
rm_data['tt_score1'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_loc1'],
    ideal_minutes=SCORE_MAPPING['travel_time']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time']['over_bad_cost']
), axis=1)
rm_data['tt_score2'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_loc2'],
    ideal_minutes=SCORE_MAPPING['travel_time_2']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time_2']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time_2']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time_2']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time_2']['over_bad_cost']
), axis=1)
rm_data['total_score'] = rm_data[['bedroom_score', 'tenure_score', 'price_score', 'tt_score1', 'tt_score2']].sum(axis=1)
rm_data.to_csv(FILENAME, index=False)

# map
m = Mapper(FILENAME)
m.create_map_with_points('output/reference.csv')
m.save_map(FILENAME.replace('csv', 'html'))
