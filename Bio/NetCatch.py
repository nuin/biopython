# Copyright 2002 by Katharine Lindner.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""NetCatch.py

NetCatch enables the user to scan a list of labelled urls and select a subset to read
into a file.

Functions:
get_urls_by_label
get_urls_by_index
get_urls_by_range
select_output_file

"""
import sys
import os
import urllib
from tempfile import mktemp

def is_absolute_url( candidate ):
    ( url_type, url ) = urllib.splittype( candidate )
    if( url_type == None ):
        return 0
    ( url_host, url ) = urllib.splithost( url )
    if( url_host == None ):
        return 0
    return 1

class Url:

    def __init__( self, label, url ):
        assert is_absolute_url( url )
        assert type( label ) == type( '' )
        self.label = label
        self.url = url

class NetCatch:
    """
    Decorator for a dictionary of links. Each link is  indexed by its label.
    Allows the user to select links of interest and read each selection into
    its own file. The filename is contructed by appending the label with an
    extension of html.

    Files can be selected by index, range or label. The destination directory
    defaults to the current directory.  The user can specify another
    dictionary by passing a list of path segments to the constructor.

    net_catch = NetCatch()
    net_catch = NetCatch( [ 'amylase', 'species' ] )
    net_catch.get_all_urls()
    net_catch.get_urls_by_label( [ 'pig', 'dog', 'cow' ] )
    net_catch.get_urls_by_index( [ 1, 4, 6, 9 ] )
    net_catch.get_urls_by_range( 2, 5 )
    """

    def __init__( self, path_segments = [] ):
        self._urls = {}
        self._labels = []
        assert type( path_segments ) == type( [] )
        self.path_segments = path_segments
        self._build_path()

    def _build_path( self ):
        base_path = os.path.join( '' )
        for segment in self.path_segments:
            base_path = os.path.join( base_path, segment )
        self.base_path = base_path

    def __str__( self ):
        i = 0
        output = ''
        for label in self._labels:
            output = output + '%d %s: %s\n' % ( i, label, self._urls[ label ] )
            i = i + 1
        return output

    def import_dict( self, href_dict ):
        for ( key, val ) in href_dict.items():
            self.add_url( key, val )

    def add_url( self, label, url ):
        assert is_absolute_url( url )
        assert type( label ) == type( '' )
        self._labels.append( label )
        self._urls[ label ] = url

    def get_all_urls( self ):
        url_opener = urllib.URLopener()
        i = 0
        for label in self._labels:
            base_path =  self.base_path
            name = '%s%d.htm' % ( label, i )
            full_path = os.path.join( base_path, name )
            out_handle = open( full_path , "wb" )
            i = i + 1
            url = self._urls[ label ]
            url_handle = url_opener.open( url )
            contents = url_handle.read()
            out_handle.write( contents )
            url_opener.close( )
            out_handle.close()

    def get_urls_by_label( self, labels ):
        url_opener = urllib.URLopener()
        for label in labels:
            base_path =  self.base_path
            name = '%s%d.htm' % ( label, i )
            full_path = os.path.join( base_path, name )
            out_handle = open( full_path , "wb" )
            url = self._urls[ label ]
            url_handle = url_opener.open( url )
            contents = url_handle.read()
            out_handle.write( contents )
            url_opener.close( )
            out_handle.close( )

    def get_urls_by_index( self, indices ):
        url_opener = urllib.URLopener()
        for index in indices:
            base_path =  self.base_path
            name = '%s%d.htm' % ( label, i )
            full_path = os.path.join( base_path, name )
            out_handle = open( full_path , "wb" )
            label = self._labels[ index ]
            url = self._urls[ label ]
            url_handle = url_opener.open( url )
            contents = url_handle.read()
            out_handle.write( contents )
            url_opener.close( )
            out_handle.close( )

    def get_urls_by_range( self, low, hi ):
        url_opener = urllib.URLopener(  )
        for index in range( low, hi ):
            base_path =  self.base_path
            name = '%s%d.htm' % ( label, i )
            full_path = os.path.join( base_path, name )
            out_handle = open( full_path , "wb" )
            label = self._labels[ index ]
            url = self._urls[ label ]
            url_handle = url_opener.open( url )
            contents = url_handle.read()
            out_handle.write( contents )
            url_opener.close( )
            out_handle.close( )

if( __name__ == '__main__' ):
    net_catch = NetCatch( [ 'net_catch' ] )
    net_catch.add_url( "CA44_HUMAN", "http://srs6.ebi.ac.uk/srs6bin/cgi-bin/wgetz?-newId+-e+[SWall-ACC:P53420]" )
    net_catch.add_url( "CA24_ASCSU", "http://srs6.ebi.ac.uk/srs6bin/cgi-bin/wgetz?-newId+-e+[SWall-ACC:P27393]" )
    net_catch.add_url( "CA54_CANFA", "http://srs6.ebi.ac.uk/srs6bin/cgi-bin/wgetz?-newId+-e+[SWall-ACC:Q28247]" )
    net_catch.get_all_urls()
    print net_catch

