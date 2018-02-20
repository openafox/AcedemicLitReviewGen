# AcedemicLitReviewGen
Attempts to automate the finding of articles and data mining needed for creating a PhD thesis lit review or a Review Article.

### citedrecursion.py
Recursive search of Google scholar based on articles that cite an imput
article. Limited by requiring matching to an input regex.

### pdf2txtmod.py
Modifications of PDFMiner to make txt extraction from Acedemic publications
easier

### getdata.py
Main(files=None, wordfn=None, save=True)
Retrieves data from extracted txt files (files) given a text file (wordfn)
with '/n' delimited regex to search for in the file.
Will automatically remove headers (##) and comments (#) from the file.

## Requirements
1. https://github.com/lucabaronti/scholar.py
2. https://github.com/euske/pdfminer
3. ???
