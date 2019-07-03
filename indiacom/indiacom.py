import os
import logging
import argparse
from logging.handlers import TimedRotatingFileHandler

import yaml

from crawler_units import IndiaComCrawler

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)

def init_logging(log_file_path):
    formatter = logging.Formatter(
        "[%(asctime)s]:[%(threadName)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    logging.basicConfig(filename=log_file_path, level=logging.INFO)
    handler = TimedRotatingFileHandler(
        log_file_path,
        backupCount=2,
        when='midnight'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def generate_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--purge-history", "-ph",
        action="store_true",
        help="ignore last run and run from start"
    )

    return parser

if __name__ == "__main__":

    parser = generate_arg_parser()
    args = parser.parse_args()

    init_logging(os.path.join(BASE_DIR, "crawl.log"))

    indiacom_crawler = IndiaComCrawler(BASE_DIR, args.purge_history)

    try:
        indiacom_crawler.crawl()
    except IOError as e:
        print("Dump file not found. Re-initiate crawler with --purge-history")
        exit()
