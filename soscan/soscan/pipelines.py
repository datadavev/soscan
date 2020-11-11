# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import logging
import copy
import sqlalchemy.exc
import soscan.models
import pyld.jsonld
import scrapy.exceptions

SO_HTTP_CONTEXT = {"@context": {"@vocab": "http://schema.org/"}}
SO_HTTPS_CONTEXT = {"@context": {"@vocab": "https://schema.org/"}}

CONTEXT_CACHE = {}


def cachingDocumentLoader(url, options={}):
    loader = pyld.jsonld.requests_document_loader()
    if url in CONTEXT_CACHE:
        return CONTEXT_CACHE[url]
    resp = loader(url, options=options)
    CONTEXT_CACHE[url] = resp
    return resp


pyld.jsonld.set_document_loader(cachingDocumentLoader)


class SoscanNormalizePipeline:
    def __init__(self):
        self.logger = logging.getLogger("SoscanNormalize")
        self._processor = pyld.jsonld.JsonLdProcessor()

    def process_item(self, item, spider):
        self.logger.debug("process_item: %s", item["url"])
        result = self.normalizeSchemaOrg(item["jsonld"])
        if not result is None:
            item["jsonld"] = result
            return item
        raise scrapy.exceptions.DropItem(
            f"JSON-LD normalization failed for document: %s", item["jsonld"]
        )

    def normalizeSchemaOrg(self, source):
        try:
            options = None
            expanded = self._processor.expand(source, options)

            # Context document should not be modified in the .compact method, but it is
            # Send a copy of the context instead of the original.
            normalized = self._processor.compact(
                expanded, copy.deepcopy(SO_HTTP_CONTEXT), {"graph": True}
            )
            # Switch the namespace to use https
            normalized["@context"]["@vocab"] = "https://schema.org/"
            finalized = self._processor.compact(
                normalized, copy.deepcopy(SO_HTTPS_CONTEXT), {"graph": True}
            )
            return finalized
        except Exception as e:
            self.logger.error("Normalize failed: %s", e)
            self.logger.error("Cache: %s", CONTEXT_CACHE)
        return None


class SoscanPersistPipeline:
    def __init__(self, db_url):
        self.db_url = db_url
        self.logger = logging.getLogger("SoscanPersist")
        self._engine = None
        self._session = None
        self._engine = soscan.models.getEngine(self.db_url)

    @classmethod
    def from_crawler(cls, crawler):
        db_url = crawler.settings.get("DATABASE_URL", None)
        return cls(db_url)

    def open_spider(self, spider):
        self.logger.debug("open_spider")
        if self._engine is None:
            return
        self._session = soscan.models.getSession(self._engine)
        # TODO: check in database for most recent date of entry

    def close_spider(self, spider):
        self.logger.debug("close_spider")
        if self._session is not None:
            self._session.close()

    def process_item(self, item, spider):
        try:
            soitem = soscan.models.SOContent(
                url=item["url"],
                http_status=item["status"],
                time_retrieved=item["time_retrieved"],
                time_loc=item["time_loc"],
                time_header=item["time_header"],
                jsonld=item["jsonld"],
            )
            exists = self._session.query(soscan.models.SOContent).get(soitem.url)
            if exists:
                self.logger.debug("EXISTING content: %s", soitem.url)
            else:
                self.logger.debug("NEW content: %s", soitem.url)
                try:
                    self._session.add(soitem)
                    self._session.commit()
                except sqlalchemy.exc.IntegrityError as e:
                    self.logger.warning("Could not add '%s' because %s", soitem.url, e)
        except Exception as e:
            self.logger.error(e)
        return item
