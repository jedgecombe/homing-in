from datetime import datetime
import logging
import math
import re
from typing import Union

from lxml import html
import pandas as pd
import requests

from homing_in.search_constructor import SearchConstructor, FixedSearch, RightMoveSearch

logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self, search: SearchConstructor):
        self.search = search

    def create(self):
        if 'rightmove' in self.search.response.url:
            return RightMoveCrawler(self.search)

    @staticmethod
    def _strip_non_alpha_numeric(dirty_list: list) -> list:
        return [re.sub(r'\W+', '', x) for x in dirty_list]

    @staticmethod
    def _strip_whitespace(dirty_list: list) -> list:
        """remove white space"""
        return [x.strip(' \n') for x in dirty_list]


class RightMoveCrawler(Crawler):
    def __init__(self, search: Union[FixedSearch, RightMoveSearch]):
        super().__init__(search)
        self.property_count = self._count_properties()
        self.page_count = self._page_count()

    def _count_properties(self) -> int:
        """number of properties"""
        tree = html.fromstring(self.search.response.content)
        xp = """//span[@class="searchHeader-resultCount"]/text()"""
        return int(tree.xpath(xp)[0].replace(',', ''))

    def _page_count(self) -> int:
        """number of pages to search through"""
        max_results_per_page = 24
        max_pages = 42
        cnt = math.ceil(self.property_count / max_results_per_page)
        return int(min([cnt, max_pages]))

    def _get_prices(self, html_tree) -> list:
        if self.search.search_type == 'rent':
            xp = """//span[@class="propertyCard-priceValue"]/text()"""
        else:  # self.search.search_type == 'buy'
            xp = """//div[@class="propertyCard-priceValue"]/text()"""
        prices = html_tree.xpath(xp)
        prices_strp = self._strip_whitespace(prices)  # strip whitespace
        prices_clean = self._strip_non_alpha_numeric(prices_strp)
        return prices_clean

    def _get_titles(self, html_tree) -> list:
        xp = """//div[@class="propertyCard-details"]//a[@class="propertyCard-link"]
        //h2[@class="propertyCard-title"]/text()"""
        titles = html_tree.xpath(xp)
        titles_clean = self._strip_whitespace(titles)
        return titles_clean

    @staticmethod
    def _get_addresses(html_tree) -> list:
        xp = """//address[@class="propertyCard-address"]//span/text()"""
        return html_tree.xpath(xp)

    def _get_weblinks(self, html_tree) -> list:
        # TODO is html_tree.xpath(xpath) the best way? Investigate other ways to parse
        xp = """//div[@class="propertyCard-details"]//a[@class="propertyCard-link"]/@href"""
        weblinks = html_tree.xpath(xp)
        return self._append_url(weblinks)

    def _get_agent_urls(self, html_tree) -> list:
        xp = """//div[@class="propertyCard-contactsItem"]//div[@class="propertyCard-branchLogo"]\
        //a[@class="propertyCard-branchLogo-link"]/@href"""
        agent_urls = html_tree.xpath(xp)
        return self._append_url(agent_urls)

    def _get_property_beds(self, html_tree) -> str:
        xp = ".//*[@id='primaryContent']/div[1]/div/div/div[2]/div/h1"
        descr_resp = html_tree.xpath(xp)
        descr = self._check_found_text(descr_resp)
        beds = descr.split()[0] if descr != '-' else descr  # first part appears to always be number of beds
        return beds

    def _get_property_tenure(self, html_tree) -> str:
        xp = ".// *[ @ id = 'tenureType']"
        tenure_resp = html_tree.xpath(xp)
        tenure = self._check_found_text(tenure_resp)
        return tenure

    def _get_property_coords(self, html_tree) -> tuple:
        xp = ".//*[@id='description']/div/div[2]/div[2]/div/a/img"
        map_resp = html_tree.xpath(xp)
        if len(map_resp) > 0:
            map_source = map_resp[0].attrib['src']
            lat = map_source.split('latitude=')[1].split('&')[0]
            long = map_source.split('longitude=')[1].split('&')[0]
        else:
            lat, long = None, None
        return lat, long

    @staticmethod
    def _check_found_text(response: list) -> str:
        if len(response) > 0:
            tenure = response[0].text
        else:
            tenure = '-'
        return tenure

    @staticmethod
    def _append_url(append_list: list) -> list:
        base = 'http://www.rightmove.co.uk'
        return [f'{base}{x}' for x in append_list]

    def _scrape_to_df(self, prices: list, titles: list, addresses: list, weblinks: list,
                      agent_urls: list, ids: list) -> pd.DataFrame:

        df_len = len(ids)  # there can be blank cards for some of the fields
        df = pd.DataFrame({'price': prices[:df_len], 'description': titles[:df_len], 'address': addresses[:df_len],
                           'url': weblinks[:df_len], 'agent_url': agent_urls[:df_len], 'id': ids})
        df.dropna(inplace=True)
        df = df[df['price'].apply(lambda x: x.isnumeric())]  # drop non numeric
        if len(df) > 0:
            df['price'] = df['price'].astype(int)
            df['scrape_time'] = datetime.today()
        return df

    def _scrape_page(self, request_content) -> pd.DataFrame:
        # process html
        tree = html.fromstring(request_content)

        # Create data lists from xpaths:
        prices = self._get_prices(tree)
        titles = self._get_titles(tree)
        addresses = self._get_addresses(tree)
        urls = self._get_weblinks(tree)
        agent_urls = self._get_agent_urls(tree)
        ids = self._get_id(urls)

        page_df = self._scrape_to_df(prices, titles, addresses, urls, agent_urls, ids)
        return page_df

    def _get_id(self, urls: list) -> list:
        return [x.split('property-')[2].split('.html')[0] for x in urls if x != 'http://www.rightmove.co.uk']

    def _scrape_property(self, request_content) -> dict:
        tree = html.fromstring(request_content)
        beds = self._get_property_beds(tree)
        tenure = self._get_property_tenure(tree)
        lat, long = self._get_property_coords(tree)
        return {'beds': beds, 'tenure': tenure, 'latitude': lat, 'longitude': long}

    def _scrape_properties(self, results_df: pd.DataFrame) -> pd.DataFrame:
        prop_dicts = []
        for property_id, url in zip(results_df['id'], results_df['url']):
            logger.debug(f'property url: {url}')
            property_page = requests.get(url)
            prop_details = self._scrape_property(property_page.content)
            prop_details['id'] = property_id
            prop_dicts.append(prop_details)
        property_details = pd.DataFrame(prop_dicts)
        return property_details

    @staticmethod
    def _construct_index(page_number: int):
        """index appears to be the count of the final result on the page e.g. 24 on first page = 24, 24 on second = 48
        3 on third page = 51

        """
        results_per_page = 24
        return page_number * results_per_page

    def scrape(self, max_pages: int = 10) -> pd.DataFrame:
        dfs = []
        for pg in range(1, min(self.page_count, max_pages) + 1, 1):
            idx = self._construct_index(pg)
            pg_url = f'{self.search.response.url}&index={idx}'
            logger.info(f'visting page {pg}: {pg_url}')
            pg_resp = requests.get(pg_url)
            pg_data = self._scrape_page(pg_resp.content)
            pg_data['page_number'] = pg
            dfs.append(pg_data)
            # results[pg] = pg_data
        results = pd.concat(dfs)
        results.drop_duplicates(subset=['url'], inplace=True)
        property_details = self._scrape_properties(results)

        full_results = pd.merge(results, property_details, on='id')
        logger.info(f'number of properties scraped: {len(full_results)}')
        return full_results


