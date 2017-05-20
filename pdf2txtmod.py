#!/usr/bin/env python
"""Bunch of tools to make life easier
"""
# Copyright 2017 Austin Fox
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
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter, PDFPageAggregator
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams, LTContainer, LTText, LTTextBox, LTImage
from pdfminer.layout import LTPage, LTTextLine, LTChar, LTAnno, LTFigure
from pdfminer.image import ImageWriter
from PyQt4 import QtGui

import matplotlib.mlab as mlab
import matplotlib.pyplot as plt


class TextCon(PDFPageAggregator):
    """ Modified from http://stackoverflow.com/questions/15737806/extract-text-using-pdfminer-and-pypdf2-merges-columns
    """
    def __init__(self, rsrcmgr, pageno=1, laparams=None, imagewriter=None,
            imagename = None):
        PDFPageAggregator.__init__(self, rsrcmgr, pageno=pageno, laparams=laparams)
        self.rows = []
        self.page_number = 0
        self.imagewriter = imagewriter
        self.imagename = str(imagename)


    def receive_layout(self, ltpage):
        def render(item, page_number):
            if isinstance(item, LTPage) or isinstance(item, LTTextBox):
                for child in item:
                    render(child, page_number)
            elif isinstance(item, LTFigure):
                # self.outfp.write('<figure name="%s" bbox="%s">\n' % (item.name, bbox2str(item.bbox)))
                for child in item:
                    render(child, page_number)
            elif isinstance(item, LTTextLine):
                child_str = ''
                for child in item:
                    if isinstance(child, (LTChar, LTAnno)):
                        child_str += child.get_text()
                child_str = ' '.join(child_str.split()).strip()
                if child_str:
                    row = (page_number, item.bbox[0], item.bbox[1], item.bbox[2], item.bbox[3], child_str) # bbox == (x1, y1, x2, y2)
                    self.rows.append(row)
                for child in item:
                    render(child, page_number)

            elif isinstance(item, LTImage):
                if self.imagewriter is not None:
                    item.name = self.imagename + item.name
                    self.imagewriter.export_image(item)
        render(ltpage, self.page_number)
        self.page_number += 1
        # sort by page number then the reverse of y
        self.rows = sorted(self.rows, key = lambda x: (x[0], -x[2]))
        self.result = ltpage
        return

    # Some dummy functions to save memory/CPU when all that is wanted
    # is text.  This stops all the image and drawing output from being
    # recorded and taking up RAM.
    def render_image(self, name, stream):
        if self.imagewriter is None:
            return
        PDFPageAggregator.render_image(self, name, stream)
        return

    def paint_path(self, gstate, stroke, fill, evenodd, path):
        return



def get_datafiles():
    """Qt file dialogue widget
    """
    filetypes = 'PDF (*.pdf)'
    app = QtGui.QApplication(sys.argv)
    widget = QtGui.QWidget()
    # Set window title
    widget.setWindowTitle("Hello World!")
    files = QtGui.QFileDialog.getOpenFileNames(widget,
                                               'Program to run', '',
                                               filetypes,
                                               None,
                                               QtGui.QFileDialog.DontUseNativeDialog)
    # Show window
    #widget.show()
    app.exit()
    return files


# main
def main():
    files = get_datafiles()
    # debug option level
    debug = 0
    # input option
    password = ''
    pagenos = set()
    #pagenos.update( int(x)-1 for x in v.split(',') )
    maxpages = 0
    # output option
    rotation = 0
    stripcontrol = False
    layoutmode = 'normal'
    codec = 'utf-8'
    pageno = 1
    scale = 1
    caching = True
    rsrcmgr = PDFResourceManager(caching=caching)
    showpageno = True

    ## Line Agumentation ? Parameters
    laparams = LAParams()
    laparams.all_texts = True
    laparams.detect_vertical = True
    laparams.line_overlap = 0.3  # Line overlap
    laparams.char_margin = 2.0  # Letter Spacing
    laparams.line_margin = 0.5  # Line Spacing
    laparams.word_margin = 0.1  # Word spacing
    laparams.boxes_flow = 0.5  # +-1.0  how much horizontal vs. vertical matters
    #position maters for line continuation
    #
    PDFDocument.debug = debug
    PDFParser.debug = debug
    CMapDB.debug = debug
    PDFPageInterpreter.debug = debug
    #


    for fname in files:
        fname = str(fname)
        imagedir = os.path.abspath(os.path.join(os.path.dirname(fname), 'img'))
        # print(imagedir)
        imagewriter = None
        imagewriter = ImageWriter(imagedir)  # output folder for images
        name = os.path.splitext(os.path.basename(fname))[0]
        print(name)
        outfile = fname[:-4] + '.txt'
        device = TextCon(rsrcmgr, laparams=laparams, imagewriter=imagewriter,
                         imagename=name)

        interpreter = PDFPageInterpreter(rsrcmgr, device)

        fp = file(fname, 'rb')
        for page in PDFPage.get_pages(fp, pagenos,
                                      maxpages=maxpages, password=password,
                                      caching=caching, check_extractable=True):
            page.rotate = (page.rotate+rotation) % 360
            interpreter.process_page(page)

        ### Reoder Data to account for columns
        #x_data = []
        lines = []
        column2 = []
        pagenumber = 0
        previous = [0,0,0,0,0,0]
        max_x = max([row[3] for row in device.rows])
        min_x = min([row[1] for row in device.rows])
        mid_x = (max_x - min_x) / 2

        for row in device.rows:
            if row[0] == pagenumber + 1:
                lines += column2
                column2 = []
                pagenumber += 1

            if row[0] == pagenumber:
                if int(row[1]) < mid_x:
                    lines.append(str(row[5])) # row[5].encode('utf8'))
                    previous = row
                    continue
                if int(row[1]) > mid_x and ((int(previous[1]) < mid_x and
                                           int(previous[3]) < mid_x)
                                          or (int(previous[1]) > mid_x and
                                              int(previous[3]) > mid_x)
                                          or previous[3] > max_x * 0.9):

                    column2.append(str(row[5])) # row[5].encode('utf8'))
                    continue
                else:
                    lines.append(str(row[5])) # row[5].encode('utf8'))
                    previous = row
                    continue
        lines += column2

        with open(outfile, 'w') as f:
            f.write(' '.join(lines))
            #x_data.append(row[1])

    # the histogram of the data
    #n, bins, patches = plt.hist(x_data, 50)
    #plt.show()

    device.close()
    print('Done')
    return

if __name__ == '__main__': sys.exit(main())
    # This looks really good
    # http://www.degeneratestate.org/posts/2016/Jun/15/extracting-tabular-data-from-pdfs/


    # ToDO
    # 1. get rid of header and footer - need to look at html/xml in
    # pdfminer/converter <- not much help really
    # 2. seperate citations
