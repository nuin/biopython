# Copyright 2001 by Katharine Lindner.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""Martel based parser to read NBRF formatted files.

This is a huge regular regular expression for CDD, built using
the 'regular expressiona on steroids' capabilities of Martel.


http://www.ncbi.nlm.nih.gov/Structure/cdd/cdd.shtml


Notes:
Just so I remember -- the new end of line syntax is:
  New regexp syntax - \R
     \R    means "\n|\r\n?"
     [\R]  means "[\n\r]"

This helps us have endlines be consistent across platforms.

"""
# standard library
import string


from Bio.Seq import Seq
from UserDict import UserDict



"""Hold CDD data in a straightforward format.

classes:
o Record - All of the information in a CDD record.
"""

class Record( UserDict ):
    """Hold CDD information in a format similar to the original record.

    The Record class is meant to make data easy to get to when you are
    just interested in looking at CDD data.

    Attributes:
    cd
    description
    status
    source
    date
    reference
    taxonomy
    aligned
    representative
    range
    sequence
    """
    def __init__(self):
        UserDict.__init__( self )
        self.data[ 'references' ] = []
        self.data[ 'alignment_lookup' ] = {}


    def __str__( self ):
        output = ''
        keys = self.data.keys()
        keys.sort()
        for key in keys:
            output = output + '%s:\n\n' % key.upper()
            contents = self.data[ key ]
            if( type( contents ) == type( '' ) ):
                if( key == 'Sequence' ):
                    output = output + out_multiline( contents )
                else:
                    output = output + '%s\n' % contents
            elif( type( contents ) == type( {} ) ):
                output = output + output_dict( contents, 1 )
            elif( type( contents ) == type( [] ) ):
                output = output + output_list( contents, 1 )
            elif( isinstance( contents, Seq ) ):
                output = output + out_multiline( contents.data )
        output = output + '\n\n'
        return output

def output_dict( dict, level = 0 ):
    output = ''
    prefix = ''
    for j in range( 0, level ):
        prefix = prefix + '    '
    keys = dict.keys()
    keys.sort()
    for key in keys:
        contents = dict[ key ]
        if( type( contents ) == type( '' ) ):
            output = output + '%s%s = %s\n' % ( prefix, key, contents )
        elif( type( contents ) == type( {} ) ):
            output = output + output_dict( contents, level + 1 )
        elif( type( contents ) == type( [] ) ):
            output = output + output_list( contents, level + 1 )
    output = output + '\n'
    return output

def output_list( items, level = 0 ):
    output = ''
    prefix = ''
    for j in range( 0, level ):
        prefix = prefix + '    '
    for item in items:
        if( type( item ) == type( '' ) ):
            output = output + '%s%s\n' % ( prefix, item )
        elif( type( item ) == type( {} ) ):
            output = output + output_dict( item, level + 1 )
        elif( type( item ) == type( [] ) ):
            output = output + output_list( item, level + 1 )
    output = output + '\n'
    return output

def out_multiline( multiline ):
    output = ''
    for j in range( 0, len( multiline ), 80 ):
        output = output + '%s\n'  % multiline[ j: j + 80 ]
    output = output + '\n'
    return output










