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
import copy
import numpy as np
import re
import csv
from random import randint
import time
from datetime import datetime
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
    # make the cookie file
    # must be exact or it will block you :( - do the settings that you want
    # then copy the cookie file
    dt = datetime(2020, 3, 8, 9, 48, 53).strftime('%s')
    with open(cookiefile, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        f.write('.scholar.google.com	TRUE	/	FALSE	'
                '%s	GSP	'
                'IN=7e6cc990821af63+e0018ca3a198427c+41358307866a516b:'
                'LD=en:' # CF=4:'
                'A=6SqDRw:CPTS=1520718128:'
                'LM=1520718128:S=yreLNDvHLMRUyRUX'
                % dt)

    scholar.ScholarConf.LOG_LEVEL = 4
    scholar.ScholarConf.USER_AGENT = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36")
            #"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:57.0) Gecko/20100101 Firefox/57.0")


    querier = scholar.ScholarQuerier()
    settings = scholar.ScholarSettings()
    settings.set_citation_format(0)

    # not needed in cookies
    # scholar.ScholarConf.MAX_PAGE_RESULTS = 10
    # settings.set_citation_format(sr.ScholarSettings.CITFORM_BIBTEX)
    # WorldCat
    # 569367360547434339
    #settings.librarys = ['4698805854574104939']
    # querier.apply_settings(settings)

    #sleep(20)  # delay next call - stop being blocked
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
    append_csv(["#"*20] + ['']*11, filename) #edit to only add if there are arts?
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
    # make copy to help from being blocked
    #querier_2 = copy.deepcopy(querier)
    querier_2 = set_up_querier()  # would be good to get above working
    querier_2.clear_articles()
    querier_2.query = None
    error = None

    querier_2 = retrieve_arts_from_file('GS_temp', querier_2, False)

    for art in querier.articles:
        if art['url_citations'] is None:
            print('no citations')
            continue
        print('Retriving from:', art['url_citations'], art['num_citations'])

        if any(art['url'] in got_arts['cites'] for got_arts in querier_2.articles):
            # check if art was retrieved and all citing articles were saved
            print('Already Retrieved')
            continue

        querier_2, error = get_citations(querier_2, art)
        if error is not None:
            # if didn't finish retriving from art
            #(add another temp here? could be helpful for lots of cites
            return querier_2, error
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
    result = -10 # start with result 0
    retrieved = ""
    while len(self.articles)-num_arts < num_citations:
        result += 10  # start at 0
        if num_citations//10 < result//10:
            if 'scisbd' in url_citations:
                _add_cites(self, url, num_arts)
                return self, 'New Not! Check manually? (trying next page)'
            return self, ('blocked?\nNumber of citations = %d but atempting to'
                          'retrieve page %d') % (num_citations, result)
        # this is a workaround to fetch all the citations, ought to be better integrated at some point
        # get all pages
        sleep(randint(100, 500))  # 1800,3600))

        self, error = send_query(self, url_citations+'&start='+str(result))

        if error:
            return self, error
        if not len(self.articles):
            if 'scisbd' in url_citations:
                _add_cites(self, url, num_arts)
                return self, 'New = Not! Check manually? (no arts)'
            return self, 'Blocked? Nothing retrieved. (no arts)'
        if retrieved == self.articles[-1]['url']:
            if 'scisbd' in url_citations:
                _add_cites(self, url, num_arts)
                return self, 'New = Not! Check manually? (nothing retrieved)'
            return self, 'Blocked? Nothing retrieved.'
        retrieved = self.articles[-1]['url']
        print('retrieved:', len(self.articles)-num_arts)
        print('needed:', num_citations)

    _add_cites(self, url, num_arts)
    return self, error


def _add_cites(self, url, num_arts):
    """add the extra 'cites' key to arts"""
    for art in self.articles[num_arts:]:
        art['cites'] = url
    return self

def send_query(self, url=None, http=0):
    """Send query to web.
    self = querier object.
    With no url specified url will be retrieved from the querier object."""

    error = None
    if not url:
        self.clear_articles()
        query = self.query
        url=query.get_url()

    # print(self.cjar)
    # print(url)

    (html, encoding) = self._get_http_response(url=url,
                                    log_msg='dump of query response HTML',
                                    err_msg='results retrieval failed')
    if html is None:
        return self, 'request error'
    if "not a robot" in html.decode('utf-8') or "HTTP 503" in html.decode('utf-8'):
        return self, 'blocked - detected - do captcha?'
    if "Sorry, no information" in html.decode('utf-8'):
        "solve http(s) error - still not sure what causes this"
        print('switching http(s)')
        if 'https' in query.words:
            self.query.set_words('http' + query.words[5:])
        else:
            self.query.set_words('https' + query.words[4:])
        if http > 0:
            return self, 'New Not! This link no longer works, check manually'
        else:
            sleep(randint(60, 300))
            self, error = send_query(self, http=1)

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
    #querier_a = copy.deepcopy(querier)  # only one request stop being blocked
    querier_a = set_up_querier()  # would be good to get above working
    # for posible continue
    querier_b = set_up_querier()

    querier = retrieve_arts_from_file(filename, querier, rm_no_cite=False, All=True)

    filename = filename + '_new'
    if os.path.exists(filename + '.csv'):
        retrieved_arts = get_retrieved_arts(filename)
    else:
        retrieved_arts = []  # fresh new check retrieval

    # Continue?
    querier_b = retrieve_arts_from_file(filename, querier_b)
    if (len(querier_b.articles) > 0 and
        re.sub('https*:\/\/', '', querier_b.articles[0]['url']) not in
        [re.sub('https*:\/\/', '', art['url']) for art in querier.articles]):
        print('Continuing where left off')
        depth = 1
        while depth < maxdepth:
            querier_b, error = recursion(querier_b)
            if error:
                print(error)
                return retrieved_arts, error
            if len(querier_b.articles) < 1:
                print('No more articles to retrieve, Continuing')
                break
            new_check_write(querier, querier_b, regex, reflags, None,
                            filename, retrieved_arts, depth)
            depth += 1

    len_arts = len(querier.articles)
    # loop through all original articles
    for i, art in enumerate(querier.articles):
        print('\n', i, len_arts, '#'*30, '\n')
        print(art['url'])
        if re.sub('https*:\/\/', '', art['url']) in retrieved_arts:
            print('Already Retrieved')
            continue

        querier_a, error = query_get_art(querier_a, art['url'], [])

        if error:
            print(error)
            if 'New' in error:
                art['url_citations'] = error
                new_check_write(querier, querier_a, regex, reflags, art,
                                filename, retrieved_arts, 0)
                print('Continuing')
                continue
            return retrieved_arts, error

        sleep(randint(200, 800)) # may not be needed - not blocked fast


        # make number the diff
        num = (int(querier_a.articles[0]['num_citations']) -
               int(art['num_citations']))

        print('error?', error, '|', 'citers new:',
              querier_a.articles[0]['num_citations'], '|', 'citers old:',
              art['num_citations'], '|', 'Diff:', num)
        # for recording
        art['num_citations'] = querier_a.articles[0]['num_citations']

        # tricking to only get new
        querier_a.articles[0]['num_citations'] = num

        if num < 0:
            print('weird lost citations?', num)
            art['url_citations'] = 'weird lost citations?'
            new_check_write(querier, querier_a, regex, reflags, art,
                            filename, retrieved_arts, 0)
            print('Continuing')
            continue
        elif int(num) == 0:
            print('nothing new')
            # Write art data to new file for continuation ease
            append_csv(["#"*20] + ['']*11, filename)  # double for
            append_csv(["#"*20] + ['']*11, filename)  # better delim
            write_data(art, filename)
            continue

        #set up for extraction - trick into only grabbing new
        # get sorted from the last year newist first
        querier_a.articles[0]['url_citations'] += '&scipsc=&q=&scisbd=1'

        # Do Recursion to get new citations
        cont = True  # Always skip check on first go for new art
        depth = -1
        while depth < maxdepth:
            print('pre len:', len(querier_a.articles))
            if not cont:
                querier_a = new_check_write(querier, querier_a, regex, reflags,
                                    art, filename, retrieved_arts, depth)
            cont = False
            depth += 1
            if depth < maxdepth:
                # Do recursion
                querier_a, error = recursion(querier_a)
                if error:
                    if 'New' in error:
                        print(error)
                        art['url_citations'] = error
                        querier_a =  new_check_write(querier, querier_a, regex,
                                reflags, art, filename, retrieved_arts, depth)
                        if len(querier_a.articles) < 1:
                            print('Continuing')
                            break  # move to next article
                        else:
                            cont = True # don't repeat check
                    else:
                        print(error)
                        return retrieved_arts, error

            if error:
                if 'New' not in error:
                    print(error)
                    return retrieved_arts, error
            elif len(querier_a.articles) < 1:
                print('No more articles to retrieve, Continuing')
                break  # move to next article
        if depth >= maxdepth:
            print('Hit Max Depth')
        else:
            print('Continuing')


def new_check_write(querier, querier_a, regex, reflags, art_0,
                    filename, retrieved_arts, depth):
    """ check write for check_for_new"""
    print('pre2 len:', len(querier_a.articles))
    if depth < 1:
        # Write art data to new file
        append_csv(["#"*20] + ['']*11, filename)  # double for
        append_csv(["#"*20] + ['']*11, filename)  # better delim
        write_data(art_0, filename)
    # only keep proper number on citers
    # querier_a.articles = querier_a.articles[0:num+1]
    # better to compair to list of original
    delete = []
    for i, art in enumerate(querier_a.articles):
        if (re.sub('https*:\/\/', '', art['url']) in
            [re.sub('https*:\/\/', '', row['url']) for
            row in querier.articles]):
            print('Already:', art['url'])
            delete.append(i)
    # get rid of bad apples in querier
    for i in sorted(delete, reverse=True):
        print('deleting', i)
        del querier_a.articles[i]

    print('post2 len:', len(querier_a.articles))
    # check if meets re terms and has not been retrieved
    if len(querier_a.articles) > 0:
        querier_a, retrieved_arts, error = (
                check_write_articles(querier_a, regex, reflags,
                                     filename, retrieved_arts))
        print('post len:', len(querier_a.articles))
    # everything has been written make sure temp is deleted
    if os.path.exists('GS_temp.csv'):
        os.remove('GS_temp.csv')
    return querier_a


def main(filename, urls, regex, reflags, maxdepth):
    """execute a normal search - should update and make options to run from
    python, ie make real package."""

    # 2 cites deep
    #urls = ["http://www.sciencedirect.com/science/article/pii/S0272884214007160"]
    #PDF and OSU
    #url = "http://archpsyc.jamanetwork.com/article.aspx?articleid=492295"
    #url = "http://ieeexplore.ieee.org/abstract/document/7002925/"
    #regex = "[\s\S]*"  # everything
    #"""

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
            print(error)
            break


    # make take multiple inputs
    # Get osu data -> add to scholar done?
    # chage retrieved articles to scholar.articles object

if __name__ == '__main__':

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
    # Start from already retrieved
    # (must have only been from past year else will not work)
    check_for_new(filename, regex, reflags, maxdepth)

    # Run citerecursion (will pick up where left off)
    # main(filename, urls, regex, reflags, maxdepth)
