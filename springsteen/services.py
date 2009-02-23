from urllib import urlopen
from threading import Thread
from django.utils import simplejson
from django.conf import settings
from django.core.cache import cache

class Search(Thread):
    total_results = 0
    _results = []

    def __init__(self, query, params={}):
        super(Search, self).__init__()
        self.query = query
        self.params = params.copy()

    def run(self):
        return False

    def count(self):
        return len(self._results)

    def results(self):
        """
        Tuple of dictionaries in format:
        { 'title':"", 'summary':"", 'url':"" }
        """
        return ()

class CachableSearch(Search):
    _cache_duration = 60 * 30

    def make_cache_key(self):
        return "%s,%s,%s" % (self.__class__, self.query, self.params)

    def retrieve_cache(self):
        "Need to overload to decode cached data properly."
        pass

    def store_cache(self, raw):
        cache.set(self.make_cache_key(), raw, self._cache_duration)


class BossSearch(CachableSearch):
    _service = ""

    def build_uri(self):
        uri = "http://boss.yahooapis.com/ysearch/%s/v1/%s?appid=%s&format=json" \
            % (self._service, self.query, settings.BOSS_APP_ID)
        params = ["&%s=%s" % (p, self.params[p]) for p in self.params]
        return "%s%s" % (uri, "".join(params))

    def extract_data(self, results):
        self.total_results = int(results['ysearchresponse']['totalhits'])
        self._results = results['ysearchresponse']['resultset_%s' % self._service]
        for result in self._results:
            if result.has_key('source_name'):
                result['source_name'] = result['source']
            result['source'] = self._service

    def retrieve_cache(self):
        cached = cache.get(self.make_cache_key())
        if cached != None:
            cached = simplejson.loads(cached)
            self.extract_data(cached)

    def run(self):
        self.retrieve_cache()
        if not self._results:
            print "not cached"
            request = urlopen(self.build_uri())
            raw = request.read()
            self.store_cache(raw)
            results = simplejson.loads(raw)
            self.extract_data(results)
        print "cached!"

    def results(self):
        return self._results


class Web(BossSearch):
    _service = "web"

class Images(BossSearch):
    _service = "images"

class News(BossSearch):
    _service = "news"
