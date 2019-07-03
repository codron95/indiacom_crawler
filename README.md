# indiacom_crawler
A selenium based crawler to crawl business locations and phone numbers from indiacom website

## Indiacom website structure
To explain the execution, it is important to understand the structure of indiacom.

*https://www.indiacom.com/yellow-pages/?catalphabet=<alphabet>*

The url above lists the keywords to search with based on alphabets. It also has the total number of search entries stated from that keyword.

*https://www.indiacom.com/yellow-pages/<keyword>/*

- A yellow page lists paginated results from a particular keyword.
- Every page has 30 result blocks or less.
- If we know the total entries from previous link, we can calculate the number of pages.
- We can retrieve the business name, location and the link to their complete page which we term as company page from every block.
- Pertaining to company page, there are following points:-
  - Company page can be in the standard form where phone number is revealed by clicking on the phone button.
  - Company page can be a custom design with no fixed structure. For these, we find numbers from regex match.

## Config definition
conf.yml stores the following parameters as persistent state on disk:-
**last_keyword_alphabet:** A (alphabet to fetch keywords from next)
**last_keyword_index:** 1 (keyword to fetch data for from the aforementioned alphabet)
**last_keyword_page_no:** 1 (Page number to fetch for a particular keyword)

The persistent state is used in 2 ways:-
- Crawler dumps the next state to pursue as soon as it is done with the current so that if the script dies, it executes from the same point.
- It can be used to start the script from a different point so as to execute multiple processes and crawl simultaneously.

Characteristics and flags for the crawler:-
- The script tries the network call 3 times in case of failures in an exponential back-off fashion.
- --purge-history flag resets the conf.yml parameter to the beginning.
- Crawler dumps verbose logs to check current running status in the script folder itself with the name crawl.log
- Each run creates a new file with timestamp in resources folder with pipe separated data.

## Usage

`python indiacom.py`
