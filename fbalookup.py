#!/usr/bin/python
"""
Given an ASIN, find information about the lowest FBA offer.

No longer works - HTML on offer page on Amazon has changed from what it was in 2017.
Should be rewritten to use an Amazon.com API if one exists

Author: Brian Durham
Copyright: 2017 Brian Durham, all rights reserved.
"""

import re

from bs4 import BeautifulSoup as bs
from requests import get

base_url = 'https://www.amazon.com'

def get_offers_url(asin):
    """ given the ASIN, return a URL to fetch the product offers """

    # clean the ISBN into an ASIN
    asin = asin.replace(' ','').replace('-','')
    if len(asin) == 13:
        asin = asin[3:]
    
    print '{0}/gp/offer-listing/{1}/ref=dp_olp_all_mbc?ie=UTF8&condition=all'.format(base_url, asin)
    return '{0}/gp/offer-listing/{1}/ref=dp_olp_all_mbc?ie=UTF8&condition=all'.format(base_url, asin)

def is_asin_good(parsed_html):
    """ look for a signature indicating that Amazon has no product page """
    if parsed_html.find('meta', attrs={'http-equiv':'refresh'}) is None:
        # no refresh (presumably to a 404), so it is good
        return True
    else:
        return False

def extract_dollar_from_string(text):
    """
    find first dollar amount in string and return it.
    Returns None if no dollar amount is found.
    """
    result = re.search('(\$\d+\.\d\d)', text)
    if result:
        return result.group()
    else:
        return None

def extract_condition_from_string(text):
    """ removes a lot of excess characters from the condition text """
    return text.strip().replace('\n','').replace(' ','')

def next_page_url(parsed_html):
    """
    find URL for the next set of offers and return it.
    Returns None if this is the last page.
    """
    result = parsed_html.find('li',class_='a-last').find('a')
    if result is None:
        return None
    else:
        return result.attrs['href']

def extract_offers(parsed_html):
    """ extracts all offers for further processing """
    return parsed_html.find_all('div',class_='olpOffer')

def extract_price_cond_fba(offer):
    """
    Given a parsed offer, returns a dictionary with
    {
      price: string as $x.yz
      shipping: string as $x.yz or None
      condition: string as major-minor
      fba: boolean as True/False
    }
    """
    attrs = {}
    attrs['price'] = extract_dollar_from_string(
      offer.find(class_='olpPriceColumn').find('span').getText()
    )
    attrs['shipping'] = extract_dollar_from_string(
      offer.find(class_='olpPriceColumn').find('p').getText()
    )
    attrs['condition'] = extract_condition_from_string(
      offer.find(class_='olpConditionColumn').find('span').getText()
    )
    attrs['fba'] = False if offer.find(class_='olpBadge') is None else True
    return attrs

if __name__ == '__main__':
    """
    When run as a script, take in a single argument from the command line.
    The argument will be the ASIN.
    """
    import sys
    if len(sys.argv) == 1:
        sys.stderr.write('Missing ASIN. Please run: {0} ASIN\n'.format(sys.argv[0]))
        sys.exit(1)
    asin = sys.argv[1]

    # fetch first page of offers for given ASIN
    parsed_html = bs(get(get_offers_url(asin)).text, 'html.parser')

    # ensure there is actually a product page
    if not is_asin_good(parsed_html):
        print "{0}\tNo such item".format(asin)
        sys.exit(2)

    # parse through the offer listings
    fba_found = False
    while True:
        for parsed_offer in extract_offers(parsed_html):
            offer = extract_price_cond_fba(parsed_offer)
            if offer['fba']:
               # found the first FBA which should be the least
               fba_found = True
               break
        if fba_found:
            # no need to continue
            break
        # no FBA found yet, get the next set of offers
        next_url = next_page_url(parsed_html)
        if not next_url:
            # nothing left to check, no FBA found
            offer = None
            break
        # fetch next url data
        parsed_html = bs(get('{0}{1}'.format(base_url,next_url)).text,
                         'html.parser')

    # If no FBA was found, report that.
    if not fba_found:
        print "{0}\tNo FBA listings".format(asin)
        sys.exit(3)

    # If we're here, then an FBA was found. Print it.
    offer['asin'] = asin
    #offer['price'] = price[1:] # remove $ from price
    print "{asin}\t{price}\t{condition}".format(**offer)

