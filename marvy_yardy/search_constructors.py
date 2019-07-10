

class UrlConstructor:
    def __init__(self, site: str):
        assert site == 'rightmove', 'rightmove is the only site currently supported'
        self.site = site

    def create(self):
        if self.site == 'rightmove':
            return RightMove(self.site)

    def _validate_url(self):
        # TODO add check
        return True

    def fixed(self, url: str):
        if self._validate_url():
            return url

class RightMove(UrlConstructor):
    def _validate_url(self):
        # TODO add check
        return True


a = UrlConstructor(site='rightmove').create()
