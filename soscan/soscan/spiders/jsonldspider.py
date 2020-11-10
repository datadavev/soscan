import datetime
import pyld
import email.utils

import soscan.spiders.ldsitemapspider
import soscan.items
import soscan.utils

from pprint import pprint

class JsonldSpider(soscan.spiders.ldsitemapspider.LDSitemapSpider):

    name = "JsonldSpider"
    # sitemap_urls = ['https://www.bco-dmo.org/sitemap.xml',]

    def __init__(self, sitemap_urls="", *args, **kwargs):
        super(JsonldSpider, self).__init__(*args, **kwargs)
        self.sitemap_urls = sitemap_urls.split(" ")

    def sitemap_filter(self, entries):
        for entry in entries:
            pprint(entry)
            # print(f"ENTRY DT = {entry.get('lastmod')}")
            yield entry

    def parse(self, response, **kwargs):
        # print(f"URL = {response.url}")
        # print(f"TS = {response.request.meta['loc_timestamp']}")
        try:
            jsonld = pyld.jsonld.load_html(
                response.body, response.url, None, {"extractAllScripts": True}
            )
            if len(jsonld) > 0:
                item = soscan.items.SoscanItem()
                item["url"] = response.url
                item["status"] = response.status
                item["jsonld"] = jsonld
                item["time_loc"] = response.meta['loc_timestamp']
                item["time_header"] = None
                response_date = response.headers.get('Date', None)
                if response_date is not None:
                    try:
                        item["time_header"] = email.utils.parsedate_to_datetime(response_date.decode())
                    except Exception as e:
                        self.logger.error("Could not parse time: %s. %s", response_date, e)
                item["time_retrieved"] = soscan.utils.dtnow()
                yield item
        except Exception as e:
            self.logger.error("parse : %s", e)
        yield None
