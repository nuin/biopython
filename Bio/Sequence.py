# Copyright 1999 by Jeffrey Chang, Andrew Dalke.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""Sequence.py

This module provides code to work with sequences.


Classes:
AbstractSequence  Base class for all sequences.
Sequence          Basic class that stores sequences as a string.
SubSequence       Handles subsequencing with different indexing schemes.

"""

# To do:
# Add NamedSequence, add a name and id
# Add Annotation (base class, with annotation types?)

class AbstractSequence:
    def __getattr__(self, key):
        if key == "subseq":
            return SubSequence(self)
        raise AttributeError, key

    def length(self):
        raise NotImplementedError
    
    def __getslice__(self, i, j):
        raise NotImplementedError

class Sequence(AbstractSequence):
    def __init__(self, seq=''):
        self.seq = seq

    def length(self):
        return len(self.seq)
        
    def __getslice__(self, i, j):
        return self.seq[i:j]

class SubSequence:
    def __init__(self, seq):
        self.seq = seq
        
    def __call__(self, min, max):
        # with a base of 1 and including the end
        # Negative slice notation not allowed
        assert min>=1 and max >= min
        return self.seq[min-1:max]
    
    def omg(self, min, max):
        # with a base of 1 and excluding the end
        # Negative slice notation not allowed
        assert min>=1 and max>min
        return self.seq[min-1:max-1]
    
    def perl(self, min, max):
        # with a base of 0 and including the end
        # Negative slice notation not allowed
        assert min>=1 and max>=min
        return self.seq[min:max+1]
    
    def python(self, min, max):
        return self.seq[min:max]
