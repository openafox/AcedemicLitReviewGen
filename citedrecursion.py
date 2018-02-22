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

    # get cookie file from browser - it may be necessary to clear cookies
    # get user agent by searching 'my user agent'
    cookiefile = os.path.abspath(os.path.join(os.path.dirname( __file__ ),
                                           'cookies.txt'))
    # fix error - 5th column remove decimals or replace 0 in with ''
    # http://stackoverflow.com/questions/14742899/using-cookies-txt-file-with-python-requests
    if os.path.exists(cookiefile):
        scholar.ScholarConf.COOKIE_JAR_FILE = cookiefile
    scholar.ScholarConf.LOG_LEVEL = 4
    scholar.ScholarConf.USER_AGENT = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:57.0) Gecko/20100101 Firefox/57.0")

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
    querier, error = send_query(querier)

    if len(querier.articles) == 0 and not error:
        error = 'no return from query'
    return querier, error


def citerecursion(querier, retrieved_arts, regex, reflags, maxdepth,
                  filename, cont=False):
    """Takes a querier with a min of one article, a regex, reflags, and
    gets all citing articles that fit the re terms upto a max depth.
    setting cont=True assumes last run did not finish - skips check against
    retrieved_arts and re terms
    """

    depth = -1
    while depth < maxdepth:
        print('pre len:', len(querier.articles))
        if not cont:
            # remove arts already retrieved or that don't fit re terms
            querier, retrieved_arts, error = (
                    check_write_articles(querier, regex, reflags, filename,
                                         retrieved_arts))
            print('post len:', len(querier.articles))
        cont = False
        depth += 1
        if depth < maxdepth:
            querier, error = recursion(querier)
            if error is not None:
                return retrieved_arts, error
        if error is not None:  #extra?
            return retrieved_arts, error
        elif len(querier.articles) == 0:
            print('No more articles to retrieve')
            return retrieved_arts, error
    print('Hit Max Depth')
    return retrieved_arts, error

def check_write_articles(querier, regex, reflags, filename, retrieved_arts):
    """Check all art in querier against retrieved_arts and re terms. If good
    write to filename. Else write to filename_nomatch.
    """
    delete = []  # for removal of bad apples
    # add break between  querier sets for restart
    append_csv(["#"*20] + ['']*11, filename)
    for i, art in enumerate(querier.articles):
        if art['url'] is not None:
            if re.search(regex, art['title']+art['excerpt'], reflags) is None:
                print('Non match:', art['url'])
                write_data(art, filename + '_nomatch')
                delete.append(i)
            elif re.sub('https*:\/\/', '', art['url']) in retrieved_arts:
                # write already retrieved anyway to record articles it cites
                print('Already:', art['url'])
                art['url_citations'] = ""
                # remove citation url so on restart wont open
                write_data(art, filename)
                delete.append(i)
            else: # good article
                print('Retrieved:', art['url'])
                write_data(art, filename)
                retrieved_arts.append(re.sub('https*:\/\/', '', art['url']))
        else:
            delete.append(i)

    # get rid of bad apples in querier
    for i in sorted(delete, reverse=True):
        del querier.articles[i]
    # remove the temp file if it exist all are now saved to filename
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
    """Write art data to filename"""
    # hack need to implement in scholar.py
    if art['cites'] is None:
        art['cites'] = ""
    # get retrieved data in a sorted list from dic
    items = sorted(list(art.attrs.values()), key=lambda item: item[2])
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
    "Append data to filename.csv"""
    with open(filename + '.csv', 'ab') as f:
        writer = csv.writer(f)
        writer.writerow(data)


def recursion(querier):
    """Retrieve all artcles citing arts in querier.
    returns new (querier, error) containing all citing (new) articles"""
    querier_2 = set_up_querier()
    error = None
    querier_2 = retrieve_arts_from_file('GS_temp', querier_2, False)

    for art in querier.articles:
        print('Retriving from:', art['url_citations'], art['num_citations'])

        if any(art['url'] in got_arts['cites'] for got_arts in querier_2.articles):
            # check if art was retrieved and all citing articles were saved
            print('Already Retrieved')
            continue
        if art['url_citations'] is None:
            print('no citations')
            continue
        querier_2, error = get_citations(querier_2, art)
        if error is not None:
            # if didn't finish retriving from art
            #(add another temp here? could be helpful for lots of cites
            return querier, error
        else:  # Save temp file for restart - allows skiping arts in querier
            if os.path.exists('GS_temp.csv'):
                os.remove('GS_temp.csv')
            print('Saving Temp')
            append_csv(["#"*20] + ['']*11, 'GS_temp')
            for art in querier_2.articles:
                write_data(art, 'GS_temp')

    return querier_2, error


def get_citations(self, art):
    """Retrieve all articles citing art.
    self is a querier object"""
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

        self, error = send_query(self, url_citations+'&start='+str(result))
        if error:
            return self, error
        if retrieved == self.articles[-1]['url']:
            return self, 'blocked?'
        retrieved = self.articles[-1]['url']
        result += 10
        print('retrieved:', len(self.articles)-num_arts)
        print('needed:', num_citations)
    for art in self.articles[num_arts:]:
        art['cites'] = url

    return self, error

def send_query(self, url=None):
    """Send query to web.
    self = querier object.
    With no url specified url will be retrieved from the querier object."""
    error = None
    if not url:
        self.clear_articles()
        query = self.query
        url=query.get_url()

    print(self.cjar)
    print(url)

    (html, encoding) = self._get_http_response(url=url,
                                    log_msg='dump of query response HTML',
                                    err_msg='results retrieval failed')
    if html is None:
        return self, 'request error'
    if "not a robot" in html.decode('utf-8') or "HTTP 503" in html.decode('utf-8'):
        return self, 'blocked'
    if "Sorry, no information" in html.decode('utf-8'):
        "solve http(s) error - still not sure what causes this"
        if 'https' in query.words:
            query.set_words('http' + query.words[5:])
        else:
            query.set_words('https' + query.words[4:])
        self.query=query
        send_query(self)

    self.parse(html, encoding)
    return self, error


def make_csv_backup(filename):
    """Copy an article saved .csv for backup"""
    i = 1
    while os.path.exists(filename + '_backup'+ str(i) +'.csv'):
        i += 1
    with open(filename + '.csv', 'rb') as f:
        reader = csv.reader(f)
        with open(filename + '_backup'+ str(i) +'.csv', 'wb') as f:
            writer = csv.writer(f)
            writer.writerows(reader)

def retrieve_arts_from_file(filename, querier, rm_no_cite=True, All=False):
    """Build querier object from a file containing art data.
    rm_no_cite - remove articles without citation url.
    All - retrieve (True) All non duplicate arts or (False) just last set."""
    try:
        with open(filename + '.csv', 'rb') as f:
            reader = csv.reader(f)
            rows = [row for row in reader]
    except:
        print('No file:', filename)
        return querier

    breaks = []
    for i, row in enumerate(rows):
        if "#"*10 in row[0].decode('utf-8'):
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

def check_for_new(filename, regex, reflags, maxdepth):
    """check if an previous recursion has new citations"""

    querier = set_up_querier()  # store orriginal
    querier_a = set_up_querier()  # for new citations

    querier = retrieve_arts_from_file(filename, querier, rm_no_cite=False, All=True)

    filename = filename + '_new'
    if os.path.exists(filename + '.csv'):
        retrieved_arts = get_retrieved_arts(filename + '_new.csv')
    else:
        retrieved_arts = []  # fresh new check retrieval

    # loop through all original articles
    for art in querier.articles:
        print('\n' + '#'*30 + '\n')
        print(art['url'])

        querier_a, error = query_get_art(querier_a, art['url'], [])
        print('error?', error, 'citers new:',
              querier_a.articles[0]['num_citations'], 'citers old:',
              art['num_citations'])

        #set up for extraction - trick into only grabbing new
        # get sorted from the last year newist first
        art['url_citations'] += '&scipsc=&q=&scisbd=1'
        # make number the diff
        querier_a.articles[0]['num_citations'] = (querier_a.articles[0]['num_citations'] -
                                art['num_citations'])
        num = querier_a.articles[0]['num_citations']
        if num < 0:
            print('weird lost citations?', art['num_citations'])
            continue
        elif num == 0:
            print('nothing new')
            # Write art data to new file for continuation ease
            append_csv(["#"*20] + ['']*11, filename)  # double for
            append_csv(["#"*20] + ['']*11, filename)  # better delim
            write_data(art, filename)
            continue

        # Do Recursion to get new citations
        cont = True  # Always skip check on first go for new art
        depth = -1
        while depth < maxdepth:
            print('pre len:', len(querier_a.articles))
            if not cont:
                if depth == 0:
                    # Write art data to new file
                    append_csv(["#"*20] + ['']*11, filename)  # double for
                    append_csv(["#"*20] + ['']*11, filename)  # better delim
                    write_data(art, filename)
                # only keep proper number on citers
                # querier_a.articles = querier_a.articles[0:num+1]
                # better to compair to list of original
                for i, art in enumerate(querier_a.articles):
                    if (re.sub('https*:\/\/', '', art['url']) in
                        [row['url'] for row in querier.articles]):
                        del querier_a.articles[i]
                # check if meets re terms and has not been retrieved
                querier_a, retrieved_arts, error = (
                        check_write_articles(querier_a, regex, reflags,
                                             filename, retrieved_arts))
                print('post len:', len(querier_a.articles))
            cont = False
            depth += 1
            if depth < maxdepth:
                querier_a, error = recursion(querier_a, regex, reflags)
                if error is not None:
                    return retrieved_arts, error
            if error is not None:  # extra?
                return retrieved_arts, error
            elif len(querier_a.articles) == 0:
                print('No more articles to retrieve')
                return retrieved_arts, error
        print('Hit Max Depth')
        return retrieved_arts, error


def main():
    """execute a normal search - should update and make options to run from
    python, ie make real package."""

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
        error = None
        #if 'pickle' in url:
            #restart a search using saved pickle
        #    with open('CR_querier.pkl', 'rb') as input:
        #        querier = pickle.load(input)
        if '#' in url[0]:
            continue

        print('\n' + '#'*30 + '\n')
        print('url:', url)
        if 'continue' in url:
            cont = True
            querier = set_up_querier()
            make_csv_backup(filename)
            querier = retrieve_arts_from_file(filename, querier)
        # if starting from article url
        else:
            querier = set_up_querier()
            querier, error = query_get_art(querier, url, retrieved_arts)

        if querier is not None:
            if len(querier.articles) > 0:
                retrieved_arts, error = citerecursion(querier, retrieved_arts,
                                                     regex, reflags, maxdepth,
                                                     filename, cont)
        else:
            print('bad query')
            break
        if error is not None:
            print(Error)
            break


    # make take multiple inputs
    # Get osu data -> add to scholar done?
    # chage retrieved articles to scholar.articles object

if __name__ == '__main__':

    #filename = 'test'  # leave off extension writes a csv and a bib

    #filename  = os.path.abspath(os.path.join(os.path.dirname( __file__ ), 'out', filename))
    #check_for_new(filename)

    main()
