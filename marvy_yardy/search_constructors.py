

import requests


class SearchConstructor:
    def __init__(self, url_type: str):
        assert url_type == 'fixed', 'fixed is the only url_type currently supported'
        self.url_type = url_type
        self.response = None
        self.validated_url = False
        self.search_type = None

    def create(self):
        if self.url_type == 'rightmove':
            return RightMoveSearch()
        elif self.url_type == 'fixed':
            return FixedSearch()

    def _validate_url(self, response):
        if response.status_code == 200:
            valid = True
        else:
            valid = False
        return valid

    def _check_search_type(self):
        # TODO this should be part of RightMoveSearch really but as not implemented yet, leave here
        sale_ids = ['/property-for-sale/', '/new-homes-for-sale/']
        rent_ids = ['/property-to-rent/']
        if any(x in self.response.url for x in sale_ids):
            search_type = 'sale'
        elif any(x in self.response.url for x in rent_ids):
            search_type = 'rent'
        else:
            raise ValueError('search_type not identified')
        return search_type


class FixedSearch(SearchConstructor):
    def __init__(self):
        super().__init__('fixed')

    def search(self, url):
        self.response = requests.get(url)
        self.validated_url = self._validate_url(self.response)
        self.search_type = self._check_search_type()


class RightMoveSearch(SearchConstructor):
    def __init__(self):
        super().__init__('rightmove')

    def _validate_url(self):
        # TODO add check
        return True


