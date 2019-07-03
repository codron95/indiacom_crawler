from __future__ import division

import re
import math
import time
import logging
from selenium import webdriver

from custom_exceptions import PageFetchException

logger = logging.getLogger(__name__)


class DriverBase(object):

    BACK_OFF_CONSTANT = 4

    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("headless")

        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.driver.set_page_load_timeout(20)

    def get(self, url, tries=0):
        try:
            time.sleep(tries*self.BACK_OFF_CONSTANT)
            self.driver.get(url)

            if self._body_is_empty():
                raise Exception

        except Exception as e:
            # Catching flat exception to avoid script
            # dying under any circumstance
            tries += 1
            if tries > 3:
                raise PageFetchException

            return self.get(url, tries)

        else:
            return True

    def _body_is_empty(self):
        if not self.driver.find_elements_by_xpath("//body//*"):
            return True

        return False


class Keywords(DriverBase):

    KEYWORD_URL = "https://www.indiacom.com/yellow-pages/?catalphabet={alphabet}"

    def __init__(self, alphabet):
        super(Keywords, self).__init__()

        url = self.KEYWORD_URL.format(alphabet=alphabet)
        self.get(url)
        self.keyword_data = self.driver.find_elements_by_xpath(
            "//li[@class='catlink']"
        )
        self.count_pattern = re.compile(r"(\d+)")
        self.total_entries_per_page = 30

    def nth_keyword_href(self, n):
        cat_link = self.keyword_data[n-1].find_elements_by_xpath(".//a")[0]
        return cat_link.get_property("href")

    def nth_keyword_name(self, n):
        cat_link = self.keyword_data[n-1].find_elements_by_xpath(".//a")[0]
        return cat_link.text

    def nth_keyword_page_count(self, n):
        cat_link_text = self.keyword_data[n-1].text
        entry_count = int(re.search(self.count_pattern, cat_link_text).group())
        page_count_total = math.ceil(entry_count/self.total_entries_per_page)
        return int(page_count_total)

    @property
    def count(self):
        return len(self.keyword_data)


class CompanyPage(DriverBase):

    REGEX_LIST = [
        r"(\+?\(?91\)?\s*-\s*[0-9]{10})",
        r"(\+?\(?91\)?\s*-\s*\(?[0-9]{1,4}\)?\s*-\s*[0-9]{8,10})"
    ]

    def __init__(self, url):
        super(CompanyPage, self).__init__()

        self.get(url)
        self.page_source = self.driver.page_source

        self.regex_compiled = self._compile_regex()

    def _compile_regex(self):
        regex_list_compiled = []
        for regex in self.REGEX_LIST:
            regex_list_compiled.append(re.compile(regex))

        return regex_list_compiled

    def _sanitize(self, phone_no):
        phone_no = phone_no.replace("\n", "")
        phone_no = phone_no.replace(" ", "")
        return phone_no

    def _de_duplicate(self, list):
        new_list = []
        for elem in list:
            if elem not in new_list:
                new_list.append(elem)

        return new_list

    def _get_phone_nos_by_regex(self):
        matches = []
        for pattern in self.regex_compiled:
            pattern_matches = re.finditer(pattern, self.page_source)
            if pattern_matches:
                for match in pattern_matches:
                    phone_no = match.group()
                    phone_no = self._sanitize(phone_no)
                    matches.append(phone_no)

        return self._de_duplicate(matches)

    def _get_phone_nos_by_click(self):
        phone_link_xpath = "//div[@id='div_phoneadd']//a"
        phone_no_xpath = "//div[@id='div_phoneadd']/div[@class='lighttext']/strong/a"

        phone_link_elem = self.driver.find_elements_by_xpath(phone_link_xpath)

        if not phone_link_elem:
            return []

        phone_link_elem[0].click()
        phone_no_elem = self.driver.find_elements_by_xpath(phone_no_xpath)

        if not phone_no_elem:
            return []

        return [phone_no_elem[0].text]

    def get_phone_nos(self):

        phone_nos = self._get_phone_nos_by_click()

        if not phone_nos:
            phone_nos = self._get_phone_nos_by_regex()

        return phone_nos


class YellowPage(DriverBase):

    YELLOWPAGE_URL = "{base_url}?page={page}"

    def __init__(self, url, page=1):
        super(YellowPage, self).__init__()

        url = self.YELLOWPAGE_URL.format(
            base_url=url,
            page=page
        )
        self.get(url)

    def _get_location(self, business_block):
        location = business_block.find_elements_by_xpath("//div[@class='b_address']")

        if not location:
            return "Not Found"

        return location[0].text

    def _get_business_name(self, business_block):
        business_name = business_block.find_elements_by_xpath(".//div[@class='b_name']")
        if not business_name:
            return "Not Found"

        return business_name[0].text

    def _get_detail_href(self, business_block):
        link_elem_xpath = ".//div[@class='b_name']//a"
        link_elem = business_block.find_elements_by_xpath(link_elem_xpath)
        if not link_elem:
            return None

        return link_elem[0].get_property("href")

    def get_data(self):
        accumulated_frame = []

        business_blocks = self.driver.find_elements_by_xpath("//div[@class='b_listing']")

        for index, business_block in enumerate(business_blocks):
            logger.info("Crawling " + str(index+1) + " entry on this page")
            single_frame = {}
            single_frame["business_name"] = self._get_business_name(business_block)
            single_frame["location"] = self._get_location(business_block)
            try:
                company_page = CompanyPage(self._get_detail_href(business_block))
            except PageFetchException as e:
                logger.info("Network failure while crawling entry")
                continue

            phone_nos = company_page.get_phone_nos()

            single_frame["phone"] = ",".join(phone_nos)

            accumulated_frame.append(single_frame)

        return accumulated_frame
