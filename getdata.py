#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Retrieves data from extracted txt files (files) given a text file (wordfn)
with '/n' delimited regex to search for in the file.
Will automatically remove headers (##) and comments (#) from the file.
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
#import re
import regex as re
import csv
import time

from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog


def get_datafiles(supported_datafiles, location):
    """Qt file dialogue widget
    """
    types = ' '.join([row[0] for row in supported_datafiles])
    filetypes = 'Supported (' + types + ')'
    app = QApplication(sys.argv)
    widget = QWidget()
    files, _ = QFileDialog.getOpenFileNames(
                        widget,
                        'Program to run',
                        location,
                        filetypes + ';;All files (*.*)',
                        None,
                        QFileDialog.DontUseNativeDialog)
    return files


def get_sentance(string, positions):
    """ Find beginning and end of strings
    complex regex left for examples
    may need to add exceptions for things like et al., Mr., etc.
    see -
    http://stackoverflow.com/questions/3965323/making-regular-expression-more-efficient
    sped up with compile.search
    http://www.diveintopython.net/performance_tuning/regular_expressions.html
    tested on https://regex101.com
    how long can a sentance be??
    https://sites.google.com/a/brown.edu/predicting-genre-of-academic-writing/
    """
    #positions = [50]
    #string = ("This is a test.13 a really 1.3 awesome 1.2 of the greatest"
    #          "xx   proportions.[2-4] I really try.")
    # some journals use numbers right after . for refs so this make it more complex
    # re_end = re.compile('(?:.(?![^\d][.?!][\s\d]))*..[.?!]\d{0,2}-?\d{0,2}',
    #                    flags=re.I)
        #
           # '[^\d]\[?\d{0,2}(?:-\d{1,2})?\]?[.?!](?!\d\s)'
           #             '\[?\d{0,2}(?:-\d{1,2})?\]?\s'

    re_end = re.compile('[.?!](?<!(?:ref|fig)\.)(?!\d\s)'
                        '\[?\d{0,2}(?:-\d{1,2})?\]?\s',  # {e<0}',
                        flags=re.I).search
    # re_beg = re.compile('(?:.(?!\d{0,2}-?\d{0,2}[.?!][^\d]))*', flags=re.I)
    re_beg = re.compile('\s\]?(?:\d{1,2}-)?\d{0,2}\[?[.?!][^\d]',
                        # '\]?\d{0,2}-?\d{0,2}\[?[^\d]', #  {e<2}',
                        flags=re.I).search


    sentance = []

    for i, position in enumerate(positions):
        end_add = min([len(string[position:]), 400])
        beg_add = min([len(string[:position]), 400])
        end_str = string[position:position+end_add]
        beg_str = string[position:position-beg_add:-1]  # Backwards for faster regex
        #print(beg_str)
        #print('\n')
        #print(end_str)
        m_end = re_end(end_str)
        m_beg = re_beg(beg_str)
        if m_end is None:
            #print('end none')
            end_act = end_add
        else:
            end_act =m_end.end()
        if m_beg is None:
            #print('beg none')
            beg_act = beg_add
        else:
            beg_act = m_beg.start()
        end = position + end_act
        beg = position - beg_act + 1

        sentance.append([beg])
        sentance[i].append(end)
        sentance[i].append(string[beg: end])
    return sentance


def find_fuzzy_key_words(string, wordlist):
    """Return word positions
    http://stackoverflow.com/questions/34780253/efficiently-string-searching-in-python

    from curses.ascii import isascii
    from unicodedata import normalize
    deaccentuate = lambda t: filter(isascii, normalize('NFD', t).encode('utf-8'))
    """

    #re_rmvcmts =  re.compile(r'\s*#.*', re.DOTALL) # remove #
    #wordlist = [re.sub(re_rmvcmts, "", word).strip() for word in wordlist]
    #wordlist = filter(None, wordlist) # remove none
    # fuzzy - https://pypi.python.org/pypi/regex/#additional-features

    wordlist = filter(None, wordlist) # remove none
    rs = r'|'.join(['(?:%s){e<%d}' %
                   (p, round(len(p)*0.2)) for p in wordlist])
    r = re.compile(rs)
    matches = []
    for m in r.finditer(string): matches.append([m.start(), m.string[m.start(0):m.end(0)]])
    return matches


def find_refs_in_text(string):
    # this same scheme can work for refs too eg match \.[\d]|[^\d]\.\d and all other perms
    # then go back and get the sentance.

    pass

def main(files=None, wordfn=None, save=True):
    """doc string
    """
    if wordfn is None:
        wordfn = get_datafiles('Keyword File', '*.txt', False)
        print(wordfn)
    if files is None:
        files = get_datafiles('*.txt', None)
        print(files)

    with open(wordfn, 'r') as f:
        wordlist = f.readlines()


    headers = [['File']]
    terms = []
    temp = []
    re_rmvcmts =  re.compile(r'\s*#.*', re.DOTALL)  # remove '# comment'
    for line in wordlist:
        if line[0:2] == '##':  # check if header
            headers[0].append(line[2:].strip())
            if len(temp) > 0:
                terms.append(temp)
            temp = []
        elif line[0] != '#' and line.strip() != "":  # if not a comment line or header
            temp.append(re.sub(re_rmvcmts, "", line).strip())

    if len(temp) > 0:
        terms.append(temp)

    headers[0].append("Figures")
    headers[0].append("Tables")
    headers[0].append("Pt?")

    for f, filename in enumerate(files):
        with open(filename, 'r') as fn:
            # Read the file contents and generate a list with each line
            string = fn.readlines()

        headers.append([os.path.basename(filename)[:-4]] +
                        [""]*(len(headers[0])-1))
        cont = 0
        for line in string:
            line = line.strip()
            if 'References' in line[0:12]:
                cont = 1
                continue

            if cont == 1:
                cont = 0
                continue

            if cont == 5 or not line:
                continue

            if 'Tables' in line[0:8]:
                cont = 4
                continue

            if 'Table' in line[0:8] and cont == 4:
                headers[f+1][-2] += line + '\r\n'
                continue

            if 'Headers' in line[0:10]:
                cont = 5
                continue

            if 'Figures' in line[0:9]:
                cont = 3
                continue

            if cont == 3:
                headers[f+1][-3] += line + '\r\n'
                continue

            for i, term in enumerate(terms):
                data = []
                matches = find_fuzzy_key_words(line, term)
                #print(line[0:10], len(matches))
                positions = [row[0] for row in matches]
                sentances = get_sentance(line, positions)
                for j, match in enumerate(matches):
                    # look for duplicates
                    if not sentances[j][0:2] in [row[0:2] for row in data]:
                        data.append(sentances[j])
                        if "Substrates" in headers[0][i+1]:
                            if "Pt" in sentances[j][2]:
                                headers[f+1][-1] = 'Yes'
                        headers[f+1][i+1] += sentances[j][2] + '\r\n'
                        #data.append('New Line')

    if save:
        savepath = os.path.join(os.path.dirname(filename), '_matches.csv')
        if not os.path.exists(savepath):
            with open(savepath, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(headers[0])
        with open(savepath, 'a') as f:
            writer = csv.writer(f)
            writer.writerows(headers[1:])

    return headers


if __name__ == '__main__':
    """
    files = []
    files.append(os.path.join(exfiles,
        'Yueqiu et al_2012_Large piezoelectric response of Bi sub0.txt'))
    files.append(os.path.join(exfiles,
        'Yu et al_2007_The synthesis of lead-free ferroelectric Bisub0.txt'))
    files.append(os.path.join(exfiles,
        'Cheng et al_2004_Combinatorial studies of (1−x)Na0.txt'))
    savepath = os.path.join(exfiles, 'test.csv')
    """

    exfiles = os.path.abspath(os.path.join(os.path.dirname( __file__ ),
                                           'examplefiles'))
    wordfn = os.path.join(exfiles, os.pardir, 'find_these.txt')
    data = main(wordfn=wordfn)

    print('done')
    #"""

    #sentance = "This is a test.12-12 ar eally awesome te 3.3  ref. st. of the greatest proportions. I really try."
    #print(get_sentance(sentance, [20]))

