# Copyright 1999 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""Code to support writing parsers.



Classes:
AbstractParser         Base class for parsers.
AbstractConsumer       Base class of all Consumers.
TaggingConsumer        Consumer that tags output with its event.  For debugging
SGMLStrippingConsumer  Consumer that strips SGML tags from output.
EventGenerator         Generate Biopython Events from Martel XML output

Functions:
safe_readline          Read a line from a handle, with check for EOF.
safe_peekline          Peek at next line, with check for EOF.
read_and_call          Read a line from a handle and pass it to a method.
read_and_call_while    Read many lines, as long as a condition is met.
read_and_call_until    Read many lines, until a condition is met.
attempt_read_and_call  Like read_and_call, but forgiving of errors.
is_blank_line          Test whether a line is blank.

"""

import sys
import string
import traceback
from types import *

from Bio import File

# XML from python 2.0
try:
    from xml.sax import handler
    xml_support = 1
except ImportError:
    sys.stderr.write("Warning: Could not import SAX for dealing with XML.\n" +
                     "This causes problems with some ParserSupport modules\n")
    xml_support = 0

class AbstractParser:
    """Base class for other parsers.

    """
    def parse(self, handle):
        raise NotImplementedError, "Please implement in a derived class"

    def parse_str(self, string):
        return self.parse(File.StringHandle(string))

    def parse_file(self, filename):
        return self.parse(open(filename))

class AbstractConsumer:
    """Base class for other Consumers.

    Derive Consumers from this class and implement appropriate
    methods for each event that you want to receive.
    
    """
    def _unhandled_section(self):
        pass
    def _unhandled(self, data):
        pass
    def __getattr__(self, attr):
        if attr[:6] == 'start_' or attr[:4] == 'end_':
            method = self._unhandled_section
        else:
            method = self._unhandled
        return method

class TaggingConsumer(AbstractConsumer):
    """A Consumer that tags the data stream with the event and
    prints it to a handle.  Useful for debugging.

    """
    def __init__(self, handle=None, colwidth=15, maxwidth=80):
        """TaggingConsumer(handle=sys.stdout, colwidth=15, maxwidth=80)"""
        # I can't assign sys.stdout to handle in the argument list.
        # If I do that, handle will be assigned the value of sys.stdout
        # the first time this function is called.  This will fail if
        # the user has assigned sys.stdout to some other file, which may
        # be closed or invalid at a later time.
        if handle is None:
            handle = sys.stdout
	self._handle = handle
        self._colwidth = colwidth
        self._maxwidth = maxwidth

    def unhandled_section(self):
        self._print_name('unhandled_section')

    def unhandled(self, data):
        self._print_name('unhandled', data)

    def _print_name(self, name, data=None):
        if data is None:
	    # Write the name of a section.
            self._handle.write("%s %s\n" % ("*"*self._colwidth, name))
        else:
	    # Write the tag and line.
            self._handle.write("%-*s: %s\n" % (
                self._colwidth, name[:self._colwidth],
                string.rstrip(data[:self._maxwidth-self._colwidth-2])))

    def __getattr__(self, attr):
        if attr[:6] == 'start_' or attr[:4] == 'end_':
            method = lambda a=attr, s=self: s._print_name(a)
        else:
            method = lambda x, a=attr, s=self: s._print_name(a, x)
        return method

class SGMLStrippingConsumer:
    """A consumer that strips off SGML tags.

    This is meant to be used as a decorator for other consumers.

    """
    def __init__(self, consumer):
        if type(consumer) is not InstanceType:
            raise ValueError, "consumer should be an instance"
        self._consumer = consumer
        self._prev_attr = None
        self._stripper = File.SGMLStripper()

    def _apply_clean_data(self, data):
        clean = self._stripper.strip(data)
        self._prev_attr(clean)

    def __getattr__(self, name):
        if name in ['_prev_attr', '_stripper']:
            return getattr(self, name)
        attr = getattr(self._consumer, name)
        # If this is not a method, then return it as is.
        if type(attr) is not MethodType:
            return attr
        # If it's a section method, then return it.
        if name[:6] == 'start_' or name[:4] == 'end_':
            return attr
        # Otherwise, it's an info event, and return my method.
        self._prev_attr = attr
        return self._apply_clean_data

# onle use the Event Generator if XML handling is okay
if xml_support:
    class EventGenerator(handler.ContentHandler):
        """Handler to generate events associated with a Martel parsed file.

        This acts like a normal SAX handler, and accepts XML generated by
        Martel during parsing. These events are then converted into
        'Biopython events', which can then be caught by a standard
        biopython consumer
        """
        def __init__(self, consumer, interest_tags):
            """Initialize to begin catching and firing off events.

            Arguments:
            o consumer - The consumer that we'll send Biopython events to.
            o interest_tags - A listing of all the tags we are interested in.
            """
            self._consumer = consumer

            self.interest_tags = interest_tags

            # a dictionary of flags to recognize when we are in different
            # info items
            self.flags = {}
            for tag in self.interest_tags:
                self.flags[tag] = 0

            # a dictionary of content for each tag of interest
            self.info = {}
            for tag in self.interest_tags:
                self.info[tag] = ''

            # the previous tag we were collecting information for.
            # We set a delay in sending info to the consumer so that we can
            # collect a bunch of tags in a row and append all of the info
            # together.
            self._previous_tag = ''

        def _get_set_flags(self):
            """Return a listing of all of the flags which are set as positive.
            """
            set_flags = []
            for tag in self.flags.keys():
                if self.flags[tag] == 1:
                    set_flags.append(tag)

            return set_flags

        def startElement(self, name, attrs):
            """Recognize when we are recieving different items from Martel.

            We want to recognize when Martel is passing us different items
            of interest, so that we can collect the information we want from
            the characters passed.
            """
            # set the appropriate flag if we are keeping track of these flags
            if name in self.flags.keys():
                # make sure that all of the flags are being properly unset
                assert self.flags[name] == 0, "Flag % not unset" % name

                self.flags[name] = 1

        def characters(self, content):
            """Extract the information.

            Using the flags that are set, put the character information in
            the appropriate place.
            """
            set_flags = self._get_set_flags()

            # deal with each flag in the set flags
            for flag in set_flags:
                self.info[flag] += content

        def endElement(self, name):
            """Send the information to the consumer.

            Once we've got the end element we've collected up all of the
            character information we need, and we need to send this on to
            the consumer to do something with it.

            We have a delay of one tag on doing this, so that we can collect
            all of the info from multiple calls to the same element at once.
            """
            # only deal with the tag if it is something we are
            # interested in and potentially have information for
            if name in self._get_set_flags():
                # if we are at a new tag, pass on the info from the last tag
                if self._previous_tag and self._previous_tag != name:
                    self._make_callback(self._previous_tag)

                # set this tag as the next to be passed
                self._previous_tag = name

                # unset the flag for this tag so we stop collecting info
                # with it
                self.flags[name] = 0

                # add a space to the end of the info. Then we'll have this
                # if we roll over lines, and it'll get stripped out otherwise
                self.info[name] += ' '

        def _make_callback(self, name):
            """Call the callback function with the info with the given name.
            """
            # strip off whitespace and call the consumer
            callback_function = eval('self._consumer.' + name)
            info_to_pass = string.strip(self.info[name])
            callback_function(info_to_pass)

            # reset the information for the tag
            self.info[name] = ''

        def endDocument(self):
            """Make sure all of our information has been passed.

            This just flushes out any stored tags that need to be passed.
            """
            if self._previous_tag:
                self._make_callback(self._previous_tag)

def read_and_call(uhandle, method, **keywds):
    """read_and_call(uhandle, method[, start][, end][, contains][, blank][, has_re])

    Read a line from uhandle, check it, and pass it to the method.
    Raises a SyntaxError if the line does not pass the checks.

    start, end, contains, blank, and has_re specify optional conditions
    that the line must pass.  start and end specifies what the line must
    begin or end with (not counting EOL characters).  contains
    specifies a substring that must be found in the line.  If blank
    is a true value, then the line must be blank.  has_re should be
    a regular expression object with a pattern that the line must match
    somewhere.

    """
    line = safe_readline(uhandle)
    errmsg = apply(_fails_conditions, (line,), keywds)
    if errmsg is not None:
        raise SyntaxError, errmsg
    method(line)

def read_and_call_while(uhandle, method, **keywds):
    """read_and_call_while(uhandle, method[, start][, end][, contains][, blank][, has_re]) -> number of lines

    Read a line from uhandle and pass it to the method as long as
    some condition is true.  Returns the number of lines that were read.

    See the docstring for read_and_call for a description of the parameters.
    
    """
    nlines = 0
    while 1:
        line = safe_readline(uhandle)
        # If I've failed the condition, then stop reading the line.
        if apply(_fails_conditions, (line,), keywds):
            uhandle.saveline(line)
            break
        method(line)
        nlines = nlines + 1
    return nlines

def read_and_call_until(uhandle, method, **keywds):
    """read_and_call_until(uhandle, method, 
    start=None, end=None, contains=None, blank=None) -> number of lines

    Read a line from uhandle and pass it to the method until
    some condition is true.  Returns the number of lines that were read.

    See the docstring for read_and_call for a description of the parameters.
    
    """
    nlines = 0
    while 1:
        line = safe_readline(uhandle)
        # If I've met the condition, then stop reading the line.
        if not apply(_fails_conditions, (line,), keywds):
            uhandle.saveline(line)
            break
        method(line)
        nlines = nlines + 1
    return nlines

def attempt_read_and_call(uhandle, method, **keywds):
    """attempt_read_and_call(uhandle, method, **keywds) -> boolean

    Similar to read_and_call, but returns a boolean specifying
    whether the line has passed the checks.  Does not raise
    exceptions.

    See docs for read_and_call for a description of the function
    arguments.

    """
    line = safe_readline(uhandle)
    passed = not apply(_fails_conditions, (line,), keywds)
    if passed:
        method(line)
    else:
        uhandle.saveline(line)
    return passed

def _fails_conditions(line, start=None, end=None, contains=None, blank=None,
                      has_re=None):
    if start is not None:
        if line[:len(start)] != start:
            return "Line does not start with '%s':\n%s" % (start, line)
    if end is not None:
        if string.rstrip(line)[-len(end):] != end:
            return "Line does not end with '%s':\n%s" % (end, line)
    if contains is not None:
        if string.find(line, contains) == -1:
            return "Line does not contain '%s':\n%s" % (contains, line)
    if blank is not None:
        if blank:
            if not is_blank_line(line):
                return "Expected blank line, but got:\n%s" % line
        else:
            if is_blank_line(line):
                return "Expected non-blank line, but got a blank one"
    if has_re is not None:
        if has_re.search(line) is None:
            return "Line does not match regex '%s':\n%s" % (
                has_re.pattern, line)
    return None

def is_blank_line(line, allow_spaces=0):
    """is_blank_line(line, allow_spaces=0) -> boolean

    Return whether a line is blank.  allow_spaces specifies whether to
    allow whitespaces in a blank line.  A true value signifies that a
    line containing whitespaces as well as end-of-line characters
    should be considered blank.

    """
    if not line:
        return 1
    if allow_spaces:
        return string.rstrip(line) == ''
    return line[0] == '\n' or line[0] == '\r'

def safe_readline(handle):
    """safe_readline(handle) -> line

    Read a line from an UndoHandle and return it.  If there are no more
    lines to read, I will raise a SyntaxError.

    """
    line = handle.readline()
    if not line:
        raise SyntaxError, "Unexpected end of stream."
    return line

def safe_peekline(handle):
    """safe_peekline(handle) -> line

    Peek at the next line in an UndoHandle and return it.  If there are no
    more lines to peek, I will raise a SyntaxError.
    
    """
    line = handle.peekline()
    if not line:
        raise SyntaxError, "Unexpected end of stream."
    return line
