# Copyright 1999 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""Index.py

This module provides a way to create indexes to text files.

Classes:
Index     Dictionary-like class used to store index information.

_ShelveIndex    An Index class based on the shelve module.
_InMemoryIndex  An in-memory Index class.

"""
import os
import array
import string
import cPickle
import shelve
import UserDict

class _ShelveIndex(UserDict.UserDict):
    """An index file wrapped around shelve.

    """
    # Without a good dbm module installed, this is pretty slow and
    # generates large files.  When generating an index on a FASTA-
    # formatted file with 82000 sequences (37Mb), the 
    # index 'dat' file is 42Mb and 'dir' file is 8Mb.

    __version = 2
    __version_key = '__version'

    def __init__(self, indexname, truncate=None):
        UserDict.UserDict.__init__(self)
        try:
            if truncate:
                # In python 1.52 and before, dumbdbm (under shelve)
                # doesn't clear the old database.
                files = [indexname + '.dir',
                         indexname + '.dat',
                         indexname + '.bak'
                         ]
                for file in files:
                    if os.path.exists(file):
                        os.unlink(file)
                raise "open a new shelf"
            self.data = shelve.open(indexname, flag='r')
        except:
            # No database exists.
            self.data = shelve.open(indexname, flag='n')
            self.data[self.__version_key] = self.__version
        else:
            # Check to make sure the database is the correct version.
            version = self.data.get(self.__version_key, None)
            if version is None:
                raise IOError, "Unrecognized index format"
            elif version != self.__version:
                raise IOError, "Version %s doesn't match my version %s" % \
                      (version, self.__version)
            
    def __del__(self):
        if self.__dict__.has_key('data'):
            self.data.close()

class _InMemoryIndex(UserDict.UserDict):
    """This creates an in-memory index file.

    """
    # File Format:
    # version
    # key value
    # [...]
    
    __version = 3
    __version_key = '__version'

    def __init__(self, indexname, truncate=None):
        self._indexname = indexname
        UserDict.UserDict.__init__(self)
        
        # Remove the database if truncate is true.
        if truncate and os.path.exists(indexname):
            os.unlink(indexname)

        # Load the database if it exists
        if os.path.exists(indexname):
            handle = open(indexname)
            version = self._toobj(string.rstrip(handle.readline()))
            if version != self.__version:
                raise IOError, "Version %s doesn't match my version %s" % \
                      (version, self.__version)
            lines = handle.readlines()
            lines = map(string.split, lines)
            for key, value in lines:
                key, value = self._toobj(key), self._toobj(value)
                self[key] = value
            
    def __del__(self):
        handle = open(self._indexname, 'w')
        handle.write("%s\n" % self._tostr(self.__version))
        for key, value in self.items():
            handle.write("%s %s\n" % (self._tostr(key), self._tostr(value)))
        handle.close()

    def _tostr(self, obj):
        # I need a representation of the object that's saveable to
        # a file that uses whitespace as delimiters.  Thus, I'm
        # going to pickle the object, and then convert each character of
        # the string to its ASCII integer value.  Then, I'm going to convert
        # the integers into strings and join them together with commas. 
        # It's not the most efficient way of storing things, but it's
        # relatively fast.
        s = cPickle.dumps(obj)
        intlist = array.array('b', s)
        strlist = map(str, intlist)
        return string.join(strlist, ',')

    def _toobj(self, str):
        intlist = map(int, string.split(str, ','))
        intlist = array.array('b', intlist)
        strlist = map(chr, intlist)
        return cPickle.loads(string.join(strlist, ''))

Index = _InMemoryIndex
