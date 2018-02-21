#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Recursive search of Google scholar based on articles that cite an imput
article. Limited by requiring matching to an input regex.
"""
# Copyright 2018 Austin Fox
# Program is distributed under the terms of the
# GNU General Public License see ./License for more information.

# Python 3 compatibility
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import (
         bytes, dict, int, list, object, range, str,
         ascii, chr, hex, input, next, oct, open,
         pow, round, super,
         filter, map, zip)
# #######################

import sys, os
import numpy as np
import re
import csv
from random import randint
import time
import scholar as sr


def sleep(length):
    toolbar_width = 60
    wait = length/toolbar_width
    # setup toolbar
    sys.stdout.write("[%s]" % (" " * toolbar_width))
    sys.stdout.flush()
    sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['
    for i in xrange(toolbar_width):
        time.sleep(wait) # do real work here
        # update the bar
        sys.stdout.write("-")
        sys.stdout.flush()

    sys.stdout.write("\n")


def get_retrieved_arts(filename):
    retrieved_arts = []
    try:
        with open(filename + '.csv','rb') as dest_f:
            data_iter = csv.reader(dest_f)
            retrieved_arts = [re.sub('https*:\/\/', '', data[1]) for
                              data in data_iter]
    except:
        print('No File:', filename)

    return retrieved_arts


def set_up_querier():
    scholar = sr

    cookiefile = os.path.abspath(os.path.join(os.path.dirname( __file__ ),
                                           'cookies.txt'))
    # fix error repace 0 in 5th column with '' and remove decimals
    # http://stackoverflow.com/questions/14742899/using-cookies-txt-file-with-python-requests if os.path.exists(cookiefile):
    scholar.ScholarConf.COOKIE_JAR_FILE = cookiefile
    scholar.ScholarConf.LOG_LEVEL = 4
    scholar.ScholarConf.USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X"
            "10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"
            "64.0.3282.140  Safari/537.36")

    scholar.ScholarConf.MAX_PAGE_RESULTS = 10

    querier = scholar.ScholarQuerier()
    settings = scholar.ScholarSettings()
    # settings.set_citation_format(sr.ScholarSettings.CITFORM_BIBTEX)
    settings.set_citation_format(0)
    # WorldCat
    # 569367360547434339
    settings.librarys = ['4698805854574104939']
    querier.apply_settings(settings)
    return querier


def query_get_art(querier, url, retrieved_arts):
    """Takes querier and a url and returns the querier with the article added.
    """
    # check if already retrieved before running query
    if re.sub('https*:\/\/', '', url) in retrieved_arts:
        print('Already Retrieved')
        return querier, None

    query = sr.SearchScholarQuery()
    query.set_words(url)
    querier.query=query
    send_query(querier)

    if len(querier.articles) == 0:
        Error = 'no return from query'
    else:
        Error = None
    return querier, Error


def citerecursion(querier, retrieved_arts, regex, reflags, maxdepth,
                  filename, cont=False):
    """Takes a querier with a min of one article and
    gets all citing articles that fit search terms upto a max depth.
    """

    depth = -1
    while depth < maxdepth:
        print('pre len:', len(querier.articles))
        if not cont:
            querier, retrieved_arts, Error = (
                    check_write_articles(querier, regex, reflags, filename,
                                         retrieved_arts))
            print('post len:', len(querier.articles))
        cont = False
        depth += 1
        if depth < maxdepth:
            querier, Error = recursion(querier, regex, reflags)
            if Error is not None:
                return retrieved_arts, Error
        if Error is not None:
            return retrieved_arts, Error
        elif len(querier.articles) == 0:
            print('No more articles to retrieve')
            return retrieved_arts, Error
    print('Hit Max Depth')
    return retrieved_arts, Error

def check_write_articles(querier, regex, reflags, filename, retrieved_arts):
    delete = []
    # add break between  querier sets for restart
    append_csv(["####################", "", "", "", "", "", "", "", "", "",],
               filename)
    for i, art in enumerate(querier.articles):
        if art['url'] is not None:
            if re.search(regex, art['title']+art['excerpt'], reflags) is None:
                print('Non match:', art['url'])
                write_data(art, filename + '_nomatch')
                delete.append(i)
            elif re.sub('https*:\/\/', '', art['url']) in retrieved_arts:
                # write anyway to record articles it cites
                # remove citation url so on restart wont open
                print('Already:', art['url'])
                art['url_citations'] = ""
                write_data(art, filename)
                delete.append(i)
            else: # good article
                print('Retrieved:', art['url'])
                write_data(art, filename)
                retrieved_arts.append(re.sub('https*:\/\/', '', art['url']))
        else:
            delete.append(i)

    # get rid of bad apples
    for i in sorted(delete, reverse=True):
        del querier.articles[i]
    # remove the temp file if it exist
    if os.path.exists('GS_temp.csv'):
        os.remove('GS_temp.csv')
    # check if bad response or just out of good articles
    if len(querier.articles) == 0:
        if len(delete) > 0:
            return querier, retrieved_arts, None
        else: # utoh
            return querier, retrieved_arts, 'something went wrong'

    return querier, retrieved_arts, None


def write_data(art, filename):
    # hack need to implement in scholar.py
    if art['cites'] is None:
        art['cites'] = ""
    #print([item[1] for item in art.attrs.values()])
    items = sorted(list(art.attrs.values()), key=lambda item: item[2])
    # Find largest label length:
    res = []
    for item in items:
        if item[0] is not None:
            res.append(unicode(item[0]).encode('utf-8'))
                    #re.sub(r'[^\x00-\x7F]+',' ', u"%s" % item[0]))
            # add to list and get rid on non ASCII chars
        else:
            res.append('')
    append_csv(res, filename)
    # Bibtex
    if art.citation_data is not None:
        with open(filename + '.bib', 'ab') as f:
            f.write(art.citation_data)


def append_csv(data, filename):
    with open(filename + '.csv', 'ab') as f:
        writer = csv.writer(f)
        writer.writerow(data)


def recursion(querier, regex, reflags):
    querier_2 = set_up_querier()
    Error = None
    querier_2 = retrieve_arts_from_file('GS_temp', querier_2, False)

    for art in querier.articles:
        print('Retriving from:', art['url_citations'], art['num_citations'])
        if any(art['url'] in got_arts['cites'] for got_arts in querier_2.articles):
            print('Already Retrieved')
            continue
        if art['url_citations'] is None:
            print('no citations')
            continue
        querier_2, Error = get_citations(querier_2, art)
        if Error is not None:
            return querier, Error
        else:  # Save temp file for restart
            if os.path.exists('GS_temp.csv'):
                os.remove('GS_temp.csv')
            print('Saving Temp')
            append_csv(["####################"], 'GS_temp')
            for art in querier_2.articles:
                write_data(art, 'GS_temp')

    return querier_2, Error


def get_citations(self, art):
    """ here self is a querier object"""
    url_citations = art['url_citations']
    num_citations = int(art['num_citations'])
    url = art['url']
    num_arts = len(self.articles)
    print('start:', num_arts)
    result = 0 # start with result 0
    retrieved = ""
    while len(self.articles)-num_arts < num_citations:
        # this is a workaround to fetch all the citations, ought to be better integrated at some point
        # get all pages
        sleep(randint(90, 300))  # 1800,3600))

        self = send_query(self, url_citations+'&start='+str(result))

        if retrieved == self.articles[-1]['url']:
            return self, 'blocked?'
        retrieved = self.articles[-1]['url']
        result += 10
        print('retrieved:', len(self.articles)-num_arts)
        print('needed:', num_citations)
    for art in self.articles[num_arts:]:
        art['cites'] = url

    return self, None

def send_query(self, url=None):

    if not url:
        self.clear_articles()
        query = self.query
        url=query.get_url()
        print(url)

    (html, encoding) = self._get_http_response(url=url,
                                    log_msg='dump of query response HTML',
                                    err_msg='results retrieval failed')
    if html is None:
        return self,  'request error'
    if "not a robot" in html.decode('utf-8') or "HTTP 503" in html.decode('utf-8'):
        return self, 'blocked'
    if "Sorry, no information" in html.decode('utf-8'):
        "solve http(s) error - still not sure what causes this"
        if 'https' in query.words:
            query.set_words('http' + query.words[5:])
        else:
            query.set_words('https' + query.words[4:])
        querier.query=query
        send_query(self)

    self.parse(html, encoding)
    return self


def make_csv_backup(filename):
    i = 1
    while os.path.exists(filename + '_backup'+ str(i) +'.csv'):
        i += 1
    with open(filename + '.csv', 'rb') as f:
        reader = csv.reader(f)
        with open(filename + '_backup'+ str(i) +'.csv', 'wb') as f:
            writer = csv.writer(f)
            writer.writerows(reader)

def retrieve_arts_from_file(filename, querier, rm_no_cite=True, All=False):
    try:
        with open(filename + '.csv', 'rb') as f:
            reader = csv.reader(f)
            rows = [row for row in reader]
    except:
        print('No file:', filename)
        return querier

    breaks = []
    for i, row in enumerate(rows):
        if "##########" in row[0].decode('utf-8'):
            breaks.append(i)
    if All:
        for i in breaks[::-1]:
            del rows[i]
        search = rows
    else:
        search = rows[breaks[-1]+1:]

    for row in search:
        art = sr.ScholarArticle()
        art.attrs['cites'] = [None, 'cites', 12]  # add my extra column
        for key in art.attrs.keys():
            art[key] = row[art.attrs[key][2]].decode('utf-8')
            art['url_citation'] = None  # keep from trying to load bib

        if art['url'] not in [row['url'] for row in querier.articles]:
            # Don't add if already added
            if (art['url_citations'] is not None and
                art['url_citations'] <> ""):
                querier.add_article(art)
                # print('added:', art['url'])
            elif rm_no_cite is False and art['url'] is not None:
                querier.add_article(art)
                # print('added2:', art['url'])

    print('loaded:', len(querier.articles))
    return querier

def check_for_new(filename):
    """check if an previous recursion has new citations"""

    querier = set_up_querier()
    querier_2 = set_up_querier()
    retrieve_arts_from_file(filename, querier, rm_no_cite=False, All=True)
    for art in querier.articles:
        print(art['url'])
        querier_2, Error = query_get_art(querier_2, art['url'], [])
            print(querier_2.articles[0]['num_citations'], art['num_citations'])
        if querier_2.articles[0]['num_citations'] > art['num_citations']:
            print('do the rec')
        else:
            print('nothing new')
        print('\n' + '#'*30 + '\n')




def main():
    # 2 cites deep
    #urls = ["http://www.sciencedirect.com/science/article/pii/S0272884214007160"]
    #PDF and OSU
    #url = "http://archpsyc.jamanetwork.com/article.aspx?articleid=492295"
    #url = "http://ieeexplore.ieee.org/abstract/document/7002925/"
    #regex = "[\s\S]*"  # everything
    #"""
    with open('urls.txt', 'r') as f:
        content = f.readlines()
    urls = [url.strip() for url in content]
    #"""
    regex = "(?=.*film)(?=.*bi)(?=.*na)"
    #regex = "film"
    # | is or,
    reflags = re.IGNORECASE
    maxdepth = 20
    filename = 'test'  # leave off extension writes a csv and a bib

    filename  = os.path.abspath(os.path.join(os.path.dirname( __file__ ),
                                           'out', filename))

    fresh = False
    if fresh:
        if os.path.exists(filename + '.csv'):
            os.remove(filename + '.csv')
        if os.path.exists(filename + '.bib'):
            os.remove(filename + '.bib')

    retrieved_arts = get_retrieved_arts(filename)
    #print(retrieved_arts)

    for url in urls:
        cont = False
        Error = None
        print('\n' + '#'*30 + '\n')
        print('url:', url)
        #if 'pickle' in url:
            #restart a search using saved pickle
        #    with open('CR_querier.pkl', 'rb') as input:
        #        querier = pickle.load(input)
        if '#' in url[0]:
            continue
        elif 'continue' in url:
            cont = True
            querier = set_up_querier()
            make_csv_backup(filename)
            querier = retrieve_arts_from_file(filename, querier)
        # if starting from article url
        else:
            querier = set_up_querier()
            querier, Error = query_get_art(querier, url, retrieved_arts)

        if querier is not None:
            if len(querier.articles) > 0:
                retrieved_arts, Error = citerecursion(querier, retrieved_arts,
                                                     regex, reflags, maxdepth,
                                                     filename, cont)
        else:
            print('bad query')
            break
        if Error is not None:
            print(Error)
            break


    # make take multiple inputs
    # Get osu data -> add to scholar done?
    # chage retrieved articles to scholar.articles object

if __name__ == '__main__':

    filename = 'test'  # leave off extension writes a csv and a bib

    filename  = os.path.abspath(os.path.join(os.path.dirname( __file__ ),
                                           'out', filename))
    check_for_new(filename)

    #main()
