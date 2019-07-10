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


LONDON_BRIDGE_COORDS = (51.50489, -0.08754)
DEPARTURE_TIME = '2019/07/17 08:00:00'
TRANSPORT_MODE = 'TRANSIT'

FILENAME = 'output/results.csv'

SCORE_MAPPING = {
    'beds': {
        '1': -10,
        '2': 0,
        '3': 5,
        '4': 10,
        'other': -20
    },
    'tenure': {
        'Freehold': 5,
        'Share of Freehold': 2,
        'Leasehold': -10,
        '-': 0,
        'other': 0
    },
    'price': {
        'max_desired': 650000,
        'score_per_ten_thousand_under': 0.5,
        'score_per_ten_thousand_over': -1.0
    },
    'travel_time': {
        'ideal_minutes': 30,
        'bad_minutes': 60,
        'ideal_score': 10,
        'over_ideal_cost': -0.5,
        'over_bad_cost': -1
    }
}


URL = 'https://www.rightmove.co.uk/property-for-sale/find.html?searchType=SALE&locationIdentifier=REGION%5E70306&insId=1&radius=0.25&minPrice=&maxPrice=550000&minBedrooms=&maxBedrooms=&displayPropertyType=&maxDaysSinceAdded=14&_includeSSTC=on&sortByPriceDescending=&primaryDisplayPropertyType=&secondaryDisplayPropertyType=&oldDisplayPropertyType=&oldPrimaryDisplayPropertyType=&newHome=&auction=false'

# construct initial search url
uc = SearchConstructor(url_type='fixed').create()
uc.search(URL)

# scrape rightmove
rm = Crawler(uc).create()
rm_data = rm.scrape()
rm_data.to_csv(FILENAME)

# travel time
rm_data = pd.read_csv(FILENAME)
rm_data['travel_time_loc1'] = rm_data.apply(lambda x: travel_time(
    start_coords=(x['latitude'], x['longitude']),
    end_coords=LONDON_BRIDGE_COORDS,
    departure_time=DEPARTURE_TIME,
    mode=TRANSPORT_MODE
), axis=1)

# run scoring
rm_data['bedroom_score'] = rm_data.apply(lambda x: Scorer.value_map(x['beds'], SCORE_MAPPING['beds']), axis=1)
rm_data['tenure_score'] = rm_data.apply(lambda x: Scorer.value_map(x['tenure'], SCORE_MAPPING['tenure']), axis=1)
rm_data['price_score'] = rm_data.apply(lambda x: Scorer.price(x['price'], SCORE_MAPPING['price']['max_desired'],
                                                              SCORE_MAPPING['price']['score_per_ten_thousand_under'],
                                                              SCORE_MAPPING['price']['score_per_ten_thousand_over']
                                                              ), axis=1)
rm_data['tt_score'] = rm_data.apply(lambda x: Scorer.travel_time(
    x['travel_time_loc1'],
    ideal_minutes=SCORE_MAPPING['travel_time']['ideal_minutes'],
    bad_minutes=SCORE_MAPPING['travel_time']['bad_minutes'],
    ideal_score=SCORE_MAPPING['travel_time']['ideal_score'],
    over_ideal_cost=SCORE_MAPPING['travel_time']['over_ideal_cost'],
    over_bad_cost=SCORE_MAPPING['travel_time']['over_bad_cost']
), axis=1)
rm_data['total_score'] = rm_data[['bedroom_score', 'tenure_score', 'price_score', 'tt_score']].sum(axis=1)
rm_data.to_csv(FILENAME, index=False)

# map
m = Mapper(FILENAME)
m.create_map_with_points()
m.save_map(FILENAME.replace('csv', 'html'))
