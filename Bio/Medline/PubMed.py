# Copyright 1999-2000 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""PubMed.py

This module provides code to work with PubMed from the NCBI.
http://www.ncbi.nlm.nih.gov/PubMed/

Online documentation for linking to PubMed is available at:
http://www.ncbi.nlm.nih.gov/PubMed/linking.html


Classes:
Dictionary     Access PubMed articles using a dictionary interface.

Functions:
search_for     Search PubMed.
find_related   Find related articles in PubMed.
download_many  Download many articles from PubMed in batch mode.

"""

import string
import re
import sgmllib

from Bio import File
from Bio.WWW import NCBI
from Bio.Medline import Medline
from Bio.WWW import RequestLimiter

class Dictionary:
    """Access PubMed using a read-only dictionary interface.

    Methods:
    
    """
    def __init__(self, delay=5.0, parser=None):
        """Dictionary(delay=5.0, parser=None)

        Create a new Dictionary to access PubMed.  parser is an optional
        parser (e.g. Medline.RecordParser) object to change the results
        into another form.  If set to None, then the raw contents of the
        file will be returned.  delay is the number of seconds to wait
        between each query.

        """
        self.parser = parser
        self.limiter = RequestLimiter(delay)

    def __len__(self):
        raise NotImplementedError, "PubMed contains lots of entries"
    def clear(self):
        raise NotImplementedError, "This is a read-only dictionary"
    def __setitem__(self, key, item):
        raise NotImplementedError, "This is a read-only dictionary"
    def update(self):
        raise NotImplementedError, "This is a read-only dictionary"
    def copy(self):
        raise NotImplementedError, "You don't need to do this..."
    def keys(self):
        raise NotImplementedError, "You don't really want to do this..."
    def items(self):
        raise NotImplementedError, "You don't really want to do this..."
    def values(self):
        raise NotImplementedError, "You don't really want to do this..."
    
    def has_key(self, id):
        """S.has_key(id) -> bool"""
        try:
            self[id]
        except KeyError:
            return 0
        return 1

    def get(self, id, failobj=None):
        try:
            return self[id]
        except KeyError:
            return failobj
        raise "How did I get here?"

    def __getitem__(self, id):
        """S.__getitem__(id) -> object

        Return the Medline entry.  id is either the Medline Unique ID
        or the Pubmed ID of the article.  Raises a KeyError if there's an
        error.
        
        """
        # First, check to see if enough time has passed since my
        # last query.
        self.limiter.wait()
        
        try:
            handle = NCBI.pmfetch(
                db='PubMed', id=id, report='medlars', mode='text')
        except IOError, x:
            # raise a KeyError instead of an IOError
            # XXX I really should distinguish between a real IOError and
            # if the id is not in the database.
            raise KeyError, x
        if self.parser is not None:
            return self.parser.parse(handle)
        return handle.read()

def search_for(search, batchsize=10000, delay=2, callback_fn=None,
               start_id=0, max_ids=None):
    """search_for(search[, batchsize][, delay][, callback_fn]
    [, start_id][, max_ids]) -> ids

    Search PubMed and return a list of the PMID's that match the
    criteria.  search is the search string used to search the
    database.  batchsize specifies the number of ids to return at one
    time.  By default, it is set to 10000, the maximum.  delay is the
    number of seconds to wait between queries (default 2).
    callback_fn is an optional callback function that will be called
    as passed a PMID as results are retrieved.  start_id specifies the
    index of the first id to retrieve and max_ids specifies the
    maximum number of id's to retrieve.

    """
    class ResultParser(sgmllib.SGMLParser):
        # Parse the ID's out of the HTML-formatted page that PubMed
        # returns.  The format of the page is:
        # <Title>QueryResult</Title>
        # <Body>
        # 10807727<Br>
        # [...]
        # </Body>
        def __init__(self):
            sgmllib.SGMLParser.__init__(self)
            self.ids = []
            self.in_body = 0
        def start_body(self, attributes):
            self.in_body = 1
        def end_body(self):
            self.in_body = 0
        _not_pmid_re = re.compile(r'\D')
        def handle_data(self, data):
            # The ID's only appear in the body.  If I'm not in the body,
            # then don't do anything.
            if not self.in_body:
                return
            # If data is just whitespace, then ignore it.
            data = string.strip(data)
            if not data:
                return
            # Everything here should be a PMID.  Check and make sure
            # data really is one.  A PMID should be a string consisting
            # of only integers.  Should I check to make sure it
            # meets a certain minimum length?
            if self._not_pmid_re.search(data):
                raise SyntaxError, \
                      "I expected an ID, but '%s' doesn't look like one." % \
                      repr(data)
            self.ids.append(data)

    limiter = RequestLimiter(delay)
    ids = []
    while max_ids is None or len(ids) < max_ids:
        parser = ResultParser()
        
        # Check to make sure enough time has passed before my
        # last search.  If not, then wait.
        limiter.wait()

        start = start_id + len(ids)
        max = batchsize
        if max_ids is not None and max > max_ids - len(ids):
            max = max_ids - len(ids)

        # Do a query against PmQty.  Search medline, using the
        # search string, and get only the ID's in the results.
        h = NCBI.pmqty('m', search, dopt='d', dispmax=max, dispstart=start)
        parser.feed(h.read())
        ids.extend(parser.ids)
        if callback_fn is not None:
            # Call the callback function with each of the new ID's.
            for id in parser.ids:
                callback_fn(id)
        if len(parser.ids) < max or not parser.ids:  # no more id's to read
            break
    return ids

def find_related(pmid):
    """find_related(pmid) -> ids

    Search PubMed for a list of citations related to pmid.  pmid can
    be a PubMed ID, a MEDLINE UID, or a list of those.

    """
    class ResultParser(sgmllib.SGMLParser):
        # Parse the ID's out of the HTML-formatted page that PubMed
        # returns.  The format of the page is:
        # <pmneighborResult> 
        #      <id>######</id>
        #      [...]
        # </pmneighborResult>

        def __init__(self):
            sgmllib.SGMLParser.__init__(self)
            self.ids = []
            self.in_id = 0
        def start_id(self, attributes):
            self.in_id = 1
        def end_id(self):
            self.in_id = 0
        _not_pmid_re = re.compile(r'\D')
        def handle_data(self, data):
            if not self.in_id:
                return
            # Everything here should be a PMID.  Check and make sure
            # data really is one.  A PMID should be a string consisting
            # of only integers.  Should I check to make sure it
            # meets a certain minimum length?
            if self._not_pmid_re.search(data):
                raise SyntaxError, \
                      "I expected an ID, but '%s' doesn't look like one." % \
                      repr(data)
            self.ids.append(data)

    parser = ResultParser()
    if type(pmid) is type([]):
        pmid = string.join(pmid, ',')
    h = NCBI.pmneighbor(pmid, 'pmid')
    parser.feed(h.read())
    return parser.ids

def download_many(ids, callback_fn, broken_fn=None, delay=120.0, batchsize=500,
                  parser=None):
    """download_many(ids, callback_fn, broken_fn=None, delay=120.0, batchsize=500)

    Download many records from PubMed.  ids is a list of either the
    Medline Unique ID or the PubMed ID's of the articles.  Each time a
    record is downloaded, callback_fn is called with the text of the
    record.  broken_fn is an optional function that is called with the
    id of records that were not able to be downloaded.  delay is the
    number of seconds to wait between requests.  batchsize is the
    number of records to request each time.

    """
    # parser is an undocumented parameter that allows people to
    # specify an optional parser to handle each record.  This is
    # dangerous because the results may be malformed, and exceptions
    # in the parser may disrupt the whole download process.
    if batchsize > 500 or batchsize < 1:
        raise ValueError, "batchsize must be between 1 and 500"
    limiter = RequestLimiter(delay)
    current_batchsize = batchsize
    
    # Loop until all the ids are processed.  We want to process as
    # many as possible with each request.  Unfortunately, errors can
    # occur.  Some id may be incorrect, or the server may be
    # unresponsive.  In addition, one broken id out of a list of id's
    # can cause a non-specific error.  Thus, the strategy I'm going to
    # take, is to start by downloading as many as I can.  If the
    # request fails, I'm going to half the number of records I try to
    # get.  If there's only one more record, then I'll report it as
    # broken and move on.  If the request succeeds, I'll double the
    # number of records until I get back up to the batchsize.
    while ids:
        id_str = ','.join(ids[:current_batchsize])

        # Make sure enough time has passed before I do another query.
        limiter.wait()
        try:
            # Query PubMed.  If one or more of the id's are broken,
            # this will raise an IOError.
            handle = NCBI.pmfetch(
                db='PubMed', id=id_str, report='medlars', mode='text')
        except IOError:   # Query did not work.
            if current_batchsize == 1:
                # There was only 1 id in the query.  Report it as
                # broken and move on.
                id = ids.pop(0)
                if broken_fn is not None:
                    broken_fn(id)
            else:
                # I don't know which one is broken.  Try again with
                # fewer id's.
                current_batchsize = current_batchsize / 2
            continue

        results = handle.read()
        
        # I'm going to check to make sure PubMed returned the same
        # number of id's as I requested.  If it didn't then I'm going
        # to raise an exception.  This could take a lot of memory if
        # the batchsize is large.
        iter = Medline.Iterator(File.StringHandle(results))
        num_ids = 0
        while 1:
            if iter.next() is None:
                break
            num_ids = num_ids + 1
        if num_ids != current_batchsize and num_ids != len(ids):
            raise SyntaxError, "I requested %d id's from PubMed but found %d" \
                  % (current_batchsize, num_ids)

        # Iterate through the results and pass the records to the
        # callback.
        iter = Medline.Iterator(File.StringHandle(results), parser)
        while 1:
            rec = iter.next()
            if rec is None:
                break
            callback_fn(ids[idnum], rec)

        ids = ids[current_batchsize:]

        # If I'm not downloading the maximum number of articles,
        # double the number for next time.
        if current_batchsize < batchsize:
            current_batchsize = current_batchsize * 2
            if current_batchsize > batchsize:
                current_batchsize = batchsize
