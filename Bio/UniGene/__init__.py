import string
import operator
import urllib
import sgmllib
import UserDict
import Bio.File
import Martel
from mx import TextTools



class UniGeneParser( sgmllib.SGMLParser ):

    def reset( self ):
        sgmllib.SGMLParser.reset( self )
        self.text = ''
        self.queue = UserDict.UserDict()
        self.open_tag_stack = []
        self.open_tag = 'open_html'
        self.key_waiting = ''
        self.master_key = ''
        self.context = 'general_info'

    def parse( self, handle ):
        self.reset()
        self.feed( handle )
        for key in self.queue.keys():
            if( self.queue[ key ] == {} ):
                if( key[ :15 ] == 'UniGene Cluster' ):
                    self.queue[ 'UniGene Cluster' ] = key[ 16: ]
                del self.queue[ key ]
        return self.queue

#
# Assumes an empty line between records
#
    def feed( self, handle ):
        if isinstance(handle, Bio.File.UndoHandle):
            uhandle = handle
        else:
            uhandle = Bio.File.UndoHandle(handle)
        text = ''
        while 1:
            line = uhandle.readline()
            line = string.strip( line )
            if( line == '' ):
                break
            text = text + ' ' + line

        sgmllib.SGMLParser.feed( self, text )



    def handle_data(self, newtext ):
        newtext = string.strip( newtext )
        self.text = self.text + newtext

    def start_a( self, attrs ):
        if( self.context == 'seq_info' ):
            if( self.open_tag != 'open_b' ):
                self.text = ''

#        self.queue.append( attrs )

    def end_a( self ):
        if( self.context == 'seq_info' ):
            if( self.open_tag != 'open_b' ):
                if( self.key_waiting == '' ):
                    self.key_waiting = self.text
                    self.text = ''

    def start_b( self, attrs ):

        self.open_tag_stack.append( self.open_tag )
        self.open_tag = 'open_b'
        if( self.key_waiting == '' ):
            self.text = ''

    def end_b( self ):
        if( self.text[ :15 ] == 'UniGene Cluster' ):
            self.queue[ 'UniGene Cluster' ] = self.text[ 16: ]
            self.text = ''
        elif( self.key_waiting == '' ):
            self.extract_key()

    def extract_key( self ):
        text = string.strip( self.text )
        key = string.join( string.split( text ) )
        words = string.split( key )
        key = string.join( words[ :2 ] )
        self.text = ''

        try:
            self.open_tag = self.open_tag_stack.pop()
        except:
            self.open_tag = 'open_html'
        if( self.open_tag == 'open_table_data' ):
            if( self.context == 'general_info' ):
                if( self.key_waiting == '' ):
                    self.key_waiting = key
                    self.text = ''
            elif( self.context == 'seq_info' ):
                if( text == 'Key to Symbols' ):
                    self.context = 'legend'
                    self.master_key = key
        elif( self.context == 'general_info' ):
            self.master_key = key
            if( string.find( key, 'SEQUENCE' ) != -1 ):
                self.context = 'seq_info'
            self.queue[ key ] = UserDict.UserDict()
        elif( self.context == 'seq_info' ):
            self.queue[ key ] = UserDict.UserDict()
            self.master_key = key



    def start_table( self, attrs ):
        self.open_tag_stack.append( self.open_tag )
        self.open_tag = 'open_table'

    def end_table( self ):
        try:
            self.open_tag = self.open_tag_stack.pop()
        except:
            self.open_tag = 'open_html'
        self.key_waiting = ''

    def start_tr( self, attrs ):
        self.open_tag_stack.append( self.open_tag )
        self.open_tag = 'open_table_row'
        self.text = ''

    def end_tr( self ):
        try:
            self.open_tag = self.open_tag_stack.pop()
        except:
            self.open_tag = 'open_html'
        text = self.text
        if text:
            self.text = ''
            if( text[ 0 ] == ':' ):
                text = text[ 1: ]
            text = string.join( string.split( text ) )
            if( ( self.context == 'general_info' ) or \
                ( self.context == 'seq_info' ) ):
                try:
                    contents = self.queue[ self.master_key ][ self.key_waiting ]
                    if( type( contents ) == type( [] ) ):
                        contents.append( text )
                    else:
                        self.queue[ self.master_key ][ self.key_waiting ] = \
                            [ contents , text ]
                except:
                    self.queue[ self.master_key ][ self.key_waiting ] = text


                self.key_waiting = ''



    def start_td( self, attrs ):
        self.open_tag_stack.append( self.open_tag )
        self.open_tag = 'open_table_data'

    def end_td( self ):
        try:
            self.open_tag = self.open_tag_stack.pop()
        except:
            self.open_tag = 'open_html'
        if( self.context == 'seq_info' ):
            self.text = self.text + ' '

    def print_item( self, item, level = 1 ):
        indent = '    '
        for j in range( 0, level ):
            indent = indent + '    '
        if( type( item ) == type( '' ) ):
            if( item != '' ):
                print '%s%s' % ( indent, item )
        elif( type( item ) == type([])):
            for subitem in item:
                self.print_item( subitem, level + 1 )
        elif( isinstance( item, UserDict.UserDict ) ):
            keys = item.keys()
            keys.sort()
            for subitem in keys:
                print '%skey is %s' % ( indent, subitem )
                self.print_item( item[ subitem ], level + 1 )
        else:
            print item

    def print_tags( self ):
        queue_keys = self.queue.keys()
        queue_keys.sort()
        for key in queue_keys:
            print 'key %s' % key
            self.print_item( self.queue[ key ] )



if( __name__ == '__main__' ):
    handle = open( 'Hs13225.htm')
    undo_handle = Bio.File.UndoHandle( handle )
    unigene_parser = UniGeneParser()
    unigene_parser.parse( handle )
    unigene_parser.print_tags()
