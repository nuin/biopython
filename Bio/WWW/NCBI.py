# Copyright 1999-2000 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""NCBI.py

Provides code to access NCBI over the WWW.

The main Entrez web page is available at:
http://www.ncbi.nlm.nih.gov/Entrez/

A list of the Entrez utilities is available at:
http://www.ncbi.nlm.nih.gov/entrez/utils/utils_index.html

The main Blast web page is available at:
http://www.ncbi.nlm.nih.gov/BLAST/


Functions:
query        Query Entrez.
pmfetch      Retrieve results using a unique identifier.
pmqty        Search PubMed.
pmneighbor   Return a list of related articles for a PubMed entry.
_open

"""
import string
import re
import urllib
import sgmllib
import urlparse
import time

from Bio import File

def query(cmd, db, cgi='http://www.ncbi.nlm.nih.gov/entrez/query.fcgi',
          **keywds):
    """query(cmd, db, cgi='http://www.ncbi.nlm.nih.gov/entrez/query.fcgi',
    **keywds) -> handle

    Query Entrez and return a handle to the results.  See the online
    documentation for an explanation of the parameters:
    http://www.ncbi.nlm.nih.gov/entrez/query/static/linking.html

    Raises an IOError exception if there's a network error.

    """
    variables = {'cmd' : cmd, 'db' : db}
    variables.update(keywds)
    return _open(cgi, variables)

def pmfetch(db, id, report=None, mode=None,
            cgi="http://www.ncbi.nlm.nih.gov/entrez/utils/pmfetch.fcgi"):
    """pmfetch(db, id, report=None, mode=None,
    cgi="http://www.ncbi.nlm.nih.gov/entrez/utils/pmfetch.fcgi")

    Query PmFetch and return a handle to the results.  See the
    online documentation for an explanation of the parameters:
    http://www.ncbi.nlm.nih.gov/entrez/utils/pmfetch_help.html
    
    Raises an IOError exception if there's a network error.
    
    """
    variables = {'db' : db, 'id' : id}
    if report is not None:
        variables['report'] = report
    if mode is not None:
        variables['mode'] = mode
    return _open(cgi, variables)

def pmqty(db, term, dopt=None, 
          cgi='http://www.ncbi.nlm.nih.gov/entrez/utils/pmqty.fcgi',
          **keywds):
    """pmqty(db, term, dopt=None,
    cgi='http://www.ncbi.nlm.nih.gov/entrez/utils/pmqty.fcgi') -> handle

    Query PmQty and return a handle to the results.  See the
    online documentation for an explanation of the parameters:
    http://www.ncbi.nlm.nih.gov/entrez/utils/pmqty_help.html
    
    Raises an IOError exception if there's a network error.
    
    """
    variables = {'db' : db, 'term' : term}
    if dopt is not None:
        variables['dopt'] = dopt
    variables.update(keywds)
    return _open(cgi, variables)

def pmneighbor(pmid, display,
               cgi='http://www.ncbi.nlm.nih.gov/entrez/utils/pmneighbor.fcgi'):
    """pmneighbor(pmid, display,
    cgi='http://www.ncbi.nlm.nih.gov/entrez/utils/pmneighbor.fcgi') -> handle

    Query PMNeighbor and return a handle to the results.  See the
    online documentation for an explanation of the parameters:
    http://www.ncbi.nlm.nih.gov/entrez/utils/pmneighbor_help.html
    
    Raises an IOError exception if there's a network error.
    
    """
    variables = {'pmid' : pmid, 'display' : display}
    return _open(cgi, variables)

def _open(cgi, params={}, get=1):
    """_open(cgi, params={}, get=1) -> UndoHandle

    Open a handle to Entrez.  cgi is the URL for the cgi script to access.
    params is a dictionary with the options to pass to it.  get is a boolean
    that describes whether a GET should be used.  Does some
    simple error checking, and will raise an IOError if it encounters one.

    """
    # Open a handle to Entrez.
    options = urllib.urlencode(params)
    if get:  # do a GET
        fullcgi = cgi
        if options:
            fullcgi = "%s?%s" % (cgi, options)
        handle = urllib.urlopen(fullcgi)
    else:    # do a POST
        handle = urllib.urlopen(cgi, options)

    # Wrap the handle inside an UndoHandle.
    uhandle = File.UndoHandle(handle)

    # Check for errors in the first 5 lines.
    # This is kind of ugly.
    lines = []
    for i in range(5):
        lines.append(uhandle.readline())
    for i in range(4, -1, -1):
        uhandle.saveline(lines[i])
    data = string.join(lines, '')
                   
    if string.find(data, "500 Proxy Error") >= 0:
        # Sometimes Entrez returns a Proxy Error instead of results
        raise IOError, "500 Proxy Error (Entrez busy?)"
    elif string.find(data, "WWW Error 500 Diagnostic") >= 0:
        raise IOError, "WWW Error 500 Diagnostic (Entrez busy?)"
    elif data[:5] == "ERROR":
        # XXX Possible bug here, because I don't know whether this really
        # occurs on the first line.  I need to check this!
        raise IOError, "ERROR, possibly because id not available?"
    # Should I check for 404?  timeout?  etc?
    return uhandle
    
