"""implement Martel parsers

The classes in this module are used by other Martel modules and not
typically by external users.

There are two major parsers, 'Parser' and 'RecordParser.'  The first
is the standard one, which parses the file as one string in memory
then generates the SAX events.  The other reads a record at a time
using a RecordReader and generates events after each read.  The
generated event callbacks are identical.

At some level, both parsers use "_do_callback" to convert mxTextTools
tags into SAX events.

XXX finish this documentation

XXX need a better way to get closer to the likely error position when
parsing.

XXX need to implement Locator

"""

import urllib, pprint, traceback, sys, string
from xml.sax import xmlreader, _exceptions, handler

try:
    from mx import TextTools
except ImportError:
    import TextTools

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# These exceptions are liable to change in the future
class ParserException(_exceptions.SAXException):
    """used when a parse cannot be done"""
    pass

class ParserPositionException(ParserException):
    def __init__(self, pos):
        ParserException.__init__(self,
                    "error parsing at or beyond character %d" % pos,
                                     None)
        self.pos = pos
    def __iadd__(self, offset):
        self.pos += offset
        self._msg = "error parsing at or beyond character %d" % self.pos
        return self

class ParserRecordException(ParserException):
    """used by the RecordParser when it can't read a record"""
    pass


# Uses a hack to support back references in mxTextTools!

# THIS MEANS SINGLE THREADED SUPPORT for anything using
# backreferences!  There is a much more complicated solution where the
# first element of any taglist is defined to contain the _match_group
# for that parse session.  I don't want to do that, since another
# approach is to modify mxTextTools to pass around an extra state
# object, or to write my own code.  (Did someone say NIH syndrome? :)
_match_group = {}



# The SAX startElements take an AttributeList as the second argument.
# Martel's attributes are always empty, so make a simple class which
# doesn't do anything and which I can guarantee won't be modified.
class MartelAttributeList(xmlreader.AttributesImpl):
    def getLength(self):
        return 0
    def getName(self, i):
        raise IndexError, i
    def getType(self, i):
        raise IndexError, i
    def getValue(self, i):
        raise IndexError, i
    def __len__(self):
        return 0
    def __getitem__(self, key):
        if type(key) == type(0):
            raise IndexError, key
        else:
            raise KeyError, key
    def keys(self):
        return []
    def values(self):
        return []
    def items(self):
        return []
    def has_key(self, key):
        return 0
    def get(self, key, alternative):
        return alternative

# singleton object shared amoung all startElement calls
_attribute_list = MartelAttributeList([])


def _do_callback(s, begin, end, taglist, cont_handler):
    """internal function to convert the tagtable into ContentHandler events

    's' is the input text
    'begin' is the current position in the text
    'end' is 1 past the last position of the text allowed to be parsed
    'taglist' is the tag list from mxTextTools.parse
    'cont_handler' is the SAX ContentHandler
    """
    for item in taglist:
        tag, l, r, subtags = item
        # If the tag's beginning is after the current position, then
        # the text from here to the tag's beginning are characters()
        if begin < l:
            cont_handler.characters(s[begin:l])
        else:
            # Some integrity checking
            assert begin == l, "begin = %d and l = %d" % (begin, l)

        # Named groups doesn't create ">ignore" tags, so pass them on
        # to the ContentHandler.  Unnamed groups still need a name so
        # mxTextTools can create subtags for them.  I named them
        # ">ignore" - don't create events for them.
        if tag != ">ignore":
            cont_handler.startElement(tag, _attribute_list)

        # Recurse if it has any children
        if subtags:
            _do_callback(s, l, r, subtags, cont_handler)
        else:
            cont_handler.characters(s[l:r])
        begin = r

        if tag != ">ignore":
            cont_handler.endElement(tag)

    # anything after the last tag and before the end of the current
    # range are characters
    if begin < end:
        cont_handler.characters(s[begin:end])

def _parse_elements(s, tagtable, cont_handler, debug_level):
    """parse the string with the tagtable and send the ContentHandler events

    Specifically, it sends the startElement, endElement and characters
    events but not startDocument and endDocument.
    """
    if debug_level:
        import Generate
        Generate._position = 0

    result, taglist, pos = TextTools.tag(s, tagtable, 0, len(s))

    # Special case text for the base ContentHandler since I know that
    # object does nothing and I want to test the method call overhead.
    if cont_handler.__class__ != handler.ContentHandler:
        # Send any tags to the client (there can be some even if there
        _do_callback(s, 0, pos, taglist, cont_handler)

    if not result:
        if debug_level:
            return ParserPositionException(Generate._position)
        else:
            return ParserPositionException(pos)
    elif pos != len(s):
        return pos
    else:
        return None

# This needs an interface like the standard XML parser
class Parser(xmlreader.XMLReader):
    """Parse the input data all in memory"""

    def __init__(self, tagtable, (want_groupref_names, debug_level) = (0, 1)):
        xmlreader.XMLReader.__init__(self)

        assert type(tagtable) == type( () ), "mxTextTools only allows a tuple tagtable"
        self.tagtable = tagtable

        # WARNING: This attribute is set directly by Generate - it bypasses
        # the value used in __init__.
        # Used to tell if the global "match_group" dict needs to be cleared.
        self.want_groupref_names = want_groupref_names

        self.debug_level = debug_level
        
    def __str__(self):
        x = StringIO()
        pprint.pprint(self.tagtable, x)
        return x.getvalue()

    def parseFile(self, fileobj):
        """parse using the input file object

        XXX will be removed with the switch to Python 2.0, where parse()
        takes an 'InputSource'
        """
        # Just parse as a string
        self.parseString(fileobj.read())
    
    def parse(self, systemId):
        """parse using the URL"""
        # Just parse as a file ... which parses as a string
        self.parseFile(urllib.urlopen(systemId))
        
    def parseString(self, s):
        """parse using the given string

        XXX will be removed with the switch to Python 2.0, where parse()
        takes an 'InputSource'
        """
        self._cont_handler.startDocument()

        if self.want_groupref_names:
            _match_group.clear()

        # parse the text and send the SAX events
        result = _parse_elements(s, self.tagtable, self._cont_handler,
                                 self.debug_level)

        if result is None:
            # Successful parse
            pass

        elif isinstance(result, _exceptions.SAXException):
            # could not parse record, and wasn't EOF
            self._err_handler.fatalError(result)
        
        else:
            # Reached EOF
            pos = result
            self._err_handler.fatalError(ParserPositionException(pos))
        
        # Send an endDocument event even after errors
        self._cont_handler.endDocument()

    def close(self):
        pass

class RecordParser(xmlreader.XMLReader):
    """Parse the input data a record at a time"""
    def __init__(self, format_name, record_tagtable,
                 (want_groupref_names, debug_level),
                 make_reader, reader_args = ()):
        """parse the input data a record at a time

        format_name - XML tag name for the whole data file
        record_tagtable - mxTexTools tag table for each record
        want_groupref_names - flag to say if the match_group table needs to
              be reset (will disappear with better support from mxTextTools)

        make_reader - callable object which creates a RecordReader; first
              parameter will be an input file object
        reader_args - optional arguments to pass to make_reader after the
              input file object
        """
        xmlreader.XMLReader.__init__(self)
        
        self.format_name = format_name
        assert type(record_tagtable) == type( () ), \
               "mxTextTools only allows a tuple tagtable"
        self.tagtable = record_tagtable
        self.want_groupref_names = want_groupref_names
        self.debug_level = debug_level
        self.make_reader = make_reader
        self.reader_args = reader_args
    
    def __str__(self):
        x = StringIO()
        pprint.pprint(self.tagtable, x)
        return "parse records: " + x.getvalue()
    
    def parseFile(self, fileobj):
        """parse using the input file object

        XXX will be removed with the switch to Python 2.0, where parse()
        takes an 'InputSource'
        """
        self._cont_handler.startDocument()
        
        try:
            reader = apply(self.make_reader, (fileobj,) + self.reader_args)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # something unexpected happened
            # so call it a fatal error and stop
            outfile = StringIO()
            traceback.print_exc(file=outfile)
            self._err_handler.fatalError(ParserRecordException(
                outfile.getvalue(), sys.exc_info()[1]))
            self._cont_handler.endDocument()
            return

        if self.want_groupref_names:
            _match_group.clear()
        
        self._cont_handler.startElement(self.format_name, _attribute_list)
        filepos = 0  # can get mixed up with DOS style "\r\n"
        while 1:
            try:
                record = reader.next()  
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # something unexpected happened (couldn't find a record?)
                # so call it a fatal error and stop
                outfile = StringIO()
                traceback.print_exc(file=outfile)
                self._err_handler.fatalError(ParserRecordException(
                    outfile.getvalue(), sys.exc_info()[1]))
                self._cont_handler.endDocument()
                return
            
            if record is None:
                break
            result = _parse_elements(record, self.tagtable, self._cont_handler,
                                     self.debug_level)

            if result is None:
                # Successfully read the record
                pass
            elif isinstance(result, _exceptions.SAXException):
                # Wrong format or a SAX problem, but this is recoverable
                result += filepos
                self._err_handler.error(result)
            else:
                # Did not reach end of string, but this is recoverable
                pos = filepos + result
                self._err_handler.error(ParserPositionException(pos))

            filepos = filepos + len(record)

        self._cont_handler.endElement(self.format_name)
        self._cont_handler.endDocument()

    def parse(self, systemId):
        """parse using the URL"""
        # Just parse it as a file
        self.parseFile(urllib.urlopen(systemId))
        
    def parseString(self, s):
        """parse using the given string

        XXX will be removed with the switch to Python 2.0, where parse()
        takes an 'InputSource'
        """
        # Just parse it as a file
        strfile = StringIO(s)
        self.parseFile(strfile)

    def close(self):
        pass

# This is entirely too complex, but I don't see a way to simplify it
class HeaderFooterParser(xmlreader.XMLReader):
    """Header followed by 0 or more records followed by a footer"""
    def __init__(self, format_name,
                 make_header_reader, header_reader_args, header_tagtable,
                 make_reader, reader_args, record_tagtable,
                 make_footer_reader, footer_reader_args, footer_tagtable,
                 (want_groupref_names, debug_level)):
        xmlreader.XMLReader.__init__(self)

        self.format_name = format_name

        self.make_header_reader = make_header_reader
        self.header_reader_args = header_reader_args
        self.header_tagtable = header_tagtable

        self.make_reader = make_reader
        self.reader_args = reader_args
        self.record_tagtable = record_tagtable
        
        self.make_footer_reader = make_footer_reader
        self.footer_reader_args = footer_reader_args
        self.footer_tagtable = footer_tagtable
        
        self.want_groupref_names = want_groupref_names
        self.debug_level = debug_level

    def __str__(self):
        x = StringIO()
        pprint.pprint( (self.header_tagtable, self.record_tagtable,
                        self.footer_tagtable), x)
        return "header footer records: " + x.getvalue()

    def parseString(self, s):
        strfile = StringIO(s)
        self.parseFile(strfile)

    def parse(self, systemID):
        self.parseFile(urllib.urlopen(systemID))

    def parseFile(self, fileobj):
        self._cont_handler.startDocument()
        self._cont_handler.startElement(self.format_name, _attribute_list)

        if self.want_groupref_names:
            _match_group.clear()

        # Read the header
        if self.make_header_reader is not None:
            try:
                header_reader = apply(self.make_header_reader,
                                      (fileobj,) + self.header_reader_args)
                header = header_reader.next()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # something unexpected happened
                # so call it a fatal error and stop
                outfile = StringIO()
                traceback.print_exc(file=outfile)
                self._err_handler.fatalError(ParserRecordException(
                    outfile.getvalue(), sys.exc_info()[1]))
                self._cont_handler.endDocument()
                return

            # Parse the text (if any) and send the SAX events
            if header is None:
                header = ""

            result = _parse_elements(header, self.header_tagtable,
                                     self._cont_handler, self.debug_level)

            if result is None:
                # Successful parse
                pass
            elif isinstance(result, _exceptions.SAXException):
                # could not parse header, and wasn't EOF
                self._err_handler.fatalError(result)
                self._cont_handler.endDocument()
                return
            else:
                # Reached EOF
                pos = result
                self._err_handler.fatalError(ParserPositionException(pos))
                self._cont_handler.endDocument()
                return

        # We've successfully parsed the header, now parse the records

        # Get any forward data from the header reader
        if self.make_header_reader is None:
            x, lookahead = fileobj, ""
        else:
            x, lookahead = header_reader.remainder()

        # Make the record reader
        try:
            reader = apply(self.make_reader, (fileobj,) + self.reader_args,
                           {"lookahead": lookahead})
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # something unexpected happened
            # so call it a fatal error and stop
            outfile = StringIO()
            traceback.print_exc(file=outfile)
            self._err_handler.fatalError(ParserRecordException(
                outfile.getvalue(), sys.exc_info()[1]))
            self._cont_handler.endDocument()
            return

        if header is None:
            filepos = 0
        else:
            filepos = len(header)

        record_exc_info = None
        while 1:
            try:
                record = reader.next()
##                print "RECORD"
##                print repr(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
#                print "PRoiblem here"
                # Something strange happened, so perhaps it's a footer?
                # Save the exception in case the footer doesn't parse
                outfile = StringIO()
                traceback.print_exc(file=outfile)
                record_exc_info = ParserRecordException(outfile.getvalue(),
                                                        sys.exc_info()[1])
                record = None
                break

            if record is None:
                # Reached EOF, but need to see if an empty footer is okay
                break

            result = _parse_elements(record, self.record_tagtable,
                                     self._cont_handler, self.debug_level)

            if result is None:
                # Successfully parsed the record
                pass
            else:
                # Failed to parse the record, so maybe it's a footer?
                # XXX If it isn't a footer, should try to recover by reading
                # next record -- this whole function needs a rewrite!
                if self.make_footer_reader is not None:
                    # Perhaps, so have to try
                    if isinstance(result, _exceptions.SAXException):
                        result += filepos
                        record_exc_info = result, None
                    else:
                        record_exc_info = \
                                    ParserPositionException(filepos + result), \
                                    None
                    break
                else:
                    # No footer possible
                    if isinstance(result, _exceptions.SAXException):
                        # Wrong format or a SAX problem, but recoverable
                        if isinstance(result, ParserPositionException):
                            # fix offset if possible
                            result += filepos
                        self._err_handler.error(result)
                    else:
                        # Did not reach end of string, but recoverable
                        pos = filepos + result
                        self._err_handler.error(ParserPositionException(pos))

            filepos = filepos + len(record)


        # At this point one of:
        #  - Reached EOF, so record is None and reader.lookahead == ""
        #  - The record could not be read, so record is None and
        #        reader.lookahead may contain data
        #  - The record could not be parsed, so record contains text and
        #        reader.lookahead may contain data

        x, lookahead = reader.remainder()
        if record is not None:
            # For the case when the record footer and the format have
            # the same RecordReader
            lookahead = record + lookahead

        if self.make_footer_reader is not None:
            # Make the footer reader
            try:
                reader = apply(self.make_footer_reader,
                               (fileobj,) + self.footer_reader_args,
                               {"lookahead": lookahead})
                footer = reader.next()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # something unexpected happened

                # If there was an error processing records, use that first
                if record_exc_info is not None:
                    self._err_handler.fatalError(record_exc_info)
                    self._cont_handler.endDocument()
                    return
                
                # Else call it a fatal error and stop
                outfile = StringIO()
                traceback.print_exc(file=outfile)
                self._err_handler.fatalError(ParserRecordException(
                    outfile.getvalue(), sys.exc_info()[1]))
                self._cont_handler.endDocument()
                return

            if footer is None:
                footer = ""

            result = _parse_elements(footer, self.footer_tagtable,
                                     self._cont_handler, self.debug_level)

            if result is None:
                # Successful parse
                pass
            elif record_exc_info is not None:
                self._err_handler.fatalError(record_exc_info)
                self._cont_handler.endDocument()
                return
            elif isinstance(result, _exceptions.SAXException):
                if isinstance(result, ParserPositionException):
                    result += filepos+ result.pos
                self._err_handler.fatalError(result)
                self._cont_handler.endDocument()
                return
            else:
                # Reached EOF
                pos = filepos + result
                self._err_handler.fatalError(ParserPositionException(pos))
                self._cont_handler.endDocument()
                return

            # see if there is any text left over
            x, lookahead = reader.remainder()
            
        if lookahead or fileobj.read(1):
            pos = filepos + len(footer)
            self._err_handler.fatalError(ParserPositionException(pos))
            self._cont_handler.endDocument()
            return

        # Hey, it finished.
        self._cont_handler.endElement(self.format_name)
        self._cont_handler.endDocument()


class HeaderFooterParser(xmlreader.XMLReader):
    """Header followed by 0 or more records followed by a footer"""
    def __init__(self, format_name,
                 make_header_reader, header_reader_args, header_tagtable,
                 make_reader, reader_args, record_tagtable,
                 make_footer_reader, footer_reader_args, footer_tagtable,
                 (want_groupref_names, debug_level)):
        xmlreader.XMLReader.__init__(self)

        self.format_name = format_name

        self.make_header_reader = make_header_reader
        self.header_reader_args = header_reader_args
        self.header_tagtable = header_tagtable

        self.make_reader = make_reader
        self.reader_args = reader_args
        self.record_tagtable = record_tagtable
        
        self.make_footer_reader = make_footer_reader
        self.footer_reader_args = footer_reader_args
        self.footer_tagtable = footer_tagtable
        
        self.want_groupref_names = want_groupref_names
        self.debug_level = debug_level

    def __str__(self):
        x = StringIO()
        pprint.pprint( (self.header_tagtable, self.record_tagtable,
                        self.footer_tagtable), x)
        return "header footer records: " + x.getvalue()

    def parseString(self, s):
        strfile = StringIO(s)
        self.parseFile(strfile)

    def parse(self, systemID):
        self.parseFile(urllib.urlopen(systemID))

    def parseFile(self, fileobj):
        self._cont_handler.startDocument()
        self._cont_handler.startElement(self.format_name, _attribute_list)

        if self.want_groupref_names:
            _match_group.clear()

        # Read the header
        filepos = 0
        lookahead = ""
        if self.make_header_reader is not None:
            try:
                header_reader = apply(self.make_header_reader,
                                      (fileobj,) + self.header_reader_args)
                header = header_reader.next()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # Something unexpected happend so call it a fatal error
                outfile = StringIO()
                traceback.print_exc(file=outfile)
                exc = ParserRecordException(outfile.getvalue(),
                                            sys.exc_info()[1])
                self._err_handler.fatalError(exc)
                self._cont_handler.endDocument()
                return

            # Parse the text (if any) and send the SAX events
            if header is None:
                header = ""
            filepos += len(header)

            result = _parse_elements(header, self.header_tagtable,
                                     self._cont_handler, self.debug_level)
            if result is None:
                # Successful parse
                pass
            elif isinstance(result, _exceptions.SAXException):
                # Could not parse header and wasn't EOF
                self._err_handler.fatalError(result)
                self._cont_handler.endDocument()
                return
            else:
                # Reached EOF
                pos = result
                self._err_handler.fatalError(ParserPositionException(pos))
                self._cont_handler.endDocument()
                return

        # We've successfully parsed the header, now parse the records

        # Get any forward data from the header reader
        if self.make_header_reader is None:
            x, lookahead = fileobj, ""
        else:
            x, lookahead = header_reader.remainder()

        if self.make_footer_reader is None:
            # Only records - no footer
            try:
                reader = apply(self.make_reader, (fileobj,) + self.reader_args,
                               {"lookahead": lookahead})
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # Something unexpected happened so call it a fatal
                # error and stop
                outfile = StringIO()
                traceback.print_exc(file=outfile)
                exc = ParserRecordException(outfile.getvalue(),
                                            sys.exc_info()[1])
                self._err_handler.fatalError(exc)
                self._cont_handler.endDocument()
                return

            while 1:
                try:
                    record = reader.next()
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    # Something unexpected happened and I cannot recover
                    outfile = StringIO()
                    traceback.print_exc(file=outfile)
                    exc = ParserRecordException(outfile.getvalue(),
                                                sys.exc_info()[1])
                    self._err_handler.fatalError(exc)
                    self._cont_handler.endDocument()
                    return

                if record is None:
                    # Reached EOF, so that's it (since there's no footer)
                    self._cont_handler.endElement(self.format_name)
                    self._cont_handler.endDocument()
                    return

                result = _parse_elements(record, self.record_tagtable,
                                         self._cont_handler, self.debug_level)
                if result is None:
                    # Successfully parsed the record
                    pass
                else:
                    # Failed to parse the record, but can recover
                    if isinstance(result, _exceptions.SAXException):
                        result += filepos
                    else:
                        result = ParserPositionException(filepos + result)
                    self._err_handler.error(result)

                filepos += len(record)
                    
        assert self.make_footer_reader is not None, "internal error"
            
        # This gets to be quite complicated :(

        # If the record fails, try the footer.  If that fails,
        # skip the record and try again
        record_exc = None
        try:
            reader = apply(self.make_reader, (fileobj,) + self.reader_args,
                           {"lookahead": lookahead})
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # Something unexpected happened - could be that there was
            # no record and only a footer?  Save the current exception.
            outfile = StringIO()
            traceback.print_exc(file=outfile)
            record_exc = ParserRecordException(outfile.getvalue(),
                                               sys.exc_info()[1])

        while record_exc is None:
            try:
                record = reader.next()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # Something unexpected happened.  Could be the footer,
                # but save the current exception in case it isn't
                outfile = StringIO()
                traceback.print_exc(file=outfile)
                record_exc = ParserRecordException(outfile.getvalue(),
                                                   sys.exc_info()[1])
                break

            if record is None:
                # Reached EOF, but there should have been a footer
                record_exc = ParserPositionException(filepos)
                break

            result = _parse_elements(record, self.record_tagtable,
                                     self._cont_handler, self.debug_level)
            if result is None:
                # Successfully parsed the record
                pass
            else:
                # Failed to parse the record, but may recover of it
                # isn't the footer
                if isinstance(result, _exceptions.SAXException):
                    result += filepos
                else:
                    result = ParserPositionException(filepos + result)
                record_exc = result

                # Is there a valid footer?
                try:
                    footer = ""
                    x, lookahead = reader.remainder()
                    footer_reader = apply(self.make_footer_reader,
                                          (fileobj,) + self.footer_reader_args,
                                          {"lookahead": record + lookahead})
                    footer = footer_reader.next()
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    # Not a footer either, so call this an error and
                    # attempt the next record
                    self._err_handler.error(record_exc)
                    record_exc = None

                    # But that means I need to reset the record reader(!)
                    x, lookahead = footer_reader.remainder()
                    try:
                        reader = apply(self.make_reader,
                                       (fileobj,) + self.reader_args,
                                       {"lookahead": footer + lookahead})
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except:
                        # Something unexpected happened.  Save the
                        # current exception and stop reading
                        outfile = StringIO()
                        traceback.print_exc(file=outfile)
                        record_exc = ParserRecordException(outfile.getvalue(),
                                                           sys.exc_info()[1])
                        break
                    
                    

                # Hmm, okay, it was a valid footer, but can be it be
                # parsed?
                result = _parse_elements(footer, self.footer_tagtable,
                                         self._cont_handler, self.debug_level)

                if result is None:
                    # parsed the footer, but need to check that it's
                    # at EOF
                    x, remainder = footer_reader.remainder()
                    if remainder or x.read(1):
                        # Acck, there's data left over
                        record_exc = ParserPositionException(filepos +
                                                             len(footer))
                        self._err_handler.fatalError(record_exc)
                        self._cont_handler.endDocument()
                        return
                    # Success!
                    self._cont_handler.endElement(self.format_name)
                    self._cont_handler.endDocument()
                    return
                else:
                    # Wasn't a footer, so reset the reader stream and skip
                    # past the record which I know I can read.
                    x, remainder = footer_reader.remainder()
                    reader = apply(self.make_reader,
                                   (fileobj, ) + self.reader_args,
                                   {"lookahead": footer + remainder})
                    record = reader.next()
                    self._err_handler.error(record_exc)
                    record_exc = None

            filepos += len(record)
                    
        # Could not read a record or reached EOF.  Try to parse the
        # trailer
        x, remainder = reader.remainder()
        try:
            footer_reader = apply(self.make_footer_reader,
                                  (fileobj,) + self.footer_reader_args,
                                  {"lookahead": remainder})
            footer = footer_reader.next()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # Cannot read the record, so use the older error
            self._err_handler.fatalError(record_exc)
            self._cont_handler.endDocument()
            return

        if footer is None:
            footer = ""
        result = _parse_elements(footer, self.footer_tagtable,
                                 self._cont_handler, self.debug_level)
        if result is None:
            # parsed the footer, but need to check that it's
            # at EOF
            x, remainder = footer_reader.remainder()
            if remainder or x.read(1):
                # Acck, there's data left over
                record_exc = ParserPositionException(filepos +
                                                     len(footer))
                self._err_handler.fatalError(record_exc)
                self._cont_handler.endDocument()
                return
            # Success!
            self._cont_handler.endElement(self.format_name)
            self._cont_handler.endDocument()
            return
        else:
            # Okay, use the old error
            self._err_handler.fatalError(record_exc)
            self._cont_handler.endDocument()
            return
