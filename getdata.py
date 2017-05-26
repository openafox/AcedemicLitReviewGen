#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This is my doc string.

Keyword arguments:
A -- apple
"""
# Copyright 2015 Austin Fox
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
from PyQt4 import QtGui

def get_datafiles(title=None, filetypes=None, multi=True):
    """Qt file dialogue widget
    """
    if filetypes is None:
        filetypes = 'All(*.*)'
    else:
        filetypes = 'Suported (' + filetypes + ')'

    app = QtGui.QApplication(sys.argv)
    widget = QtGui.QWidget()
    # Set window title
    widget.setWindowTitle("Hello World!")
    notnative = QtGui.QFileDialog.DontUseNativeDialog
    if multi:
        if title is None:
            title = 'Open Files'
        out = QtGui.QFileDialog.getOpenFileNames(widget,
                                                 title, '',
                                                 filetypes,
                                                 None,
                                                 notnative)
        out = [str(f) for f in out]
    else:
        out = QtGui.QFileDialog.getOpenFileName(widget,
                                                title, '',
                                                filetypes,
                                                None,
                                                notnative)
        out = str(out)
    app.exit()
    return out


def get_sentance(string, positions):
    """ Find beginning and end of strings
    complex regex left for examples
    may need to add exceptions for things like et al., Mr., etc.
    see - http://stackoverflow.com/questions/3965323/making-regular-expression-more-efficient
    sped up with compile.search
    http://www.diveintopython.net/performance_tuning/regular_expressions.html
    tested on https://regex101.com
    how long can a sentance be??
    https://sites.google.com/a/brown.edu/predicting-genre-of-academic-writing/
    """
    positions = [50]
    string = ("This is a test.13 a really 1.3 awesome 1.2 of the greatest"
              "xx   proportions.[2-4] I really try.")
    # some journals use numbers right after . for refs so this make it more complex
    # re_end = re.compile('(?:.(?![^\d][.?!][\s\d]))*..[.?!]\d{0,2}-?\d{0,2}',
    #                    flags=re.I)
    #
    re_end = re.compile('[^\d]\[?\d{0,2}(?:-\d{1,2})?\]?[.?!]'
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
    re_rmvcmts =  re.compile(r'\s*#.*', re.DOTALL)
    wordlist2 = [re.sub(re_rmvcmts, "", word).strip() for word in wordlist]
    wordlist2 = filter(None, wordlist2)
    # fuzzy - https://pypi.python.org/pypi/regex/#additional-features
    rs = r'|'.join(['(?:%s){e<%d}' %
                   (p, round(len(p)*0.2)) for p in wordlist2])
    r = re.compile(rs)
    matches = []
    for m in r.finditer(string): matches.append([m.start(), m.string[m.start(0):m.end(0)]])
    return matches

def test3():
    r = re.compile('|'.join('(?:%s)' % p for p in patterns))
    for s in strings:
        r.match(s)

    [m.start() for m in re.finditer('test', 'test test test test')]

def find_refs_in_text(string):
    # this same scheme can work for refs too eg match \.[\d]|[^\d]\.\d and all other perms
    # then go back and get the sentance.

    pass

def main(files=None, wordfn=None):
    """doc string
    """
    if wordfn is None:
        wordfn = get_datafiles('Keyword File', '*.txt', False)
        print(wordfn)
    if files is None:
        files = get_datafiles(filetypes='*.txt')
        print(files)

    with open(wordfn, 'r') as f:
        wordlist = f.readlines()

    for fn in files:
        with open(fn, 'r') as f:
            # Read the file contents and generate a list with each line
            string = f.readlines()

    for line in string:
        matches = find_fuzzy_key_words(line, wordlist)
        positions = [row[0] for row in matches]
        sentances = get_sentance(line, positions)
        data = []
        for i, match in enumerate(matches):
            if data is not []:
                if not sentances[i][0] in [row[2] for row in data]:
                    data.append(match + sentances[i])
        return data


if __name__ == '__main__':
    files = ['/Users/towel/_The_Universe/_Materials_Engr/__Thesis/Scripts/AcedemicLitReviewGen/examplefiles/Yueqiu et al_2012_Large piezoelectric response of Bi sub0.txt']
    wordfn = '/Users/towel/_The_Universe/_Materials_Engr/__Thesis/Scripts/AcedemicLitReviewGen/find_these.txt'
    #data = main(files, wordfn)
    #print(len(data))
    #for match in data:
    #    print(match)
    #    print('\n')
    sentance = "This is a test.12-12 ar eally awesome test. of the greatest proportions. I really try."
    print(get_sentance(sentance, [20]))
