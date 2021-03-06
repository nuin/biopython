# Copyright 2008 by Peter Cock.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""Multiple sequence alignment input/output as Alignment objects.

The Bio.AlignIO interface is deliberately very similar to Bio.SeqIO, and in
fact the two are connected internally.  Both modules use the same set of file
format names (lower case strings).  From the user's perspective, you can read
in a PHYLIP file containing one or more alignments using Bio.AlignIO, or you
can read in the sequences within these alignmenta using Bio.SeqIO.

Input
=====
For the typical special case when your file or handle contains one and only
one alignment, use the function Bio.AlignIO.read().  This takes an input file
handle, format string and optional number of sequences per alignment.  It will
return a single Alignment object (or raise an exception if there isn't just
one alignment):

    from Bio import AlignIO
    handle = open("example.aln", "rU")
    align = AlignIO.read(handle, "clustal")
    handle.close()
    print align

For the general case, when the handle could contain any number of alignments,
use the function Bio.AlignIO.parse(...) which takes the same arguments, but
returns an iterator giving Alignment objects.  For example, using the output
from the EMBOSS water or needle pairwise alignment prorams:

    from Bio import AlignIO
    handle = open("example.txt", "rU")
    for alignment in AlignIO.parse(handle, "emboss") :
        print alignment

If you want random access to the alignments by number, turn this into a list:

    from Bio import AlignIO
    handle = open("example.aln", "rU")
    alignments = list(AlignIO.parse(handle, "clustal"))
    print alignments[0]

Most alignment file formats can be concatenated so as to hold as many
different multiple sequence alignments as possible.  One common example
is the output of the tool seqboot in the PHLYIP suite.  Sometimes there
can be a file header and footer, as seen in the EMBOSS alignment output.

There is an optional argument for the number of sequences per alignment which
is usually only needed with the alignments stored in the FASTA format.
Without this information, there is no clear way to tell if you have say a
single alignment of 20 sequences, or four alignments of 5 sequences.  e.g.

    from Bio import AlignIO
    handle = open("example.faa", "rU")
    for alignment in AlignIO.parse(handle, "fasta", seq_count=5) :
        print alignment

The above code would split up the FASTA files, and try and batch every five
sequences into an alignment.

Output
======
Use the function Bio.AlignIO.write(...), which takes a complete set of
Alignment objects (either as a list, or an iterator), an output file handle
and of course the file format.

    from Bio import AlignIO
    alignments = ...
    handle = open("example.faa", "w")
    alignment = SeqIO.write(alignments, handle, "fasta")
    handle.close()

In general, you are expected to call this function once (with all your
alignments) and then close the file handle.  However, for file formats
like PHYLIP where multiple alignments are stored sequentially (with no file
header and footer), then multiple calls to the write function should work as
expected.

File Formats
============
When specifying the file format, use lowercase strings.  The same format
names are also used in Bio.SeqIO and include the following:

clustal   - Ouput from Clustal W or X, see also the module Bio.Clustalw
            which can be used to run the command line tool from Biopython.
emboss    - The "pairs" and "simple" alignment format from the EMBOSS tools.
fasta     - The generic sequence file format where each record starts with a
            identifer line starting with a ">" character, followed by lines
            of sequence.
fasta-m10 - For the pairswise alignments output by Bill Pearson's FASTA
            tools when used with the -m 10 command line option for machine
            readable output.
ig        - The IntelliGenetics file format, apparently the same as the
            MASE alignment format.
nexus     - Output from NEXUS, see also the module Bio.Nexus which can also
            read any phylogenetic trees in these files.
phylip    - Used by the PHLIP tools.
stockholm - A richly annotated alignment file format used by PFAM.

Note that while Bio.AlignIO can read all the above file formats, it cannot
write to all of them.

You can also use any file format supported by Bio.SeqIO, such as "fasta" or
"ig" (which are listed above), PROVIDED the sequences in your file are all the
same length.

Further Information
===================
See the wiki page http://biopython.org/wiki/AlignIO and also the Bio.AlignIO
chapter in the Biopython Tutorial and Cookbook which is also available online:

http://biopython.org/DIST/docs/tutorial/Tutorial.html
http://biopython.org/DIST/docs/tutorial/Tutorial.pdf
"""

#TODO
# - define policy on reading aligned sequences with gaps in
#   (e.g. - and . characters) including how the alphabet interacts
#
# - Can we build the to_alignment(...) functionality
#   into the generic Alignment class instead?
#
# - How best to handle unique/non unique record.id when writing.
#   For most file formats reading such files is fine; The stockholm
#   parser would fail.
#
# - MSF multiple alignment format, aka GCG, aka PileUp format (*.msf)
#   http://www.bioperl.org/wiki/MSF_multiple_alignment_format 

import os
#from cStringIO import StringIO
from StringIO import StringIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Align.Generic import Alignment
from Bio.Alphabet import Alphabet, AlphabetEncoder, _get_base_alphabet

import StockholmIO
import ClustalIO
import NexusIO
import PhylipIO
import EmbossIO
import FastaIO

#Convention for format names is "mainname-subtype" in lower case.
#Please use the same names as BioPerl and EMBOSS where possible.

_FormatToIterator ={#"fasta" is done via Bio.SeqIO
                    "clustal" : ClustalIO.ClustalIterator,
                    "emboss" : EmbossIO.EmbossIterator,
                    "fasta-m10" : FastaIO.FastaM10Iterator,
                    "nexus" : NexusIO.NexusIterator,
                    "phylip" : PhylipIO.PhylipIterator,
                    "stockholm" : StockholmIO.StockholmIterator,
                    }

_FormatToWriter ={#"fasta" is done via Bio.SeqIO
                  #"emboss" : EmbossIO.EmbossWriter, (unfinished)
                  "nexus" : NexusIO.NexusWriter,
                  "phylip" : PhylipIO.PhylipWriter,
                  "stockholm" : StockholmIO.StockholmWriter,
                  "clustal" : ClustalIO.ClustalWriter,
                  }

def write(alignments, handle, format) :
    """Write complete set of alignments to a file.

    sequences - A list (or iterator) of Alignment objects
    handle    - File handle object to write to
    format    - lower case string describing the file format to write.

    You should close the handle after calling this function.

    Returns the number of alignments written (as an integer).
    """
    from Bio import SeqIO

    #Try and give helpful error messages:
    if isinstance(handle, basestring) :
        raise TypeError("Need a file handle, not a string (i.e. not a filename)")
    if not isinstance(format, basestring) :
        raise TypeError("Need a string for the file format (lower case)")
    if not format :
        raise ValueError("Format required (lower case string)")
    if format != format.lower() :
        raise ValueError("Format string '%s' should be lower case" % format)
    if isinstance(alignments, Alignment) :
        raise TypeError("Need an Alignment list/iterator, not just a single Alignment")

    #Map the file format to a writer class
    if format in _FormatToIterator :
        writer_class = _FormatToWriter[format]
        count = writer_class(handle).write_file(alignments)
    elif format in SeqIO._FormatToWriter :
        #Exploit the existing SeqIO parser to the dirty work!
        #TODO - Can we make one call to SeqIO.write() and count the alignments?
        count = 0
        for alignment in alignments :
            SeqIO.write(alignment, handle, format)
            count += 1
    elif format in _FormatToIterator or format in SeqIO._FormatToIterator :
        raise ValueError("Reading format '%s' is supported, but not writing" \
                         % format)
    else :
        raise ValueError("Unknown format '%s'" % format)

    assert isinstance(count, int), "Internal error - the underlying writer " \
           + " should have returned the alignment count, not %s" % repr(count)
    return count

#This is a generator function!
def _SeqIO_to_alignment_iterator(handle, format, alphabet=None, seq_count=None) :
    """Uses Bio.SeqIO to create an Alignment iterator (PRIVATE).

    handle   - handle to the file.
    format   - string describing the file format.
    alphabet - optional Alphabet object, useful when the sequence type cannot
               be automatically inferred from the file itself (e.g. fasta)
    seq_count- Optional integer, number of sequences expected in
               each alignment.  Recommended for fasta format files.

    If count is omitted (default) then all the sequences in
    the file are combined into a single Alignment.
    """
    from Bio import SeqIO
    assert format in SeqIO._FormatToIterator

    if seq_count :
        #Use the count to split the records into batches.
        seq_record_iterator = SeqIO.parse(handle, format, alphabet)

        records = []
        for record in seq_record_iterator :
            records.append(record)
            if len(records) == seq_count :
                yield SeqIO.to_alignment(records)
                records = []
        if len(records) > 0 :
            raise ValueError("Check seq_count argument, not enough sequences?")
    else :
        #Must assume that there is a single alignment using all
        #the SeqRecord objects:
        records = list(SeqIO.parse(handle, format, alphabet))
        if records :
            yield SeqIO.to_alignment(records)
        else :
            #No alignment found!
            pass

def _force_alphabet(alignment_iterator, alphabet) :
     """Iterate over alignments, over-riding the alphabet (PRIVATE)."""
     #Assume the alphabet argument has been pre-validated
     given_base_class = _get_base_alphabet(alphabet).__class__
     for align in alignment_iterator :
         if not isinstance(_get_base_alphabet(align._alphabet),
                           given_base_class) :
             raise ValueError("Specified alphabet %s clashes with "\
                              "that determined from the file, %s" \
                              % (repr(alphabet), repr(align._alphabet)))
         for record in align :
             if not isinstance(_get_base_alphabet(record.seq.alphabet),
                               given_base_class) :
                 raise ValueError("Specified alphabet %s clashes with "\
                                  "that determined from the file, %s" \
                            % (repr(alphabet), repr(record.seq.alphabet)))
             record.seq.alphabet = alphabet
         align._alphabet = alphabet
         yield align
    
def parse(handle, format, seq_count=None, alphabet=None) :
    """Turns a sequence file into an iterator returning Alignment objects.

    handle   - handle to the file.
    format   - string describing the file format.
    alphabet - optional Alphabet object, useful when the sequence type cannot
               be automatically inferred from the file itself (e.g. phylip)
    seq_count- Optional integer, number of sequences expected in
               each alignment.  Recommended for fasta format files.

    If you have the file name in a string 'filename', use:

    >>> from Bio import AlignIO
    >>> filename = "Emboss/needle.txt"
    >>> format = "emboss"
    >>> for alignment in AlignIO.parse(open(filename,"rU"), format) :
    ...     print "Alignment of length", alignment.get_alignment_length()
    Alignment of length 124
    Alignment of length 119
    Alignment of length 120
    Alignment of length 118
    Alignment of length 125

    If you have a string 'data' containing the file contents, use:

    from Bio import AlignIO
    from StringIO import StringIO
    my_iterator = AlignIO.parse(StringIO(data), format)

    Use the Bio.AlignIO.read() function when you expect a single record only.
    """
    from Bio import SeqIO

    #Try and give helpful error messages:
    if isinstance(handle, basestring) :
        raise TypeError("Need a file handle, not a string (i.e. not a filename)")
    if not isinstance(format, basestring) :
        raise TypeError("Need a string for the file format (lower case)")
    if not format :
        raise ValueError("Format required (lower case string)")
    if format != format.lower() :
        raise ValueError("Format string '%s' should be lower case" % format)
    if alphabet is not None and not (isinstance(alphabet, Alphabet) or \
                                     isinstance(alphabet, AlphabetEncoder)) :
        raise ValueError("Invalid alphabet, %s" % repr(alphabet))

    #Map the file format to a sequence iterator:
    if format in _FormatToIterator :
        iterator_generator = _FormatToIterator[format]
        if alphabet is None : 
            return iterator_generator(handle, seq_count)
        try :
            #Initially assume the optional alphabet argument is supported
            return iterator_generator(handle, seq_count, alphabet=alphabet)
        except TypeError :
            #It isn't supported.
            return _force_alphabet(iterator_generator(handle, seq_count), alphabet)

    elif format in SeqIO._FormatToIterator :
        #Exploit the existing SeqIO parser to the dirty work!
        return _SeqIO_to_alignment_iterator(handle, format,
                                            alphabet=alphabet,
                                            seq_count=seq_count)
    else :
        raise ValueError("Unknown format '%s'" % format)

def read(handle, format, seq_count=None, alphabet=None) :
    """Turns an alignment file into a single Alignment object.

    handle   - handle to the file.
    format   - string describing the file format.
    alphabet - optional Alphabet object, useful when the sequence type cannot
               be automatically inferred from the file itself (e.g. phylip)
    seq_count- Optional interger, number of sequences expected in
               the alignment to check you got what you expected.

    If the handle contains no alignments, or more than one alignment,
    an exception is raised.  For example, using a PFAM/Stockholm file
    containing one alignment:

    >>> from Bio import AlignIO
    >>> filename = "Clustalw/protein.aln"
    >>> format = "clustal"
    >>> alignment = AlignIO.read(open(filename, "rU"), format)
    >>> print "Alignment of length", alignment.get_alignment_length()
    Alignment of length 411

    If however you want the first alignment from a file containing
    multiple alignments this function would raise an exception.
    Instead use:

    >>> from Bio import AlignIO
    >>> filename = "Emboss/needle.txt"
    >>> format = "emboss"
    >>> alignment = AlignIO.parse(open(filename, "rU"), format).next()
    >>> print "First alignment has length", alignment.get_alignment_length()
    First alignment has length 124

    Use the Bio.AlignIO.parse() function if you want to read multiple
    records from the handle.
    """
    iterator = parse(handle, format, seq_count, alphabet)
    try :
        first = iterator.next()
    except StopIteration :
        first = None
    if first is None :
        raise ValueError("No records found in handle")
    try :
        second = iterator.next()
    except StopIteration :
        second = None
    if second is not None :
        raise ValueError("More than one record found in handle")
    if seq_count :
        assert len(first.get_all_seqs())==seq_count
    return first

def _test():
    """Run the Bio.AlignIO module's doctests.

    This will try and locate the unit tests directory, and run the doctests
    from there in order that the relative paths used in the examples work.
    """
    import doctest
    import os
    if os.path.isdir(os.path.join("..","..","Tests")) :
        print "Runing doctests..."
        cur_dir = os.path.abspath(os.curdir)
        os.chdir(os.path.join("..","..","Tests"))
        doctest.testmod()
        os.chdir(cur_dir)
        del cur_dir
        print "Done"
        
if __name__ == "__main__" :
    _test()
