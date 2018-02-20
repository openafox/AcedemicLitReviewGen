#!/usr/bin/env python
"""Modifications of PDFMiner to make txt extraction from Acedemic publications
easier
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

import sys
import os
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.converter import PDFPageAggregator
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams, LTContainer, LTText, LTTextBox, LTImage
from pdfminer.layout import LTPage, LTTextLine, LTChar, LTAnno, LTFigure
from pdfminer.image import ImageWriter
from PyQt4 import QtGui

import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import regex as re


class TextCon(PDFPageAggregator):
    """ Modified from
    http://stackoverflow.com/questions/15737806/extract-text-using-pdfminer-and-pypdf2-merges-columns
    """
    def __init__(self, rsrcmgr, pageno=1, laparams=None, imagewriter=None,
                 imagename=None):
        PDFPageAggregator.__init__(self, rsrcmgr, pageno=pageno,
                                   laparams=laparams)
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
                # self.outfp.write('<figure name="%s" bbox="%s">\n' %
                # (item.name, bbox2str(item.bbox)))
                for child in item:
                    render(child, page_number)
            elif isinstance(item, LTTextLine):
                child_str = ''
                for child in item:
                    if isinstance(child, (LTChar, LTAnno)):
                        child_str += child.get_text()
                child_str = ' '.join(child_str.split()).strip()
                if child_str:
                    row = (page_number, item.bbox[0], item.bbox[1],
                           item.bbox[2], item.bbox[3], child_str)
                    # bbox == (x1, y1, x2, y2)
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
        self.rows = sorted(self.rows, key=lambda x: (x[0], -x[2]))
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
    files = QtGui.QFileDialog.getOpenFileNames(
            widget,
            'Program to run', '',
            filetypes,
            None,
            QtGui.QFileDialog.DontUseNativeDialog)
    app.exit()
    return files


# main
def main(files=None):
    if files is None:
        files = get_datafiles()
    # debug option level
    debug = 0
    # input option
    password = ''
    pagenos = set()
    # pagenos.update( int(x)-1 for x in v.split(',') )
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

    # Line Agumentation ? Parameters
    laparams = LAParams()
    laparams.all_texts = True
    laparams.detect_vertical = True
    laparams.line_overlap = 0.3  # Line overlap
    laparams.char_margin = 2.0  # Letter Spacing
    laparams.line_margin = 0.5  # Line Spacing
    laparams.word_margin = 0.1  # Word spacing
    laparams.boxes_flow = 0.5  # +-1.0  how much hor vs. vertical matters
    # position maters for line continuation
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
        try:
            for page in PDFPage.get_pages(fp, pagenos,
                                      maxpages=maxpages, password=password,
                                      caching=caching, check_extractable=True):
                page.rotate = (page.rotate+rotation) % 360
                interpreter.process_page(page)
        except:
            continue

        rows = [list(row) for row in device.rows]

        pages = max([row[0] for row in rows])
        max_y = max([row[4] for row in rows])
        min_y = min([row[2] for row in rows])

        list_0 = [int(row[4]) for row in rows]
        list_1 = []
        [list_1.append(obj) for obj in list_0
                if obj not in list_1 and list_0.count(obj) > pages - 1]
        max_y2 = max(list_1)

        list_0 = [int(row[2]) for row in rows]
        list_1 = []
        [list_1.append(obj) for obj in list_0
                if obj not in list_1 and list_0.count(obj) > pages - 1]
        min_y2 = min(list_1)

        print('max_ys:', max_y-max_y2)
        print('min_ys:', min_y-min_y2)

        # Get max and min the hard way because of stupid headers
        list_0 = [int(row[3]) for row in rows]
        list_1 = []
        [list_1.append(obj) for obj in list_0
                if obj not in list_1 and list_0.count(obj) > 10]
        if list_1:
            max_x = max(list_1)
        else:
            max_x = max([int(row[3]) for row in device.rows])

        list_0 = [int(row[1]) for row in rows]
        list_1 = []
        [list_1.append(obj) for obj in list_0
                if obj not in list_1 and list_0.count(obj) > 10]
        if list_1:
            min_x = min(list_1)
        else:
            min_x = min([int(row[3]) for row in device.rows])
        # Errors if more pics on one side then other
        # mid_x = (sum([(float(row[1]) + float(row[3]))/2 for row in
        #    device.rows])/len(device.rows))
        mid_x = (max_x + min_x)/2
        # mid_x = 595/2  # center of A4 at 72px/in Letter would be 612/2
        l_height = sum([row[4] - row[2] for row in rows])/len(rows)

        # print('max_x:', max_x)
        # print('min_x:', min_x)
        # print('mid_x:', mid_x)
        print('l_height:', l_height)

        column2 = []
        lines = []
        pagenumber = 0
        table_caps = ['\n']
        table_data = []
        table = False

        for i, row in enumerate(rows):
            #l_height = row[4]-row[2]
            l_space = rows[i-1][2]-row[4]

            #print(l_height, l_space, rows[i-1][2], rows[i][4], str(row[5]))
            if row[0] == pagenumber + 1:
                lines += column2
                column2 = []
                pagenumber += 1

            if row[0] == pagenumber:
                if (max_y-min_y) * 0.95 > l_space > 0.8 * l_height:
                    # capture Table (assuming tables will span all columns)
                    if re.match(r"^table", str(row[5]), re.I):
                        table = True
                        table_caps.append(str(row[5]))
                        table_data.append('\n')
                        table_data.append(str(row[5]))
                        table_data.append('\n')
                        continue
                    else:
                        table = False

                # capture table captions multi lines
                elif (table_caps[-1] == str(rows[i - 1][5]) and
                    -2 * l_height < l_space < 0.5 * l_height):
                    table_caps[-1] += str(row[5])
                    table_data[-2] += str(row[5])
                    continue

                if table:
                    # capture table data
                    if int(rows[i-1][2]) == int(rows[i][2]):
                        table_data[-1] += '\t' + str(row[5])
                        continue
                    else:
                        table_data.append(str(row[5]))
                        continue

                elif int(row[1]) > mid_x and (
                        (int(rows[i-1][1]) < mid_x and
                         int(rows[i-1][3]) < mid_x) or
                        (int(rows[i-1][1]) > mid_x and
                         int(rows[i-1][3]) > mid_x) or
                        rows[i-1][3] > max_x * 0.9 or
                        l_space > 2.5 * l_height):
                    """
                        r_space > c_space or
                        previous[3] > max_x * 0.9 or
                        l_space > 2 * l_height):"""
                    if len(column2) > 0:
                        if 1 > (row[2] - column2[-1][2]) > -1:
                            # join if on same line
                            if int(row[1]) < int(column2[-1][1]):
                                column2[-1][5] = row[5] + " " + column2[-1][5]
                            else:
                                column2[-1][5] = column2[-1][5] + " " + row[5]
                        else:
                            column2.append(row)
                    else:
                        column2.append(row)
                    # print(2, str(row[5]))
                else:
                    if len(lines) > 0:
                        if 1 > (row[2] - lines[-1][2]) > -1:
                            # join if on same line
                            if int(row[1]) < int(lines[-1][1]):
                                lines[-1][5] = row[5] + " " + lines[-1][5]
                            else:
                                lines[-1][5] = lines[-1][5] + " " + row[5]
                        else:
                            lines.append(row)
                    else:
                        lines.append(row)
                    # print(3, str(row[5]))
        # add final column
        lines += column2

        fig_caps = ['\n']
        headers = ['\n']
        footers = ['\n']
        supp_info = ['\n']
        new_lines = []
        supp_re = re.compile(r"Corresponding author|Electronic mail|email"
                "|E-mail|^doi|doi:|^keywords|^pacs|^apc", re.I)

        for i, line in enumerate(lines):
            #l_height = lines[i][4]-lines[i][2]
            l_space = lines[i-1][2]-lines[i][4]
            l_space_below = 0
            l_space_2below = 0
            if i + 1 < len(lines):
                l_space_below = lines[i][2] - lines[i+1][4]
            if i + 2 < len(lines):
                l_space_2below = lines[i+1][2] - lines[i+2][4]
            fig = fig_caps[-1]
            print(l_space, l_space_below, l_space_2below, lines[i][2], lines[i][4], str(line[5]))

            # capture figure captions multi lines
            if (fig_caps[-1] == str(lines[i - 1][5]) and
                -2 * l_height < l_space < 0.5 * l_height):
                fig_caps.append(str(line[5]))
                continue
            # capture headers (up to two lines)
            if (lines[i][2] > max_y * 0.95 and
                    (l_space_below > 0.5 * l_height or
                     l_space_2below > 0.5 * l_height)):
                    headers.append('\n')
                    headers.append(str(line[5]))
                    if supp_re.search(str(line[5])):
                        headers.append('\n')
                        headers.append(str(line[5]))
                    else:
                        continue
            # capture supporting info
            if supp_re.search(str(line[5])):
                print(str(line[5]))
                supp_info.append('\n')
                supp_info.append(str(line[5]))
                continue
            if (max_y-min_y) * 0.95 > l_space > 0.5 * l_height:
                # capture figure captions
                if re.match(r"^fig", str(line[5]), re.I):
                    fig_caps.append('\n')
                    fig_caps.append(str(line[5]))
                    continue
                # capture footers
                elif lines[i][2] < min_y + max_y * 0.015:
                    footers.append('\n')
                    footers.append(str(line[5]))
                    continue
                else:
                    string = str(lines[i - 1][5])

                    if (any(string in s for s in fig_caps) or
                        any(string in s for s in headers)): # or
                        #string == footers[-1] or string == supp_info[-1]):
                        pass
                    else:
                        new_lines.append('\n')
            new_lines.append(str(line[5]))


        with open(outfile, 'w') as f:
            f.write(' '.join(new_lines))
            f.write('\n\nFigures')
            f.write(' '.join(fig_caps))
            f.write('\n\nTables')
            #f.write(' '.join(table_caps))
            f.write('\n'.join(table_data))
            f.write('\n\nHeaders')
            f.write(' '.join(headers))
            f.write('\n\nFooters')
            f.write(' '.join(footers))
            f.write('\n\nSupporting Info')
            f.write(' '.join(supp_info))

    # the histogram of the data
    # n, bins, patches = plt.hist(x_data, 50)
    # plt.show()

    device.close()
    print('Done')
    return



if __name__ == '__main__':
    # sys.exit(main())
    exfiles = os.path.abspath(os.path.join(os.path.dirname( __file__ ),
                                           'examplefiles'))
    #afile = 'Yueqiu et al_2012_Large piezoelectric response of Bi sub0.pdf'
    #afile = 'Yu et al_2007_The synthesis of lead-free ferroelectric Bisub0.pdf'
    #files = [os.path.join(exfiles, afile)]
    #main(files)
    main()
    # This looks really good
    # http://www.degeneratestate.org/posts/2016/Jun/15/extracting-tabular-data-from-pdfs/

    # ToDO
    # 1. get rid of header and footer - currently works ok but some edge cases
    # have issues - may need to compair pages to get best results
    # 2. seperate citations
