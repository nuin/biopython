# Copyright 2007 by Peter Cock.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.
#
# This code is NOT intended for direct use.  It provides a basic scanner
# (for use with a event consumer such as Bio.GenBank._FeatureConsumer)
# to parse a GenBank or EMBL file (with their shared INSDC feature table).
#
# It is used by Bio.GenBank to parse GenBank files
# It is also used by Bio.SeqIO to parse GenBank and EMBL files

import sys
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import generic_alphabet, generic_protein

class InsdcScanner :
    """Basic functions for breaking up a GenBank/EMBL file into sub sections.

    The International Nucleotide Sequence Database Collaboration (INSDC)
    between the DDBJ, EMBL, and GenBank.  These organisations all use the
    same "Feature Table" layout in their plain text flat file formats.

    However, the header and sequence sections of an EMBL file are very
    different in layout to those produced by GenBank/DDBJ."""

    #These constants get redefined with sensible values in the sub classes:
    RECORD_START = "XXX"  # "LOCUS       " or "ID   "
    HEADER_WIDTH = 3   # 12 or 5
    FEATURE_START_MARKERS = ["XXX***FEATURES***XXX"]
    FEATURE_END_MARKERS = ["XXX***END FEATURES***XXX"]
    FEATURE_QUALIFIER_INDENT = 0
    FEATURE_QUALIFIER_SPACER = ""
    SEQUENCE_HEADERS=["XXX"] #with right hand side spaces removed

    def __init__(self, debug=0) :
        assert len(self.RECORD_START)==self.HEADER_WIDTH
        for marker in self.SEQUENCE_HEADERS :
            assert marker==marker.rstrip()
        assert len(self.FEATURE_QUALIFIER_SPACER)==self.FEATURE_QUALIFIER_INDENT
        self.debug = debug
        self.line = None

    def set_handle(self, handle) :
        self.handle = handle
        self.line = ""

    def find_start(self) :
        """Read in lines until find the ID/LOCUS line, which is returned"""
        while True :
            if self.line :
                line = self.line
                self.line = ""
            else :
                line = self.handle.readline()
            if not line :
                if self.debug : print "End of file"
                return None
            if line[:self.HEADER_WIDTH]==self.RECORD_START :
                if self.debug > 1: print "Found the start of a record:\n" + line
                break
            line = line.rstrip()
            if line == "//" :
                if self.debug > 1: print "Skipping // marking end of last record"
            elif line == "" :
                if self.debug > 1: print "Skipping blank line before record"
            else :
                raise SyntaxError("Expected line starting '%s', found '%s'" \
                                  % (self.RECORD_START, line.rstrip()))
        self.line = line
        return line

    def parse_header(self) :
        """Return list of strings making up the header

        New line characters are removed.

        Assumes you have just read in the ID/LOCUS line.
        """
        assert self.line[:self.HEADER_WIDTH]==self.RECORD_START, \
               "Not at start of record"
        
        header_lines = []
        while True :
            line = self.handle.readline()
            if not line :
                raise SyntaxError("Premature end of line during sequence data")
            line = line.rstrip()
            if line in self.FEATURE_START_MARKERS :
                if self.debug : print "Found header table"
                break
            #if line[:self.HEADER_WIDTH]==self.FEATURE_START_MARKER[:self.HEADER_WIDTH] :
            #    if self.debug : print "Found header table (?)"
            #    break
            if line[:self.HEADER_WIDTH].rstrip() in self.SEQUENCE_HEADERS :
                if self.debug : print "Found start of sequence"
                break
            if line == "//" :
                raise SyntaxError("Premature end of sequence data marker '//' found")
            header_lines.append(line)
        self.line = line
        return header_lines

    def parse_features(self, skip=False) :
        """Return list of tuples for the features (if present)

        Each feature is returned as a tuple (key, location, qualifiers)
        where key and location are strings (e.g. "CDS" and
        "complement(join(490883..490885,1..879))") while qualifiers
        is a list of two string tuples (feature qualifier keys and values).

        Assumes you have already read to the start of the features table.
        """
        if self.line.rstrip() not in self.FEATURE_START_MARKERS :
            if self.debug : print "Didn't find any feature table"
            return []
        
        while self.line.rstrip() in self.FEATURE_START_MARKERS :
            self.line = self.handle.readline()

        features = []
        line = self.line
        while True :
            if not line :
                raise SyntaxError("Premature end of line during features table")
            if line[:self.HEADER_WIDTH].rstrip() in self.SEQUENCE_HEADERS :
                if self.debug : print "Found start of sequence"
                break
            line = line.rstrip()
            if line == "//" :
                raise SyntaxError("Premature end of features table, marker '//' found")
            if line in self.FEATURE_END_MARKERS :
                if self.debug : print "Found end of features"
                line = self.handle.readline()
                break
            if line[2:self.FEATURE_QUALIFIER_INDENT].strip() == "" :
                raise SyntaxError("Expected a feature qualifier in line '%s'" % line)

            if skip :
                line = self.handle.readline()
                while line[:self.FEATURE_QUALIFIER_INDENT] == self.FEATURE_QUALIFIER_SPACER :
                    line = self.handle.readline()
            else :
                #Build up a list of the lines making up this feature:
                feature_key = line[2:self.FEATURE_QUALIFIER_INDENT].strip()
                feature_lines = [line[self.FEATURE_QUALIFIER_INDENT:]]
                line = self.handle.readline()
                while line[:self.FEATURE_QUALIFIER_INDENT] == self.FEATURE_QUALIFIER_SPACER \
                or line.rstrip() == "" : # cope with blank lines in the midst of a feature
                    feature_lines.append(line[self.FEATURE_QUALIFIER_INDENT:].rstrip())
                    line = self.handle.readline()
                features.append(self.parse_feature(feature_key, feature_lines))
        self.line = line
        return features

    def parse_feature(self, feature_key, lines) :
        """Expects a feature as a list of strings, returns a tuple (key, location, qualifiers)

        For example given this GenBank feature:

             CDS             complement(join(490883..490885,1..879))
                             /locus_tag="NEQ001"
                             /note="conserved hypothetical [Methanococcus jannaschii];
                             COG1583:Uncharacterized ACR; IPR001472:Bipartite nuclear
                             localization signal; IPR002743: Protein of unknown
                             function DUF57"
                             /codon_start=1
                             /transl_table=11
                             /product="hypothetical protein"
                             /protein_id="NP_963295.1"
                             /db_xref="GI:41614797"
                             /db_xref="GeneID:2732620"
                             /translation="MRLLLELKALNSIDKKQLSNYLIQGFIYNILKNTEYSWLHNWKK
                             EKYFNFTLIPKKDIIENKRYYLIISSPDKRFIEVLHNKIKDLDIITIGLAQFQLRKTK
                             KFDPKLRFPWVTITPIVLREGKIVILKGDKYYKVFVKRLEELKKYNLIKKKEPILEEP
                             IEISLNQIKDGWKIIDVKDRYYDFRNKSFSAFSNWLRDLKEQSLRKYNNFCGKNFYFE
                             EAIFEGFTFYKTVSIRIRINRGEAVYIGTLWKELNVYRKLDKEEREFYKFLYDCGLGS
                             LNSMGFGFVNTKKNSAR"

        Then should give input key="CDS" and the rest of the data as a list of strings
        lines=["complement(join(490883..490885,1..879))", ..., "LNSMGFGFVNTKKNSAR"]
        where the leading spaces and trailing newlines have been removed.

        Returns tuple containing: (key as string, location string, qualifiers as list)
        as follows for this example:

        key = "CDS", string
        location = "complement(join(490883..490885,1..879))", string
        qualifiers = list of string tuples:

        [('locus_tag', '"NEQ001"'),
         ('note', '"conserved hypothetical [Methanococcus jannaschii];\nCOG1583:..."'),
         ('codon_start', '1'),
         ('transl_table', '11'),
         ('product', '"hypothetical protein"'),
         ('protein_id', '"NP_963295.1"'),
         ('db_xref', '"GI:41614797"'),
         ('db_xref', '"GeneID:2732620"'),
         ('translation', '"MRLLLELKALNSIDKKQLSNYLIQGFIYNILKNTEYSWLHNWKK\nEKYFNFT..."')]

        In the above example, the "note" and "translation" were edited for compactness,
        and they would contain multiple new line characters (displayed above as \n)

        If a qualifier is quoted (in this case, everything except codon_start and
        transl_table) then the quotes are NOT removed.

        Note that no whitespace is removed.
        """
        #Skip any blank lines
        iterator = iter(filter(None, lines))
        try :
            line = iterator.next()

            feature_location = line.strip()
            while feature_location[-1:]=="," :
                #Multiline location, still more to come!
                feature_location += iterator.next().strip()

            qualifiers=[]

            for line in iterator :
                if line[0]=="/" :
                    #New qualifier
                    i = line.find("=")
                    key = line[1:i] #does not work if i==-1
                    value = line[i+1:] #we ignore 'value' if i==-1
                    if i==-1 :
                        #Qualifier with no key, e.g. /pseudo
                        key = line[1:]
                        qualifiers.append((key,None))
                    elif value[0]=='"' :
                        #Quoted...
                        if value[-1]<>'"' or value<>'"' :
                            #No closing quote on the first line...
                            while value[-1] <> '"' :
                                value += "\n" + iterator.next()
                        else :
                            #One single line (quoted)
                            assert value == '"'
                            if self.debug : print "Quoted line %s:%s" % (key, value)
                        #DO NOT remove the quotes...
                        qualifiers.append((key,value))
                    else :
                        #Unquoted
                        #if debug : print "Unquoted line %s:%s" % (key,value)
                        qualifiers.append((key,value))
                else :
                    #Unquoted continuation
                    assert len(qualifiers) > 0
                    assert key==qualifiers[-1][0]
                    #if debug : print "Unquoted Cont %s:%s" % (key, line)
                    qualifiers[-1] = (key, qualifiers[-1][1] + "\n" + line)
            return (feature_key, feature_location, qualifiers)
        except StopIteration:
            #Bummer
            raise SyntaxError("Problem with '%s' feature:\n%s" \
                              % (feature_key, "\n".join(lines)))

    def parse_footer(self) :
        """returns a tuple containing a list of any misc strings, and the sequence"""
        #This is a basic bit of code to scan and discard the sequence,
        #which was useful when developing the sub classes.
        if self.line in self.FEATURE_END_MARKERS :
            while self.line[:self.HEADER_WIDTH].rstrip() not in self.SEQUENCE_HEADERS :
                self.line = self.handle.readline()
                if not self.line :
                    raise SyntaxError("Premature end of file")
                self.line = self.line.rstrip()
            
        assert self.line[:self.HEADER_WIDTH].rstrip() in self.SEQUENCE_HEADERS, \
               "Not at start of sequence"
        while True :
            line = self.handle.readline()
            if not line : raise SyntaxError("Premature end of line during sequence data")
            line = line.rstrip()
            if line == "//" : break
        self.line = line
        return ([],"") #Dummy values!

    def _feed_first_line(self, consumer, line) :
        """Handle the LOCUS/ID line, passing data to the comsumer
        
        This should be implemented by the EMBL / GenBank specific subclass
        
        Used by the parse_records() and parse() methods.
        """
        pass

    def _feed_header_lines(self, consumer, lines) :
        """Handle the header lines (list of strings), passing data to the comsumer
        
        This should be implemented by the EMBL / GenBank specific subclass
        
        Used by the parse_records() and parse() methods.
        """
        pass


    def _feed_feature_table(self, consumer, feature_tuples) :
        """Handle the feature table (list of tuples), passing data to the comsumer
        
        Used by the parse_records() and parse() methods.
        """
        consumer.start_feature_table()
        for feature_key, location_string, qualifiers in feature_tuples :
            consumer.feature_key(feature_key)
            consumer.location(location_string)
            for q_key, q_value in qualifiers :
                consumer.feature_qualifier_name([q_key])
                if q_value is not None :
                    consumer.feature_qualifier_description(q_value.replace("\n"," "))
                    
    def _feed_misc_lines(self, consumer, lines) :
        """Handle any lines between features and sequence (list of strings), passing data to the consumer
        
        This should be implemented by the EMBL / GenBank specific subclass
        
        Used by the parse_records() and parse() methods.
        """
        pass

    def feed(self, handle, consumer, do_features=True) :
        """Feed a set of data into the consumer.

        This method is intended for use with the "old" code in Bio.GenBank

        Arguments:
        handle - A handle with the information to parse.
        consumer - The consumer that should be informed of events.
        do_features - Boolean, should the features be parsed?
                      Skipping the features can be much faster.

        Return values:
        true  - Passed a record
        false - Did not find a record
        """        
        #Should work with both EMBL and GenBank files provided the
        #equivalent Bio.GenBank._FeatureConsumer methods are called...
        self.set_handle(handle)
        if not self.find_start() :
            #Could not find (another) record
            consumer.data=None
            return False
                       
        #We use the above class methods to parse the file into a simplified format.
        #The first line, header lines and any misc lines after the features will be
        #dealt with by GenBank / EMBL specific derived classes.

        #First line and header:
        self._feed_first_line(consumer, self.line)
        self._feed_header_lines(consumer, self.parse_header())

        #Features (common to both EMBL and GenBank):
        if do_features :
            self._feed_feature_table(consumer, self.parse_features(skip=False))
        else :
            self.parse_features(skip=True) # ignore the data
        
        #Footer and sequence
        misc_lines, sequence_string = self.parse_footer()
        self._feed_misc_lines(consumer, misc_lines)

        consumer.sequence(sequence_string)
        #Calls to consumer.base_number() do nothing anyway
        consumer.record_end("//")

        assert self.line == "//"

        #And we are done
        return True

    def parse(self, handle, do_features=True) :
        """Returns a SeqRecord (with SeqFeatures if do_features=True)

        See also the method parse_records() for use on multi-record files.
        """
        from Bio.GenBank import _FeatureConsumer
        from Bio.GenBank.utils import FeatureValueCleaner

        consumer = _FeatureConsumer(use_fuzziness = 1, 
                    feature_cleaner = FeatureValueCleaner())

        if self.feed(handle, consumer) :
            return consumer.data
        else :
            return None

    
    def parse_records(self, handle, do_features=True) :
        """Returns a SeqRecord object iterator

        Each record (from the ID/LOCUS line to the // line) becomes a SeqRecord

        The SeqRecord objects include SeqFeatures if do_features=True
        """
        #This is a generator function
        while True :
            record = self.parse(handle)
            if record is None : break
            assert record.id is not None
            assert record.name <> "<unknown name>"
            assert record.description <> "<unknown description>"
            yield record

    def parse_cds_features(self, handle,
                           alphabet=generic_protein,
                           tags2id=('protein_id','locus_tag','product')) :
        """Returns SeqRecord object iterator

        Each CDS feature becomes a SeqRecord.

        alphabet - Used for any sequence found in a translation field.
        """
        self.set_handle(handle)
        while self.find_start() :
            #Got an EMBL or GenBank record...
            self.parse_header() # ignore header lines!
            feature_tuples = self.parse_features()
            #self.parse_footer() # ignore footer lines!
            for line in self.handle :
                if line[:2]=="//" : break
            self.line = line.rstrip()

            #Now go though those features...
            for key, location_string, qualifiers in feature_tuples :
                if key=="CDS" :
                    #Create SeqRecord
                    #================
                    #SeqRecord objects cannot be created with annotations, they
                    #must be added afterwards.  So create an empty record and
                    #then populate it:
                    record = SeqRecord(seq=None)
                    annotations = record.annotations

                    #Should we add a location object to the annotations?
                    #I *think* that only makes sense for SeqFeatures with their
                    #sub features...
                    annotations['raw_location'] = location_string.replace(' ','')

                    for (qualifier_name, qualifier_data) in qualifiers :
                        if qualifier_data is not None \
                        and qualifier_data[0]=='"' and qualifier_data[-1]=='"' :
                            #Remove quotes
                            qualifier_data = qualifier_data[1:-1]
                        #Append the data to the annotation qualifier...
                        if qualifier_name == "translation" :
                            assert record.seq is None, "Multiple translations!"
                            record.seq = Seq(qualifier_data.replace("\n",""), alphabet)
                        elif qualifier_name == "db_xref" :
                            #its a list, possibly empty.  Its safe to extend
                            record.dbxrefs.append(qualifier_data)
                        else :
                            if qualifier_data is not None :
                                qualifier_data = qualifier_data.replace("\n"," ").replace("  "," ")
                            try :
                                annotations[qualifier_name] += " " + qualifier_data
                            except KeyError :
                                #Not an addition to existing data, its the first bit
                                annotations[qualifier_name]= qualifier_data
                        
                    #Fill in the ID, Name, Description
                    #=================================
                    try :
                        record.id = annotations[tags2id[0]]
                    except KeyError :
                        pass
                    try :
                        record.name = annotations[tags2id[1]]
                    except KeyError :
                        pass
                    try :
                        record.description = annotations[tags2id[2]]
                    except KeyError :
                        pass

                    yield record

class EmblScanner(InsdcScanner) :
    """For extracting chunks of information in EMBL files"""

    RECORD_START = "ID   "
    HEADER_WIDTH = 5
    FEATURE_START_MARKERS = ["FH   Key             Location/Qualifiers","FH"]
    FEATURE_END_MARKERS = ["XX"] #XX can also mark the end of many things!
    FEATURE_QUALIFIER_INDENT = 21
    FEATURE_QUALIFIER_SPACER = "FT" + " " * (FEATURE_QUALIFIER_INDENT-2)
    SEQUENCE_HEADERS=["SQ"] #Remove trailing spaces

    def parse_footer(self) :
        """returns a tuple containing a list of any misc strings, and the sequence"""
        assert self.line[:self.HEADER_WIDTH].rstrip() in self.SEQUENCE_HEADERS, \
            "Eh? '%s'" % self.line

        #Note that the SQ line can be split into several lines...
        misc_lines = []
        while self.line[:self.HEADER_WIDTH].rstrip() in self.SEQUENCE_HEADERS :
            misc_lines.append(self.line)
            self.line = self.handle.readline()
            if not self.line :
                raise SyntaxError("Premature end of file")
            self.line = self.line.rstrip()

        assert self.line[:self.HEADER_WIDTH] == " " * self.HEADER_WIDTH
        
        seq_lines = []
        line = self.line
        while True :
            if not line :
                raise SyntaxError("Premature end of file in sequence data")
            line = line.strip()
            if not line :
                raise SyntaxError("Blank line in sequence data")
            if line=='//' :
                break
            assert self.line[:self.HEADER_WIDTH] == " " * self.HEADER_WIDTH
            seq_lines.append("".join(line.split()[:-1]))
            line = self.handle.readline()
        self.line = line
        return (misc_lines, "".join(seq_lines))

    def _feed_first_line(self, consumer, line) :
        assert line[:self.HEADER_WIDTH].rstrip() == "ID"
        fields = [data.strip() for data in line[self.HEADER_WIDTH:].strip().split(";")]
        assert len(fields) == 7
        """
        The tokens represent:
           0. Primary accession number
           1. Sequence version number
           2. Topology: 'circular' or 'linear'
           3. Molecule type (e.g. 'genomic DNA')
           4. Data class (e.g. 'STD')
           5. Taxonomic division (e.g. 'PRO')
           6. Sequence length (e.g. '4639675 BP.')
        """

        consumer.locus(fields[0])

        #Should we also call the accession consumer?
        #There should be an AC line later.
        #consumer.accession(fields[0])

        #TODO - How to deal with the version field?  At the moment the consumer
        #will try and use this for the ID which isn't ideal for EMBL files.
        #consumer.version(fields[1])
        consumer.version(fields[0]) #want it to be used as the ID

        #Based on how the old GenBank parser worked, merge these two:
        consumer.residue_type(" ".join(fields[2:3])) #TODO - Store as two fields?

        #consumer.xxx(fields[4]) #TODO - What should we do with the data class?

        consumer.data_file_division(fields[5])

        length_parts = fields[6].split()
        assert len(length_parts) == 2
        assert length_parts[1].upper() in ["BP", "BP."]
        consumer.size(length_parts[0])

    def _feed_header_lines(self, consumer, lines) :
        EMBL_INDENT = self.HEADER_WIDTH
        EMBL_SPACER = " "  * EMBL_INDENT
        consumer_dict = {
            'AC' : 'accession',
            'DE' : 'definition',
            #'RN' : 'reference_num',
            #'RP' : 'reference_bases',
            #'RX' : reference cross reference... DOI or Pubmed
            'RA' : 'authors',
            'RT' : 'title',
            'RL' : 'journal',
            'OS' : 'organism',
            'OC' : 'taxonomy',
            #'DR' : data reference?
            'CC' : 'comment',
            #'XX' : splitter
        }
        #We have to handle the following specially:
        #RX (depending on reference type...)
        lines = filter(None,lines)
        line_iter = iter(lines)
        try :
            while True :
                try :
                    line = line_iter.next()
                except StopIteration :
                    break
                if not line : break
                line_type = line[:EMBL_INDENT].strip()
                data = line[EMBL_INDENT:].strip()

                if line_type == 'XX' :
                    pass
                elif line_type == 'RN' :
                    # Reformat reference numbers for the GenBank based consumer
                    # e.g. '[1]' becomes '1'
                    if data[0] == "[" and data[-1] == "]" : data = data[1:-1]
                    consumer.reference_num(data)
                elif line_type == 'RP' :
                    # Reformat reference numbers for the GenBank based consumer
                    # e.g. '1-4639675' becomes '(bases 1 to 4639675)'
                    assert data.count("-")==1
                    consumer.reference_bases("(bases " + data.replace("-", " to ") + ")")
                elif line_type == 'RX' :
                    # TODO - I have seen both DOI and PubMed reference cross references
                    # The GenBank based consumer and Reference class may need extending here.
                    pass
                elif line_type == 'CC' :
                    # Have to pass a list of strings for this one (not just a string)
                    consumer.comment([data])
                elif line_type == 'DR' :
                    # TODO - Data reference...
                    pass
                elif line_type in consumer_dict :
                    #Its a semi-automatic entry!
                    getattr(consumer, consumer_dict[line_type])(data)
                else :
                    if self.debug :
                        print "Ignoring EMBL header line:\n%s" % line
        except StopIteration :
            raise SyntaxError("Problem with header")
        
    def _feed_misc_lines(self, consumer, lines) :
        #TODO - Should we do something with the information on the SQ line(s)?
        pass

class GenBankScanner(InsdcScanner) :
    """For extracting chunks of information in GenBank files"""

    RECORD_START = "LOCUS       "
    HEADER_WIDTH = 12
    FEATURE_START_MARKERS = ["FEATURES             Location/Qualifiers","FEATURES"]
    FEATURE_END_MARKERS = []
    FEATURE_QUALIFIER_INDENT = 21
    FEATURE_QUALIFIER_SPACER = " " * FEATURE_QUALIFIER_INDENT
    SEQUENCE_HEADERS=["CONTIG", "ORIGIN", "BASE COUNT"] # trailing spaces removed

    def parse_footer(self) :
        """returns a tuple containing a list of any misc strings, and the sequence"""
        assert self.line[:self.HEADER_WIDTH].rstrip() in self.SEQUENCE_HEADERS, \
               "Eh? '%s'" % self.line

        misc_lines = []
        while self.line[:self.HEADER_WIDTH].rstrip() in self.SEQUENCE_HEADERS \
        or self.line[:self.HEADER_WIDTH] == " "*self.HEADER_WIDTH :
            if self.line[-1] == "\n" : self.line = self.line[:-1]
            misc_lines.append(self.line)
            self.line = self.handle.readline()
            if not self.line :
                raise SyntaxError("Premature end of file")
            self.line = self.line.rstrip()

        assert self.line[:self.HEADER_WIDTH].rstrip() not in self.SEQUENCE_HEADERS, \
               "Eh? '%s'" % self.line

        #Now just consume the sequence lines until reach the // marker
        #or a CONTIG line
        seq_lines = []
        line = self.line
        while True :
            if not line :
                raise SyntaxError("Premature end of file in sequence data")
            line = line.rstrip()
            if not line :
                raise SyntaxError("Blank line in sequence data")
            if line=='//' :
                break
            if line.find('CONTIG')==0 :
                #What should we do with this?
                break
            if len(line) > 9 and  line[9:10]<>' ' :
                raise SyntaxError("Sequence line mal-formed, '%s'" % line)
            seq_lines.append(line[10:].replace(" ",""))
            line = self.handle.readline()

        self.line = line
        #Seq("".join(seq_lines), self.alphabet)
        return (misc_lines,"".join(seq_lines))

    def _feed_first_line(self, consumer, line) :
        #####################################
        # LOCUS line                        #
        #####################################
        GENBANK_INDENT = self.HEADER_WIDTH
        GENBANK_SPACER = " "*GENBANK_INDENT
        assert line[0:GENBANK_INDENT] == 'LOCUS       ', \
               'LOCUS line does not start correctly:\n' + line

        #Have to break up the locus line, and handle the different bits of it.
        #There are at least two different versions of the locus line...
        if line[29:33] in [' bp ', ' aa '] :
            #Old...
            #
            #    Positions  Contents
            #    ---------  --------
            #    00:06      LOCUS
            #    06:12      spaces
            #    12:??      Locus name
            #    ??:??      space
            #    ??:29      Length of sequence, right-justified
            #    29:33      space, bp, space
            #    33:41      strand type
            #    41:42      space
            #    42:51      Blank (implies linear), linear or circular
            #    51:52      space
            #    52:55      The division code (e.g. BCT, VRL, INV)
            #    55:62      space
            #    62:73      Date, in the form dd-MMM-yyyy (e.g., 15-MAR-1991)
            #
            assert line[29:33] in [' bp ', ' aa '] , \
                   'LOCUS line does not contain size units at expected position:\n' + line
            assert line[41:42] == ' ', \
                   'LOCUS line does not contain space at position 42:\n' + line
            assert line[42:51].strip() in ['','linear','circular'], \
                   'LOCUS line does not contain valid entry (linear, circular, ...):\n' + line
            assert line[51:52] == ' ', \
                   'LOCUS line does not contain space at position 52:\n' + line
            assert line[55:62] == '       ', \
                   'LOCUS line does not contain spaces from position 56 to 62:\n' + line
            assert line[64:65] == '-', \
                   'LOCUS line does not contain - at position 65 in date:\n' + line
            assert line[68:69] == '-', \
                   'LOCUS line does not contain - at position 69 in date:\n' + line

            name_and_length_str = line[GENBANK_INDENT:29]
            while name_and_length_str.find('  ')<>-1 :
                name_and_length_str = name_and_length_str.replace('  ',' ')
            name_and_length = name_and_length_str.split(' ')
            assert len(name_and_length)<=2, \
                   'Cannot parse the name and length in the LOCUS line:\n' + line
            assert len(name_and_length)<>1, \
                   'Name and length collide in the LOCUS line:\n' + line
                   #Should be possible to split them based on position, if
                   #a clear definition of the standard exists THAT AGREES with
                   #existing files.
            consumer.locus(name_and_length[0])
            consumer.size(name_and_length[1])
            #consumer.residue_type(line[33:41].strip())
            consumer.residue_type(line[33:51].strip())
            consumer.data_file_division(line[52:55])
            consumer.date(line[62:73])
        elif line[40:44] in [' bp ', ' aa '] :
            #New...
            #
            #    Positions  Contents
            #    ---------  --------
            #    00:06      LOCUS
            #    06:12      spaces
            #    12:??      Locus name
            #    ??:??      space
            #    ??:40      Length of sequence, right-justified
            #    40:44      space, bp, space
            #    44:47      Blank, ss-, ds-, ms-
            #    47:54      Blank, DNA, RNA, tRNA, mRNA, uRNA, snRNA
            #    54:55      space
            #    55:63      Blank (implies linear), linear or circular
            #    63:64      space
            #    64:67      The division code (e.g. BCT, VRL, INV)
            #    67:68      space
            #    68:79      Date, in the form dd-MMM-yyyy (e.g., 15-MAR-1991)
            #
            assert line[40:44] in [' bp ', ' aa '] , \
                   'LOCUS line does not contain size units at expected position:\n' + line
            assert line[44:47] in ['   ', 'ss-', 'ds-', 'ms-'], \
                    'LOCUS line does not have valid strand type (Single stranded, ...):\n' + line
            assert line[47:54].strip() in ['','DNA','RNA','tRNA','mRNA','uRNA','snRNA'], \
                   'LOCUS line does not contain valid sequence type (DNA, RNA, ...):\n' + line
            assert line[54:55] == ' ', \
                   'LOCUS line does not contain space at position 55:\n' + line
            assert line[55:63].strip() in ['','linear','circular'], \
                   'LOCUS line does not contain valid entry (linear, circular, ...):\n' + line
            assert line[63:64] == ' ', \
                   'LOCUS line does not contain space at position 64:\n' + line
            assert line[67:68] == ' ', \
                   'LOCUS line does not contain space at position 68:\n' + line
            assert line[70:71] == '-', \
                   'LOCUS line does not contain - at position 71 in date:\n' + line
            assert line[74:75] == '-', \
                   'LOCUS line does not contain - at position 75 in date:\n' + line

            name_and_length_str = line[GENBANK_INDENT:40]
            while name_and_length_str.find('  ')<>-1 :
                name_and_length_str = name_and_length_str.replace('  ',' ')
            name_and_length = name_and_length_str.split(' ')
            assert len(name_and_length)<=2, \
                   'Cannot parse the name and length in the LOCUS line:\n' + line
            assert len(name_and_length)<>1, \
                   'Name and length collide in the LOCUS line:\n' + line
                   #Should be possible to split them based on position, if
                   #a clear definition of the stand exists THAT AGREES with
                   #existing files.
            consumer.locus(name_and_length[0])
            consumer.size(name_and_length[1])
            consumer.residue_type(line[44:63].strip())
            consumer.data_file_division(line[64:67])
            consumer.date(line[68:79])
        elif line[GENBANK_INDENT:].strip().count(" ")==0 : 
            #Truncated LOCUS line, as produced by some EMBOSS tools - see bug 1762
            #
            #e.g.
            #
            #    "LOCUS       U00096"
            #
            #rather than:
            #
            #    "LOCUS       U00096               4639675 bp    DNA     circular BCT"
            #
            #    Positions  Contents
            #    ---------  --------
            #    00:06      LOCUS
            #    06:12      spaces
            #    12:??      Locus name
            if line[GENBANK_INDENT:].strip() <> "" :
                consumer.locus(line[GENBANK_INDENT:].strip())
            else :
                #Must just have just "LOCUS       ", is this even legitimate?
                #We should be able to continue parsing... we need real world testcases!
                print >> sys.stderr, "Warning: Minimal LOCUS line found - is this correct?\n" + line
        else :
            assert False, \
                   'Did not recognise the LOCUS line layout:\n' + line


    def _feed_header_lines(self, consumer, lines) :
        #Following dictionary maps GenBank lines to the associated
        #consumer methods - the special cases like LOCUS where one
        #genbank line triggers several consumer calls have to be
        #handled individually.
        GENBANK_INDENT = self.HEADER_WIDTH
        GENBANK_SPACER = " "*GENBANK_INDENT
        consumer_dict = {
            'DEFINITION' : 'definition',
            'ACCESSION'  : 'accession',
            'NID'        : 'nid',
            'PID'        : 'pid',
            'DBSOURCE'   : 'db_source',
            'KEYWORDS'   : 'keywords',
            'SEGMENT'    : 'segment',
            'SOURCE'     : 'source',
            'AUTHORS'    : 'authors',
            'CONSRTM'    : 'consrtm',
            'TITLE'      : 'title',
            'JOURNAL'    : 'journal',
            'MEDLINE'    : 'medline_id',
            'PUBMED'     : 'pubmed_id',
            'REMARK'     : 'remark'}
        #We have to handle the following specially:
        #ORIGIN (locus, size, residue_type, data_file_division and date)
        #COMMENT (comment)
        #VERSION (version and gi)
        #REFERENCE (eference_num and reference_bases)
        #ORGANISM (organism and taxonomy)
        lines = filter(None,lines)
        lines.append("") #helps avoid getting StopIteration all the time
        line_iter = iter(lines)
        try :
            line = line_iter.next()
            while True :
                if not line : break
                line_type = line[:GENBANK_INDENT].strip()
                data = line[GENBANK_INDENT:].strip()

                if line_type == 'VERSION' :
                    #Need to call consumer.version(), and maybe also consumer.gi() as well.
                    #e.g.
                    # VERSION     AC007323.5  GI:6587720
                    while data.find('  ')<>-1:
                        data = data.replace('  ',' ')
                    if data.find(' GI:')==-1 :
                        consumer.version(data)
                    else :
                        if self.debug : print "Version [" + data.split(' GI:')[0] + "], gi [" + data.split(' GI:')[1] + "]"
                        consumer.version(data.split(' GI:')[0])
                        consumer.gi(data.split(' GI:')[1])
                    #Read in the next line!
                    line = line_iter.next()
                elif line_type == 'REFERENCE' :
                    if self.debug >1 : print "Found reference [" + data + "]"
                    #Need to call consumer.reference_num() and consumer.reference_bases()
                    #e.g.
                    # REFERENCE   1  (bases 1 to 86436)
                    #
                    #Note that this can be multiline, see Bug 1968, e.g.
                    #
                    # REFERENCE   42 (bases 1517 to 1696; 3932 to 4112; 17880 to 17975; 21142 to
                    #             28259)
                    #
                    #For such cases we will call the consumer once only.
                    data = data.strip()

                    #Read in the next line, and see if its more of the reference:
                    while True:
                        line = line_iter.next()
                        if line[:GENBANK_INDENT] == GENBANK_SPACER :
                            #Add this continuation to the data string
                            data = data + " " + line[GENBANK_INDENT:]
                            if self.debug >1 : print "Extended reference text [" + data + "]"
                        else :
                            #End of the reference, leave this text in the variable "line"
                            break

                    #We now have all the reference line(s) stored in a string, data,
                    #which we pass to the consumer
                    while data.find('  ')<>-1:
                        data = data.replace('  ',' ')
                    if data.find(' ')==-1 :
                        if self.debug >2 : print 'Reference number \"' + data + '\"'
                        consumer.reference_num(data)
                    else :
                        if self.debug >2 : print 'Reference number \"' + data[:data.find(' ')] + '\", \"' + data[data.find(' ')+1:] + '\"'
                        consumer.reference_num(data[:data.find(' ')])
                        consumer.reference_bases(data[data.find(' ')+1:])
                elif line_type == 'ORGANISM' :
                    #The first line is the organism, but subsequent lines go to the taxonomy consumer
                    consumer.organism(data)
                    data = ""
                    while True :
                        line = line_iter.next()
                        if line[0:GENBANK_INDENT] == GENBANK_SPACER :
                            data = data + ' ' + line[GENBANK_INDENT:]
                        else :
                            #We now have all the data for this taxonomy:
                            consumer.taxonomy(data.strip())
                            #End of continuation - return to top of loop!
                            break
                elif line_type == 'COMMENT' :
                    if self.debug > 1 : print "Found comment"
                    #This can be multiline, and should call consumer.comment() once
                    #with a list where each entry is a line.
                    list=[]
                    list.append(data)
                    while True:
                        line = line_iter.next()
                        if line[0:GENBANK_INDENT] == GENBANK_SPACER :
                            data = line[GENBANK_INDENT:]
                            list.append(data)
                            if self.debug > 2 : print "Comment continuation [" + data + "]"
                        else :
                            #End of the comment
                            break
                    consumer.comment(list)
                    list=[]
                elif line_type in consumer_dict :
                    #Its a semi-automatic entry!
                    #Now, this may be a multi line entry...
                    while True :
                        line = line_iter.next()
                        if line[0:GENBANK_INDENT] == GENBANK_SPACER :
                            data += ' ' + line[GENBANK_INDENT:]
                        else :
                            #We now have all the data for this entry:
                            getattr(consumer, consumer_dict[line_type])(data)
                            #End of continuation - return to top of loop!
                            break
                else :
                    if self.debug :
                        print "Ignoring GenBank header line:\n" % line
                    #Read in next line
                    line = line_iter.next()
        except StopIteration :
            raise SyntaxError("Problem in header")
        
    def _feed_misc_lines(self, consumer, lines) :
        #Deals with a few misc lines between the features and the sequence
        GENBANK_INDENT = self.HEADER_WIDTH
        GENBANK_SPACER = " "*GENBANK_INDENT
        lines.append("")
        line_iter = iter(lines)
        try :
            for line in line_iter :
                if line.find('BASE COUNT')==0 :
                    line = line[10:].strip()
                    if line :
                        if self.debug : print "base_count = " + line
                        consumer.base_count(line)
                if line.find("ORIGIN")==0 :
                    line = line[6:].strip()
                    if line :
                        if self.debug : print "origin_name = " + line
                        consumer.origin_name(line)
                if line.find("CONTIG")==0 :
                    line = line[6:].strip()
                    contig_location = line + '\n'
                    while True :
                        line = line_iter.next()
                        if not line :
                            break
                        elif line[:GENBANK_INDENT]==GENBANK_SPACER :
                            contig_location += line.rstrip()
                        else:
                            raise SyntaxError('Expected CONTIG continuation line, got:\n' + line)
                    consumer.contig_location(contig_location)
            return
        except StopIteration :
            raise SyntaxError("Problem in misc lines before sequence")
        
if __name__ == "__main__" :
    from StringIO import StringIO

    gbk_example = \
"""LOCUS       SCU49845     5028 bp    DNA             PLN       21-JUN-1999
DEFINITION  Saccharomyces cerevisiae TCP1-beta gene, partial cds, and Axl2p
            (AXL2) and Rev7p (REV7) genes, complete cds.
ACCESSION   U49845
VERSION     U49845.1  GI:1293613
KEYWORDS    .
SOURCE      Saccharomyces cerevisiae (baker's yeast)
  ORGANISM  Saccharomyces cerevisiae
            Eukaryota; Fungi; Ascomycota; Saccharomycotina; Saccharomycetes;
            Saccharomycetales; Saccharomycetaceae; Saccharomyces.
REFERENCE   1  (bases 1 to 5028)
  AUTHORS   Torpey,L.E., Gibbs,P.E., Nelson,J. and Lawrence,C.W.
  TITLE     Cloning and sequence of REV7, a gene whose function is required for
            DNA damage-induced mutagenesis in Saccharomyces cerevisiae
  JOURNAL   Yeast 10 (11), 1503-1509 (1994)
  PUBMED    7871890
REFERENCE   2  (bases 1 to 5028)
  AUTHORS   Roemer,T., Madden,K., Chang,J. and Snyder,M.
  TITLE     Selection of axial growth sites in yeast requires Axl2p, a novel
            plasma membrane glycoprotein
  JOURNAL   Genes Dev. 10 (7), 777-793 (1996)
  PUBMED    8846915
REFERENCE   3  (bases 1 to 5028)
  AUTHORS   Roemer,T.
  TITLE     Direct Submission
  JOURNAL   Submitted (22-FEB-1996) Terry Roemer, Biology, Yale University, New
            Haven, CT, USA
FEATURES             Location/Qualifiers
     source          1..5028
                     /organism="Saccharomyces cerevisiae"
                     /db_xref="taxon:4932"
                     /chromosome="IX"
                     /map="9"
     CDS             <1..206
                     /codon_start=3
                     /product="TCP1-beta"
                     /protein_id="AAA98665.1"
                     /db_xref="GI:1293614"
                     /translation="SSIYNGISTSGLDLNNGTIADMRQLGIVESYKLKRAVVSSASEA
                     AEVLLRVDNIIRARPRTANRQHM"
     gene            687..3158
                     /gene="AXL2"
     CDS             687..3158
                     /gene="AXL2"
                     /note="plasma membrane glycoprotein"
                     /codon_start=1
                     /function="required for axial budding pattern of S.
                     cerevisiae"
                     /product="Axl2p"
                     /protein_id="AAA98666.1"
                     /db_xref="GI:1293615"
                     /translation="MTQLQISLLLTATISLLHLVVATPYEAYPIGKQYPPVARVNESF
                     TFQISNDTYKSSVDKTAQITYNCFDLPSWLSFDSSSRTFSGEPSSDLLSDANTTLYFN
                     VILEGTDSADSTSLNNTYQFVVTNRPSISLSSDFNLLALLKNYGYTNGKNALKLDPNE
                     VFNVTFDRSMFTNEESIVSYYGRSQLYNAPLPNWLFFDSGELKFTGTAPVINSAIAPE
                     TSYSFVIIATDIEGFSAVEVEFELVIGAHQLTTSIQNSLIINVTDTGNVSYDLPLNYV
                     YLDDDPISSDKLGSINLLDAPDWVALDNATISGSVPDELLGKNSNPANFSVSIYDTYG
                     DVIYFNFEVVSTTDLFAISSLPNINATRGEWFSYYFLPSQFTDYVNTNVSLEFTNSSQ
                     DHDWVKFQSSNLTLAGEVPKNFDKLSLGLKANQGSQSQELYFNIIGMDSKITHSNHSA
                     NATSTRSSHHSTSTSSYTSSTYTAKISSTSAAATSSAPAALPAANKTSSHNKKAVAIA
                     CGVAIPLGVILVALICFLIFWRRRRENPDDENLPHAISGPDLNNPANKPNQENATPLN
                     NPFDDDASSYDDTSIARRLAALNTLKLDNHSATESDISSVDEKRDSLSGMNTYNDQFQ
                     SQSKEELLAKPPVQPPESPFFDPQNRSSSVYMDSEPAVNKSWRYTGNLSPVSDIVRDS
                     YGSQKTVDTEKLFDLEAPEKEKRTSRDVTMSSLDPWNSNISPSPVRKSVTPSPYNVTK
                     HRNRHLQNIQDSQSGKNGITPTTMSTSSSDDFVPVKDGENFCWVHSMEPDRRPSKKRL
                     VDFSNKSNVNVGQVKDIHGRIPEML"
     gene            complement(3300..4037)
                     /gene="REV7"
     CDS             complement(3300..4037)
                     /gene="REV7"
                     /codon_start=1
                     /product="Rev7p"
                     /protein_id="AAA98667.1"
                     /db_xref="GI:1293616"
                     /translation="MNRWVEKWLRVYLKCYINLILFYRNVYPPQSFDYTTYQSFNLPQ
                     FVPINRHPALIDYIEELILDVLSKLTHVYRFSICIINKKNDLCIEKYVLDFSELQHVD
                     KDDQIITETEVFDEFRSSLNSLIMHLEKLPKVNDDTITFEAVINAIELELGHKLDRNR
                     RVDSLEEKAEIERDSNWVKCQEDENLPDNNGFQPPKIKLTSLVGSDVGPLIIHQFSEK
                     LISGDDKILNGVYSQYEEGESIFGSLF"
ORIGIN
        1 gatcctccat atacaacggt atctccacct caggtttaga tctcaacaac ggaaccattg
       61 ccgacatgag acagttaggt atcgtcgaga gttacaagct aaaacgagca gtagtcagct
      121 ctgcatctga agccgctgaa gttctactaa gggtggataa catcatccgt gcaagaccaa
      181 gaaccgccaa tagacaacat atgtaacata tttaggatat acctcgaaaa taataaaccg
      241 ccacactgtc attattataa ttagaaacag aacgcaaaaa ttatccacta tataattcaa
      301 agacgcgaaa aaaaaagaac aacgcgtcat agaacttttg gcaattcgcg tcacaaataa
      361 attttggcaa cttatgtttc ctcttcgagc agtactcgag ccctgtctca agaatgtaat
      421 aatacccatc gtaggtatgg ttaaagatag catctccaca acctcaaagc tccttgccga
      481 gagtcgccct cctttgtcga gtaattttca cttttcatat gagaacttat tttcttattc
      541 tttactctca catcctgtag tgattgacac tgcaacagcc accatcacta gaagaacaga
      601 acaattactt aatagaaaaa ttatatcttc ctcgaaacga tttcctgctt ccaacatcta
      661 cgtatatcaa gaagcattca cttaccatga cacagcttca gatttcatta ttgctgacag
      721 ctactatatc actactccat ctagtagtgg ccacgcccta tgaggcatat cctatcggaa
      781 aacaataccc cccagtggca agagtcaatg aatcgtttac atttcaaatt tccaatgata
      841 cctataaatc gtctgtagac aagacagctc aaataacata caattgcttc gacttaccga
      901 gctggctttc gtttgactct agttctagaa cgttctcagg tgaaccttct tctgacttac
      961 tatctgatgc gaacaccacg ttgtatttca atgtaatact cgagggtacg gactctgccg
     1021 acagcacgtc tttgaacaat acataccaat ttgttgttac aaaccgtcca tccatctcgc
     1081 tatcgtcaga tttcaatcta ttggcgttgt taaaaaacta tggttatact aacggcaaaa
     1141 acgctctgaa actagatcct aatgaagtct tcaacgtgac ttttgaccgt tcaatgttca
     1201 ctaacgaaga atccattgtg tcgtattacg gacgttctca gttgtataat gcgccgttac
     1261 ccaattggct gttcttcgat tctggcgagt tgaagtttac tgggacggca ccggtgataa
     1321 actcggcgat tgctccagaa acaagctaca gttttgtcat catcgctaca gacattgaag
     1381 gattttctgc cgttgaggta gaattcgaat tagtcatcgg ggctcaccag ttaactacct
     1441 ctattcaaaa tagtttgata atcaacgtta ctgacacagg taacgtttca tatgacttac
     1501 ctctaaacta tgtttatctc gatgacgatc ctatttcttc tgataaattg ggttctataa
     1561 acttattgga tgctccagac tgggtggcat tagataatgc taccatttcc gggtctgtcc
     1621 cagatgaatt actcggtaag aactccaatc ctgccaattt ttctgtgtcc atttatgata
     1681 cttatggtga tgtgatttat ttcaacttcg aagttgtctc cacaacggat ttgtttgcca
     1741 ttagttctct tcccaatatt aacgctacaa ggggtgaatg gttctcctac tattttttgc
     1801 cttctcagtt tacagactac gtgaatacaa acgtttcatt agagtttact aattcaagcc
     1861 aagaccatga ctgggtgaaa ttccaatcat ctaatttaac attagctgga gaagtgccca
     1921 agaatttcga caagctttca ttaggtttga aagcgaacca aggttcacaa tctcaagagc
     1981 tatattttaa catcattggc atggattcaa agataactca ctcaaaccac agtgcgaatg
     2041 caacgtccac aagaagttct caccactcca cctcaacaag ttcttacaca tcttctactt
     2101 acactgcaaa aatttcttct acctccgctg ctgctacttc ttctgctcca gcagcgctgc
     2161 cagcagccaa taaaacttca tctcacaata aaaaagcagt agcaattgcg tgcggtgttg
     2221 ctatcccatt aggcgttatc ctagtagctc tcatttgctt cctaatattc tggagacgca
     2281 gaagggaaaa tccagacgat gaaaacttac cgcatgctat tagtggacct gatttgaata
     2341 atcctgcaaa taaaccaaat caagaaaacg ctacaccttt gaacaacccc tttgatgatg
     2401 atgcttcctc gtacgatgat acttcaatag caagaagatt ggctgctttg aacactttga
     2461 aattggataa ccactctgcc actgaatctg atatttccag cgtggatgaa aagagagatt
     2521 ctctatcagg tatgaataca tacaatgatc agttccaatc ccaaagtaaa gaagaattat
     2581 tagcaaaacc cccagtacag cctccagaga gcccgttctt tgacccacag aataggtctt
     2641 cttctgtgta tatggatagt gaaccagcag taaataaatc ctggcgatat actggcaacc
     2701 tgtcaccagt ctctgatatt gtcagagaca gttacggatc acaaaaaact gttgatacag
     2761 aaaaactttt cgatttagaa gcaccagaga aggaaaaacg tacgtcaagg gatgtcacta
     2821 tgtcttcact ggacccttgg aacagcaata ttagcccttc tcccgtaaga aaatcagtaa
     2881 caccatcacc atataacgta acgaagcatc gtaaccgcca cttacaaaat attcaagact
     2941 ctcaaagcgg taaaaacgga atcactccca caacaatgtc aacttcatct tctgacgatt
     3001 ttgttccggt taaagatggt gaaaattttt gctgggtcca tagcatggaa ccagacagaa
     3061 gaccaagtaa gaaaaggtta gtagattttt caaataagag taatgtcaat gttggtcaag
     3121 ttaaggacat tcacggacgc atcccagaaa tgctgtgatt atacgcaacg atattttgct
     3181 taattttatt ttcctgtttt attttttatt agtggtttac agatacccta tattttattt
     3241 agtttttata cttagagaca tttaatttta attccattct tcaaatttca tttttgcact
     3301 taaaacaaag atccaaaaat gctctcgccc tcttcatatt gagaatacac tccattcaaa
     3361 attttgtcgt caccgctgat taatttttca ctaaactgat gaataatcaa aggccccacg
     3421 tcagaaccga ctaaagaagt gagttttatt ttaggaggtt gaaaaccatt attgtctggt
     3481 aaattttcat cttcttgaca tttaacccag tttgaatccc tttcaatttc tgctttttcc
     3541 tccaaactat cgaccctcct gtttctgtcc aacttatgtc ctagttccaa ttcgatcgca
     3601 ttaataactg cttcaaatgt tattgtgtca tcgttgactt taggtaattt ctccaaatgc
     3661 ataatcaaac tatttaagga agatcggaat tcgtcgaaca cttcagtttc cgtaatgatc
     3721 tgatcgtctt tatccacatg ttgtaattca ctaaaatcta aaacgtattt ttcaatgcat
     3781 aaatcgttct ttttattaat aatgcagatg gaaaatctgt aaacgtgcgt taatttagaa
     3841 agaacatcca gtataagttc ttctatatag tcaattaaag caggatgcct attaatggga
     3901 acgaactgcg gcaagttgaa tgactggtaa gtagtgtagt cgaatgactg aggtgggtat
     3961 acatttctat aaaataaaat caaattaatg tagcatttta agtataccct cagccacttc
     4021 tctacccatc tattcataaa gctgacgcaa cgattactat tttttttttc ttcttggatc
     4081 tcagtcgtcg caaaaacgta taccttcttt ttccgacctt ttttttagct ttctggaaaa
     4141 gtttatatta gttaaacagg gtctagtctt agtgtgaaag ctagtggttt cgattgactg
     4201 atattaagaa agtggaaatt aaattagtag tgtagacgta tatgcatatg tatttctcgc
     4261 ctgtttatgt ttctacgtac ttttgattta tagcaagggg aaaagaaata catactattt
     4321 tttggtaaag gtgaaagcat aatgtaaaag ctagaataaa atggacgaaa taaagagagg
     4381 cttagttcat cttttttcca aaaagcaccc aatgataata actaaaatga aaaggatttg
     4441 ccatctgtca gcaacatcag ttgtgtgagc aataataaaa tcatcacctc cgttgccttt
     4501 agcgcgtttg tcgtttgtat cttccgtaat tttagtctta tcaatgggaa tcataaattt
     4561 tccaatgaat tagcaatttc gtccaattct ttttgagctt cttcatattt gctttggaat
     4621 tcttcgcact tcttttccca ttcatctctt tcttcttcca aagcaacgat ccttctaccc
     4681 atttgctcag agttcaaatc ggcctctttc agtttatcca ttgcttcctt cagtttggct
     4741 tcactgtctt ctagctgttg ttctagatcc tggtttttct tggtgtagtt ctcattatta
     4801 gatctcaagt tattggagtc ttcagccaat tgctttgtat cagacaattg actctctaac
     4861 ttctccactt cactgtcgag ttgctcgttt ttagcggaca aagatttaat ctcgttttct
     4921 ttttcagtgt tagattgctc taattctttg agctgttctc tcagctcctc atatttttct
     4981 tgccatgact cagattctaa ttttaagcta ttcaatttct ctttgatc
//"""

    # GenBank format protein (aka GenPept) file from:
    # http://www.molecularevolution.org/resources/fileformats/
    gbk_example2 = \
"""LOCUS       AAD51968                 143 aa            linear   BCT 21-AUG-2001
DEFINITION  transcriptional regulator RovA [Yersinia enterocolitica].
ACCESSION   AAD51968
VERSION     AAD51968.1  GI:5805369
DBSOURCE    locus AF171097 accession AF171097.1
KEYWORDS    .
SOURCE      Yersinia enterocolitica
  ORGANISM  Yersinia enterocolitica
            Bacteria; Proteobacteria; Gammaproteobacteria; Enterobacteriales;
            Enterobacteriaceae; Yersinia.
REFERENCE   1  (residues 1 to 143)
  AUTHORS   Revell,P.A. and Miller,V.L.
  TITLE     A chromosomally encoded regulator is required for expression of the
            Yersinia enterocolitica inv gene and for virulence
  JOURNAL   Mol. Microbiol. 35 (3), 677-685 (2000)
  MEDLINE   20138369
   PUBMED   10672189
REFERENCE   2  (residues 1 to 143)
  AUTHORS   Revell,P.A. and Miller,V.L.
  TITLE     Direct Submission
  JOURNAL   Submitted (22-JUL-1999) Molecular Microbiology, Washington
            University School of Medicine, Campus Box 8230, 660 South Euclid,
            St. Louis, MO 63110, USA
COMMENT     Method: conceptual translation.
FEATURES             Location/Qualifiers
     source          1..143
                     /organism="Yersinia enterocolitica"
                     /mol_type="unassigned DNA"
                     /strain="JB580v"
                     /serotype="O:8"
                     /db_xref="taxon:630"
     Protein         1..143
                     /product="transcriptional regulator RovA"
                     /name="regulates inv expression"
     CDS             1..143
                     /gene="rovA"
                     /coded_by="AF171097.1:380..811"
                     /note="regulator of virulence"
                     /transl_table=11
ORIGIN      
        1 mestlgsdla rlvrvwrali dhrlkplelt qthwvtlhni nrlppeqsqi qlakaigieq
       61 pslvrtldql eekglitrht candrrakri klteqsspii eqvdgvicst rkeilggisp
      121 deiellsgli dklerniiql qsk
//
"""
    
    embl_example="""ID   X56734; SV 1; linear; mRNA; STD; PLN; 1859 BP.
XX
AC   X56734; S46826;
XX
DT   12-SEP-1991 (Rel. 29, Created)
DT   25-NOV-2005 (Rel. 85, Last updated, Version 11)
XX
DE   Trifolium repens mRNA for non-cyanogenic beta-glucosidase
XX
KW   beta-glucosidase.
XX
OS   Trifolium repens (white clover)
OC   Eukaryota; Viridiplantae; Streptophyta; Embryophyta; Tracheophyta;
OC   Spermatophyta; Magnoliophyta; eudicotyledons; core eudicotyledons; rosids;
OC   eurosids I; Fabales; Fabaceae; Papilionoideae; Trifolieae; Trifolium.
XX
RN   [5]
RP   1-1859
RX   PUBMED; 1907511.
RA   Oxtoby E., Dunn M.A., Pancoro A., Hughes M.A.;
RT   "Nucleotide and derived amino acid sequence of the cyanogenic
RT   beta-glucosidase (linamarase) from white clover (Trifolium repens L.)";
RL   Plant Mol. Biol. 17(2):209-219(1991).
XX
RN   [6]
RP   1-1859
RA   Hughes M.A.;
RT   ;
RL   Submitted (19-NOV-1990) to the EMBL/GenBank/DDBJ databases.
RL   Hughes M.A., University of Newcastle Upon Tyne, Medical School, Newcastle
RL   Upon Tyne, NE2 4HH, UK
XX
FH   Key             Location/Qualifiers
FH
FT   source          1..1859
FT                   /organism="Trifolium repens"
FT                   /mol_type="mRNA"
FT                   /clone_lib="lambda gt10"
FT                   /clone="TRE361"
FT                   /tissue_type="leaves"
FT                   /db_xref="taxon:3899"
FT   CDS             14..1495
FT                   /product="beta-glucosidase"
FT                   /EC_number="3.2.1.21"
FT                   /note="non-cyanogenic"
FT                   /db_xref="GOA:P26204"
FT                   /db_xref="InterPro:IPR001360"
FT                   /db_xref="InterPro:IPR013781"
FT                   /db_xref="UniProtKB/Swiss-Prot:P26204"
FT                   /protein_id="CAA40058.1"
FT                   /translation="MDFIVAIFALFVISSFTITSTNAVEASTLLDIGNLSRSSFPRGFI
FT                   FGAGSSAYQFEGAVNEGGRGPSIWDTFTHKYPEKIRDGSNADITVDQYHRYKEDVGIMK
FT                   DQNMDSYRFSISWPRILPKGKLSGGINHEGIKYYNNLINELLANGIQPFVTLFHWDLPQ
FT                   VLEDEYGGFLNSGVINDFRDYTDLCFKEFGDRVRYWSTLNEPWVFSNSGYALGTNAPGR
FT                   CSASNVAKPGDSGTGPYIVTHNQILAHAEAVHVYKTKYQAYQKGKIGITLVSNWLMPLD
FT                   DNSIPDIKAAERSLDFQFGLFMEQLTTGDYSKSMRRIVKNRLPKFSKFESSLVNGSFDF
FT                   IGINYYSSSYISNAPSHGNAKPSYSTNPMTNISFEKHGIPLGPRAASIWIYVYPYMFIQ
FT                   EDFEIFCYILKINITILQFSITENGMNEFNDATLPVEEALLNTYRIDYYYRHLYYIRSA
FT                   IRAGSNVKGFYAWSFLDCNEWFAGFTVRFGLNFVD"
FT   mRNA            1..1859
FT                   /experiment="experimental evidence, no additional details
FT                   recorded"
XX
SQ   Sequence 1859 BP; 609 A; 314 C; 355 G; 581 T; 0 other;
     aaacaaacca aatatggatt ttattgtagc catatttgct ctgtttgtta ttagctcatt        60
     cacaattact tccacaaatg cagttgaagc ttctactctt cttgacatag gtaacctgag       120
     tcggagcagt tttcctcgtg gcttcatctt tggtgctgga tcttcagcat accaatttga       180
     aggtgcagta aacgaaggcg gtagaggacc aagtatttgg gataccttca cccataaata       240
     tccagaaaaa ataagggatg gaagcaatgc agacatcacg gttgaccaat atcaccgcta       300
     caaggaagat gttgggatta tgaaggatca aaatatggat tcgtatagat tctcaatctc       360
     ttggccaaga atactcccaa agggaaagtt gagcggaggc ataaatcacg aaggaatcaa       420
     atattacaac aaccttatca acgaactatt ggctaacggt atacaaccat ttgtaactct       480
     ttttcattgg gatcttcccc aagtcttaga agatgagtat ggtggtttct taaactccgg       540
     tgtaataaat gattttcgag actatacgga tctttgcttc aaggaatttg gagatagagt       600
     gaggtattgg agtactctaa atgagccatg ggtgtttagc aattctggat atgcactagg       660
     aacaaatgca ccaggtcgat gttcggcctc caacgtggcc aagcctggtg attctggaac       720
     aggaccttat atagttacac acaatcaaat tcttgctcat gcagaagctg tacatgtgta       780
     taagactaaa taccaggcat atcaaaaggg aaagataggc ataacgttgg tatctaactg       840
     gttaatgcca cttgatgata atagcatacc agatataaag gctgccgaga gatcacttga       900
     cttccaattt ggattgttta tggaacaatt aacaacagga gattattcta agagcatgcg       960
     gcgtatagtt aaaaaccgat tacctaagtt ctcaaaattc gaatcaagcc tagtgaatgg      1020
     ttcatttgat tttattggta taaactatta ctcttctagt tatattagca atgccccttc      1080
     acatggcaat gccaaaccca gttactcaac aaatcctatg accaatattt catttgaaaa      1140
     acatgggata cccttaggtc caagggctgc ttcaatttgg atatatgttt atccatatat      1200
     gtttatccaa gaggacttcg agatcttttg ttacatatta aaaataaata taacaatcct      1260
     gcaattttca atcactgaaa atggtatgaa tgaattcaac gatgcaacac ttccagtaga      1320
     agaagctctt ttgaatactt acagaattga ttactattac cgtcacttat actacattcg      1380
     ttctgcaatc agggctggct caaatgtgaa gggtttttac gcatggtcat ttttggactg      1440
     taatgaatgg tttgcaggct ttactgttcg ttttggatta aactttgtag attagaaaga      1500
     tggattaaaa aggtacccta agctttctgc ccaatggtac aagaactttc tcaaaagaaa      1560
     ctagctagta ttattaaaag aactttgtag tagattacag tacatcgttt gaagttgagt      1620
     tggtgcacct aattaaataa aagaggttac tcttaacata tttttaggcc attcgttgtg      1680
     aagttgttag gctgttattt ctattatact atgttgtagt aataagtgca ttgttgtacc      1740
     agaagctatg atcataacta taggttgatc cttcatgtat cagtttgatg ttgagaatac      1800
     tttgaattaa aagtcttttt ttattttttt aaaaaaaaaa aaaaaaaaaa aaaaaaaaa       1859
//
"""

    print "GenBank CDS Iteration"
    print "====================="

    g = GenBankScanner()
    for record in g.parse_cds_features(StringIO(gbk_example)) :
        print record
        
    g = GenBankScanner()
    for record in g.parse_cds_features(StringIO(gbk_example2),
                  tags2id=('gene','locus_tag','product')) :
        print record

    g = GenBankScanner()
    for record in g.parse_cds_features(StringIO(gbk_example + "\n" + gbk_example2),
                                       tags2id=('gene','locus_tag','product')) :
        print record

    print
    print "GenBank Iteration"
    print "================="
    g = GenBankScanner()
    for record in g.parse_records(StringIO(gbk_example),do_features=False) :
        print record.id, record.name, record.description
        print record.seq

    g = GenBankScanner()
    for record in g.parse_records(StringIO(gbk_example),do_features=True) :
        print record.id, record.name, record.description
        print record.seq

    g = GenBankScanner()
    for record in g.parse_records(StringIO(gbk_example2),do_features=False) :
        print record.id, record.name, record.description
        print record.seq

    g = GenBankScanner()
    for record in g.parse_records(StringIO(gbk_example2),do_features=True) :
        print record.id, record.name, record.description
        print record.seq

    print
    print "EMBL CDS Iteration"
    print "=================="

    e = EmblScanner()
    for record in e.parse_cds_features(StringIO(embl_example)) :
        print record
        
    print
    print "EMBL Iteration"
    print "=============="
    e = EmblScanner()
    for record in e.parse_records(StringIO(embl_example),do_features=True) :
        print record.id, record.name, record.description
        print record.seq

