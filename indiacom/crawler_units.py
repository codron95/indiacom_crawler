import os
import csv
import logging
from datetime import datetime
from abc import ABCMeta, abstractmethod
from string import ascii_uppercase

from selenium import webdriver

from helpers import load_config, update_config
from entities import YellowPage, Keywords, CompanyPage

from custom_exceptions import PageFetchException

logger = logging.getLogger(__name__)

LOG_LINE = "Crawling for alphabet: {alphabet}, keyword: {keyword}, page_no: {page_no}"


class CrawlerBase(object):
    __metaclass__ = ABCMeta

    def __init__(self, base_dir, purge_history=False):
        self.base_dir = base_dir
        self.conf_file_path = os.path.join(base_dir, "conf.yml")
        self.conf_file_handle = open(self.conf_file_path, "r+")
        self.config = load_config(self.conf_file_handle)
        self.purge_history = purge_history
        if purge_history:
            self._load_defaults()

    def _open_dump_file(self, dump_file_name):
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        dump_file_name = dump_file_name + "_" + timestamp + ".csv"
        mode = "w"

        self.dump_file_path = os.path.join(self.base_dir, "resources", dump_file_name)
        self.dump_file = open(self.dump_file_path, mode)

        update_config(self.conf_file_handle, self.config)

    def _load_defaults(self):
        self.config["last_keyword_alphabet"] = "A"
        self.config["last_keyword_index"] = 1
        self.config["last_keyword_page_no"] = 1
        update_config(self.conf_file_handle, self.config)

    def _cleanup(self):
        self.conf_file_handle.close()

    @abstractmethod
    def crawl(self, url):
        pass


class IndiaComCrawler(CrawlerBase):

    def __init__(self, base_dir, purge_history=False):
        super(IndiaComCrawler, self).__init__(base_dir, purge_history)

        self._open_dump_file("business")

        self.fieldnames = ["business_name", "location", "phone", ]
        self.writer = csv.DictWriter(
            self.dump_file,
            delimiter="|",
            quoting=csv.QUOTE_ALL,
            fieldnames=self.fieldnames
        )

        self.writer.writeheader()

    def _cleanup(self):
        super(CrawlerBase, self)._cleanup()
        self.dump_file.close()

    def _crawl_and_dump(self, keyword_href, page_no):
        yellow_page = YellowPage(keyword_href, page_no)
        data = yellow_page.get_data()

        self.dump_data(data)

        # update the page to crawl next
        self.config["last_keyword_page_no"] = page_no + 1
        update_config(self.conf_file_handle, self.config)

    def crawl(self):
        last_keyword_alphabet = self.config["last_keyword_alphabet"]
        last_keyword_alphabet_index = ascii_uppercase.index(last_keyword_alphabet)
        last_keyword_index = self.config["last_keyword_index"]
        last_keyword_page_no = self.config["last_keyword_page_no"]

        for i in range(last_keyword_alphabet_index, len(ascii_uppercase) - 1):
            keywords = Keywords(ascii_uppercase[i])
            if i == last_keyword_alphabet_index:
                keyword_index = last_keyword_index
            else:
                keyword_index = 1

            # Reset the keyword counter in conf yml
            self.config["last_keyword_index"] = keyword_index
            update_config(self.conf_file_handle, self.config)

            for j in range(keyword_index, keywords.count + 1):
                if j == last_keyword_index:
                    page_no_start = last_keyword_page_no
                else:
                    page_no_start = 1

                keyword_href = keywords.nth_keyword_href(j)
                try:
                    yellow_page = YellowPage(keyword_href)
                except PageFetchException as e:
                    logger.info("Network Failure while crawling page")
                    continue

                page_count_total = keywords.nth_keyword_page_count(j)
                logger.info("Page count for this keyword is: " + str(page_count_total))

                # Reset the page counter in conf yml
                self.config["last_keyword_page_no"] = page_no_start
                update_config(self.conf_file_handle, self.config)

                # crawl keyword until it has a next page
                for page_no in range(page_no_start, page_count_total + 1):
                    log_line = LOG_LINE.format(
                        alphabet=ascii_uppercase[i],
                        keyword=keywords.nth_keyword_name(j),
                        page_no=page_no
                    )
                    logger.info(log_line)

                    # dump data and update the page no to crawl
                    self._crawl_and_dump(keyword_href, page_no)

                # update the keyword index
                self.config["last_keyword_index"] = j + 1
                update_config(self.conf_file_handle, self.config)

            # update keyword to start with
            self.config["last_keyword_alphabet"] = ascii_uppercase[i+1]
            update_config(self.conf_file_handle, self.config)

        logger.info("Concluding crawling the entire website")
        self._cleanup()

    def dump_data(self, data):
        self.writer.writerows(data)
        self.dump_file.flush()
