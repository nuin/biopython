# Copyright 1999-2000 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.
# Patches by Mike Poidinger to support multiple databases.

"""
This module provides code to work with the standalone version of
BLAST, either blastall or blastpgp, provided by the NCBI.
http://www.ncbi.nlm.nih.gov/BLAST/

Classes:
LowQualityBlastError     Except that indicates low quality query sequences.
BlastParser              Parses output from blast.
BlastErrorParser         Parses output and tries to diagnose possible errors.
PSIBlastParser           Parses output from psi-blast.
Iterator                 Iterates over a file of blast results.

_Scanner                 Scans output from standalone BLAST.
_BlastConsumer           Consumes output from blast.
_PSIBlastConsumer        Consumes output from psi-blast.
_HeaderConsumer          Consumes header information.
_DescriptionConsumer     Consumes description information.
_AlignmentConsumer       Consumes alignment information.
_HSPConsumer             Consumes hsp information.
_DatabaseReportConsumer  Consumes database report information.
_ParametersConsumer      Consumes parameters information.

Functions:
blastall        Execute blastall.
blastpgp        Execute blastpgp.

"""

from __future__ import generators
import os
import re

from Bio import File
from Bio.ParserSupport import *
from Bio.Blast import Record


class LowQualityBlastError(Exception):
    """Error caused by running a low quality sequence through BLAST.

    When low quality sequences (like GenBank entries containing only
    stretches of a single nucleotide) are BLASTed, they will result in
    BLAST generating an error and not being able to perform the BLAST.
    search. This error should be raised for the BLAST reports produced
    in this case.
    """
    pass

class ShortQueryBlastError(Exception):
    """Error caused by running a short query sequence through BLAST.

    If the query sequence is too short, BLAST outputs warnings and errors:
    Searching[blastall] WARNING:  [000.000]  AT1G08320: SetUpBlastSearch failed.
    [blastall] ERROR:  [000.000]  AT1G08320: Blast: 
    [blastall] ERROR:  [000.000]  AT1G08320: Blast: Query must be at least wordsize
    done

    This exception is raised when that condition is detected.

    """
    pass
    

class _Scanner:
    """Scan BLAST output from blastall or blastpgp.

    Tested with blastall and blastpgp v2.0.10, v2.0.11

    Methods:
    feed     Feed data into the scanner.
    
    """
    def feed(self, handle, consumer):
        """S.feed(handle, consumer)

        Feed in a BLAST report for scanning.  handle is a file-like
        object that contains the BLAST report.  consumer is a Consumer
        object that will receive events as the report is scanned.

        """
        if isinstance(handle, File.UndoHandle):
            uhandle = handle
        else:
            uhandle = File.UndoHandle(handle)

        # Try to fast-forward to the beginning of the blast report.
        read_and_call_until(uhandle, consumer.noevent, contains='BLAST')
        # Now scan the BLAST report.
        self._scan_header(uhandle, consumer)
	self._scan_rounds(uhandle, consumer)
        self._scan_database_report(uhandle, consumer)
        self._scan_parameters(uhandle, consumer)

    def _scan_header(self, uhandle, consumer):
        # BLASTP 2.0.10 [Aug-26-1999]
        # 
        # 
        # Reference: Altschul, Stephen F., Thomas L. Madden, Alejandro A. Schaf
        # Jinghui Zhang, Zheng Zhang, Webb Miller, and David J. Lipman (1997), 
        # "Gapped BLAST and PSI-BLAST: a new generation of protein database sea
        # programs",  Nucleic Acids Res. 25:3389-3402.
        # 
        # Query= test
        #          (140 letters)
        # 
        # Database: sdqib40-1.35.seg.fa
        #            1323 sequences; 223,339 total letters
        #

        consumer.start_header()

        read_and_call(uhandle, consumer.version, contains='BLAST')
        read_and_call_while(uhandle, consumer.noevent, blank=1)

        # Read the reference lines and the following blank line.
        read_and_call(uhandle, consumer.reference, start='Reference')
        read_and_call_until(uhandle, consumer.reference, blank=1)
        read_and_call_while(uhandle, consumer.noevent, blank=1)

        # Read the Query lines and the following blank line.
        read_and_call(uhandle, consumer.query_info, start='Query=')
        read_and_call_until(uhandle, consumer.query_info, blank=1)
        read_and_call_while(uhandle, consumer.noevent, blank=1)

        # Read the database lines and the following blank line.
        read_and_call_until(uhandle, consumer.database_info, end='total letters')
        read_and_call(uhandle, consumer.database_info, contains='sequences')
        read_and_call_while(uhandle, consumer.noevent, blank=1)

        consumer.end_header()

    def _scan_rounds(self, uhandle, consumer):
        # Scan a bunch of rounds.
        # Each round begins with either a "Searching......" line
        # or a 'Score     E' line followed by descriptions and alignments.
        # The email server doesn't give the "Searching....." line.

        while 1:
            line = safe_peekline(uhandle)
            if (not line.startswith('Searching') and
                re.search(r"Score +E", line) is None and
                line.find('No hits found') == -1):
                break

            self._scan_descriptions(uhandle, consumer)
            self._scan_alignments(uhandle, consumer)

    def _scan_descriptions(self, uhandle, consumer):
        # Searching..................................................done
        # Results from round 2
        # 
        # 
        #                                                                    Sc
        # Sequences producing significant alignments:                        (b
        # Sequences used in model and found again:
        # 
        # d1tde_2 3.4.1.4.4 (119-244) Thioredoxin reductase [Escherichia ...   
        # d1tcob_ 1.31.1.5.16 Calcineurin regulatory subunit (B-chain) [B...   
        # d1symb_ 1.31.1.2.2 Calcyclin (S100) [RAT (RATTUS NORVEGICUS)]        
        # 
        # Sequences not found previously or not previously below threshold:
        # 
        # d1osa__ 1.31.1.5.11 Calmodulin [Paramecium tetraurelia]              
        # d1aoza3 2.5.1.3.3 (339-552) Ascorbate oxidase [zucchini (Cucurb...   
        #

        # If PSI-BLAST, may also have:
        #
        # CONVERGED!

        consumer.start_descriptions()

        # Read 'Searching'
        # This line seems to be missing in BLASTN 2.1.2 (others?)
        attempt_read_and_call(uhandle, consumer.noevent, start='Searching')

        # blastpgp 2.0.10 from NCBI 9/19/99 for Solaris sometimes crashes here.
        # If this happens, the handle will yield no more information.
        if not uhandle.peekline():
            raise SyntaxError, "Unexpected end of blast report.  " + \
                  "Looks suspiciously like a PSI-BLAST crash."

        # BLASTN 2.2.3 sometimes spews a bunch of warnings and errors here:
        # Searching[blastall] WARNING:  [000.000]  AT1G08320: SetUpBlastSearch 
        # [blastall] ERROR:  [000.000]  AT1G08320: Blast: 
        # [blastall] ERROR:  [000.000]  AT1G08320: Blast: Query must be at leas
        # done 
        # Reported by David Weisman.
        # Check for these error lines and ignore them for now.  Let
        # the BlastErrorParser deal with them.
        line = uhandle.peekline()
        if line.find("ERROR:") != -1 or line.startswith("done"):
            read_and_call_while(uhandle, consumer.noevent, contains="ERROR:")
            read_and_call(uhandle, consumer.noevent, start="done")

        # Check to see if this is PSI-BLAST.
        # If it is, the 'Searching' line will be followed by:
        # (version 2.0.10)
        #     Searching.............................
        #     Results from round 2
        # or (version 2.0.11)
        #     Searching.............................
        #
        #
        #     Results from round 2
        
        # Skip a bunch of blank lines.
        read_and_call_while(uhandle, consumer.noevent, blank=1)
        # Check for the results line if it's there.
        if attempt_read_and_call(uhandle, consumer.round, start='Results'):
            read_and_call_while(uhandle, consumer.noevent, blank=1)
        
        # Three things can happen here:
        # 1.  line contains 'Score     E'
        # 2.  line contains "No hits found"
        # 3.  no descriptions
        # The first one begins a bunch of descriptions.  The last two
        # indicates that no descriptions follow, and we should go straight
        # to the alignments.
        if not attempt_read_and_call(
            uhandle, consumer.description_header,
            has_re=re.compile(r'Score {4,5}E')):
            # Either case 2 or 3.  Look for "No hits found".
            attempt_read_and_call(uhandle, consumer.no_hits,
                                  contains='No hits found')
            read_and_call_while(uhandle, consumer.noevent, blank=1)

	    #Psiblast can repeat the Searching...No hits found section
	    if attempt_read_and_call(uhandle, consumer.noevent,
                                     start='Searching'):
	        read_and_call_while(uhandle, consumer.noevent, blank=1)
	        read_and_call(uhandle, consumer.noevent,
                              contains='No hits found')
	        read_and_call_while(uhandle, consumer.noevent, blank=1)
	    
            consumer.end_descriptions()
            # Stop processing.
            return

        # Read the score header lines
        read_and_call(uhandle, consumer.description_header,
                      start='Sequences producing')

        # If PSI-BLAST, read the 'Sequences used in model' line.
        attempt_read_and_call(uhandle, consumer.model_sequences,
                              start='Sequences used in model')
        read_and_call_while(uhandle, consumer.noevent, blank=1)

        # Read the descriptions and the following blank lines, making
        # sure that there are descriptions.
        if not uhandle.peekline().startswith('Sequences not found'):
            read_and_call_until(uhandle, consumer.description, blank=1)
            read_and_call_while(uhandle, consumer.noevent, blank=1)

        # If PSI-BLAST, read the 'Sequences not found' line followed
        # by more descriptions.  However, I need to watch out for the
        # case where there were no sequences not found previously, in
        # which case there will be no more descriptions.
        if attempt_read_and_call(uhandle, consumer.nonmodel_sequences,
                                 start='Sequences not found'):
            # Read the descriptions and the following blank lines.
            read_and_call_while(uhandle, consumer.noevent, blank=1)
            l = safe_peekline(uhandle)
            # Brad -- added check for QUERY. On some PSI-BLAST outputs
            # there will be a 'Sequences not found' line followed by no
            # descriptions. Check for this case since the first thing you'll
            # get is a blank line and then 'QUERY'
            if not l.startswith('CONVERGED') and l[0] != '>' \
                    and not l.startswith('QUERY'):
                read_and_call_until(uhandle, consumer.description, blank=1)
                read_and_call_while(uhandle, consumer.noevent, blank=1)

        attempt_read_and_call(uhandle, consumer.converged, start='CONVERGED')
        read_and_call_while(uhandle, consumer.noevent, blank=1)

        consumer.end_descriptions()

    def _scan_alignments(self, uhandle, consumer):
        # First, check to see if I'm at the database report.
        line = safe_peekline(uhandle)
        if line.startswith('  Database'):
            return
        elif line[0] == '>':
            # XXX make a better check here between pairwise and masterslave
            self._scan_pairwise_alignments(uhandle, consumer)
        else:
            # XXX put in a check to make sure I'm in a masterslave alignment
            self._scan_masterslave_alignment(uhandle, consumer)

    def _scan_pairwise_alignments(self, uhandle, consumer):
        while 1:
            line = safe_peekline(uhandle)
            if line[0] != '>':
                break
            self._scan_one_pairwise_alignment(uhandle, consumer)

    def _scan_one_pairwise_alignment(self, uhandle, consumer):
        consumer.start_alignment()

        self._scan_alignment_header(uhandle, consumer)

        # Scan a bunch of score/alignment pairs.
        while 1:
            line = safe_peekline(uhandle)
            if not line.startswith(' Score'):
                break
            self._scan_hsp(uhandle, consumer)
        consumer.end_alignment()

    def _scan_alignment_header(self, uhandle, consumer):
        # >d1rip__ 2.24.7.1.1 Ribosomal S17 protein [Bacillus
        #           stearothermophilus]
        #           Length = 81
        #
        read_and_call(uhandle, consumer.title, start='>')
        while 1:
            line = safe_readline(uhandle)
            if line.lstrip().startswith('Length ='):
                consumer.length(line)
                break
            elif is_blank_line(line):
                # Check to make sure I haven't missed the Length line
                raise SyntaxError, "I missed the Length in an alignment header"
            consumer.title(line)

        # Older versions of BLAST will have a line with some spaces.
        # Version 2.0.14 (maybe 2.0.13?) and above print a true blank line.
        if not attempt_read_and_call(uhandle, consumer.noevent,
                                     start='          '):
            read_and_call(uhandle, consumer.noevent, blank=1)

    def _scan_hsp(self, uhandle, consumer):
        consumer.start_hsp()
        self._scan_hsp_header(uhandle, consumer)
        self._scan_hsp_alignment(uhandle, consumer)
        consumer.end_hsp()
        
    def _scan_hsp_header(self, uhandle, consumer):
        #  Score = 22.7 bits (47), Expect = 2.5
        #  Identities = 10/36 (27%), Positives = 18/36 (49%)
        #  Strand = Plus / Plus
        #  Frame = +3
        #

        read_and_call(uhandle, consumer.score, start=' Score')
        read_and_call(uhandle, consumer.identities, start=' Identities')
        # BLASTN
        attempt_read_and_call(uhandle, consumer.strand, start = ' Strand')
        # BLASTX, TBLASTN, TBLASTX
        attempt_read_and_call(uhandle, consumer.frame, start = ' Frame')
        read_and_call(uhandle, consumer.noevent, blank=1)

    def _scan_hsp_alignment(self, uhandle, consumer):
        # Query: 11 GRGVSACA-------TCDGFFYRNQKVAVIGGGNTAVEEALYLSNIASEVHLIHRRDGF
        #           GRGVS+         TC    Y  + + V GGG+ + EE   L     +   I R+
        # Sbjct: 12 GRGVSSVVRRCIHKPTCKE--YAVKIIDVTGGGSFSAEEVQELREATLKEVDILRKVSG
        # 
        # Query: 64 AEKILIKR 71
        #              I +K 
        # Sbjct: 70 PNIIQLKD 77
        # 

        while 1:
            # Blastn adds an extra line filled with spaces before Query
            attempt_read_and_call(uhandle, consumer.noevent, start='     ')
            read_and_call(uhandle, consumer.query, start='Query')
            read_and_call(uhandle, consumer.align, start='     ')
            read_and_call(uhandle, consumer.sbjct, start='Sbjct')
            read_and_call_while(uhandle, consumer.noevent, blank=1)
            line = safe_peekline(uhandle)
            # Alignment continues if I see a 'Query' or the spaces for Blastn.
            if not (line.startswith('Query') or line.startswith('     ')):
                break
 
    def _scan_masterslave_alignment(self, uhandle, consumer):
        consumer.start_alignment()
        while 1:
            line = safe_readline(uhandle)
            # Check to see whether I'm finished reading the alignment.
            # This is indicated by 1) database section, 2) next psi-blast round
            # patch by chapmanb
            if line.startswith('Searching'):
                uhandle.saveline(line)
                break
            elif line.startswith('  Database'):
                uhandle.saveline(line)
                break
            elif is_blank_line(line):
                consumer.noevent(line)
            else:
                consumer.multalign(line)
        read_and_call_while(uhandle, consumer.noevent, blank=1)
        consumer.end_alignment()

    def _scan_database_report(self, uhandle, consumer):
        #   Database: sdqib40-1.35.seg.fa
        #     Posted date:  Nov 1, 1999  4:25 PM
        #   Number of letters in database: 223,339
        #   Number of sequences in database:  1323
        #   
        # Lambda     K      H
        #    0.322    0.133    0.369 
        #
        # Gapped
        # Lambda     K      H
        #    0.270   0.0470    0.230 
        #

        consumer.start_database_report()
	while 1:
            read_and_call(uhandle, consumer.database, start='  Database')
            # Database can span multiple lines.
            read_and_call_until(uhandle, consumer.database, start='    Posted')
            read_and_call(uhandle, consumer.posted_date, start='    Posted')
            read_and_call(uhandle, consumer.num_letters_in_database,
                       start='  Number of letters')
            read_and_call(uhandle, consumer.num_sequences_in_database,
                       start='  Number of sequences')
            read_and_call(uhandle, consumer.noevent, start='  ')

	    line = safe_readline(uhandle)
	    uhandle.saveline(line)
            if line.find('Lambda') != -1:
		break

	read_and_call(uhandle, consumer.noevent, start='Lambda')
	read_and_call(uhandle, consumer.ka_params)
	read_and_call(uhandle, consumer.noevent, blank=1)

        # not BLASTP
        attempt_read_and_call(uhandle, consumer.gapped, start='Gapped')
        # not TBLASTX
        if attempt_read_and_call(uhandle, consumer.noevent, start='Lambda'):
            read_and_call(uhandle, consumer.ka_params_gap)
            
        # Blast 2.2.4 can sometimes skip the whole parameter section.
        # Thus, I need to be careful not to read past the end of the
        # file.
        try:
            read_and_call_while(uhandle, consumer.noevent, blank=1)
        except SyntaxError, x:
            if str(x) != "Unexpected end of stream.":
                raise
        consumer.end_database_report()

    def _scan_parameters(self, uhandle, consumer):
        # Matrix: BLOSUM62
        # Gap Penalties: Existence: 11, Extension: 1
        # Number of Hits to DB: 50604
        # Number of Sequences: 1323
        # Number of extensions: 1526
        # Number of successful extensions: 6
        # Number of sequences better than 10.0: 5
        # Number of HSP's better than 10.0 without gapping: 5
        # Number of HSP's successfully gapped in prelim test: 0
        # Number of HSP's that attempted gapping in prelim test: 1
        # Number of HSP's gapped (non-prelim): 5
        # length of query: 140
        # length of database: 223,339
        # effective HSP length: 39
        # effective length of query: 101
        # effective length of database: 171,742
        # effective search space: 17345942
        # effective search space used: 17345942
        # T: 11
        # A: 40
        # X1: 16 ( 7.4 bits)
        # X2: 38 (14.8 bits)
        # X3: 64 (24.9 bits)
        # S1: 41 (21.9 bits)
        # S2: 42 (20.8 bits)

        # Blast 2.2.4 can sometimes skip the whole parameter section.
        # Thus, check to make sure that the parameter section really
        # exists.
        if not uhandle.peekline():
            return

        consumer.start_parameters()

        read_and_call(uhandle, consumer.matrix, start='Matrix')
        # not TBLASTX
        attempt_read_and_call(uhandle, consumer.gap_penalties, start='Gap')
        read_and_call(uhandle, consumer.num_hits,
                      start='Number of Hits')
        read_and_call(uhandle, consumer.num_sequences,
                      start='Number of Sequences')
        read_and_call(uhandle, consumer.num_extends,
                      start='Number of extensions')
        read_and_call(uhandle, consumer.num_good_extends,
                      start='Number of successful')

        read_and_call(uhandle, consumer.num_seqs_better_e,
                      start='Number of sequences')

        # not BLASTN, TBLASTX
        if attempt_read_and_call(uhandle, consumer.hsps_no_gap,
                                 start="Number of HSP's better"):
            read_and_call(uhandle, consumer.hsps_prelim_gapped,
                          start="Number of HSP's successfully")
            read_and_call(uhandle, consumer.hsps_prelim_gap_attempted,
                          start="Number of HSP's that")
            read_and_call(uhandle, consumer.hsps_gapped,
                          start="Number of HSP's gapped")
        # not in blastx 2.2.1
        attempt_read_and_call(uhandle, consumer.query_length,
                              start='length of query')
        read_and_call(uhandle, consumer.database_length,
                      start='length of database')

        read_and_call(uhandle, consumer.effective_hsp_length,
                      start='effective HSP')
        # Not in blastx 2.2.1
        attempt_read_and_call(uhandle, consumer.effective_query_length,
                              start='effective length of query')
        read_and_call(uhandle, consumer.effective_database_length,
                      start='effective length of database')
        # Not in blastx 2.2.1, added a ':' to distinguish between
        # this and the 'effective search space used' line
        attempt_read_and_call(uhandle, consumer.effective_search_space,
                              start='effective search space:')
        # Does not appear in BLASTP 2.0.5
        attempt_read_and_call(uhandle, consumer.effective_search_space_used,
                              start='effective search space used')

        # BLASTX, TBLASTN, TBLASTX
        attempt_read_and_call(uhandle, consumer.frameshift, start='frameshift')
        read_and_call(uhandle, consumer.threshold, start='T')
        read_and_call(uhandle, consumer.window_size, start='A')
        read_and_call(uhandle, consumer.dropoff_1st_pass, start='X1')
        read_and_call(uhandle, consumer.gap_x_dropoff, start='X2')
        # not BLASTN, TBLASTX
        attempt_read_and_call(uhandle, consumer.gap_x_dropoff_final,
                              start='X3')
        read_and_call(uhandle, consumer.gap_trigger, start='S1')
        # not in blastx 2.2.1
        # first we make sure we have additional lines to work with, if
        # not then the file is done and we don't have a final S2
        if not is_blank_line(uhandle.peekline(), allow_spaces=1):
            read_and_call(uhandle, consumer.blast_cutoff, start='S2')

        consumer.end_parameters()

class BlastParser(AbstractParser):
    """Parses BLAST data into a Record.Blast object.

    """
    def __init__(self):
        """__init__(self)"""
        self._scanner = _Scanner()
        self._consumer = _BlastConsumer()

    def parse(self, handle):
        """parse(self, handle)"""
        self._scanner.feed(handle, self._consumer)
        return self._consumer.data

class PSIBlastParser(AbstractParser):
    """Parses BLAST data into a Record.PSIBlast object.

    """
    def __init__(self):
        """__init__(self)"""
        self._scanner = _Scanner()
        self._consumer = _PSIBlastConsumer()

    def parse(self, handle):
        """parse(self, handle)"""
        self._scanner.feed(handle, self._consumer)
        return self._consumer.data

class _HeaderConsumer:
    def start_header(self):
        self._header = Record.Header()
        
    def version(self, line):
        c = line.split()
        self._header.application = c[0]
        self._header.version = c[1]
        self._header.date = c[2][1:-1]

    def reference(self, line):
        if line.startswith('Reference: '):
            self._header.reference = line[11:]
        else:
            self._header.reference = self._header.reference + line
            
    def query_info(self, line):
        if line.startswith('Query= '):
            self._header.query = line[7:]
        elif not line.startswith('       '):  # continuation of query_info
            self._header.query = "%s%s" % (self._header.query, line)
        else:
            letters, = _re_search(
                r"([0-9,]+) letters", line,
                "I could not find the number of letters in line\n%s" % line)
            self._header.query_letters = _safe_int(letters)
                
    def database_info(self, line):
        line = line.rstrip()
        if line.startswith('Database: '):
            self._header.database = line[10:]
	elif not line.endswith('total letters'):
            self._header.database = self._header.database + line.strip()
        else:
            sequences, letters =_re_search(
                r"([0-9,]+) sequences; ([0-9,]+) total letters", line,
                "I could not find the sequences and letters in line\n%s" %line)
            self._header.database_sequences = _safe_int(sequences)
            self._header.database_letters = _safe_int(letters)

    def end_header(self):
        # Get rid of the trailing newlines
        self._header.reference = self._header.reference.rstrip()
        self._header.query = self._header.query.rstrip()

class _DescriptionConsumer:
    def start_descriptions(self):
        self._descriptions = []
        self._model_sequences = []
        self._nonmodel_sequences = []
        self._converged = 0
        self._type = None
        self._roundnum = None

        self.__has_n = 0   # Does the description line contain an N value?

    def description_header(self, line):
        if line.startswith('Sequences producing'):
            cols = line.split()
            if cols[-1] == 'N':
                self.__has_n = 1
    
    def description(self, line):
        dh = self._parse(line)
        if self._type == 'model':
            self._model_sequences.append(dh)
        elif self._type == 'nonmodel':
            self._nonmodel_sequences.append(dh)
        else:
            self._descriptions.append(dh)

    def model_sequences(self, line):
        self._type = 'model'

    def nonmodel_sequences(self, line):
        self._type = 'nonmodel'

    def converged(self, line):
        self._converged = 1

    def no_hits(self, line):
        pass

    def round(self, line):
        if not line.startswith('Results from round'):
            raise SyntaxError, "I didn't understand the round line\n%s" % line
        self._roundnum = _safe_int(line[18:].strip())

    def end_descriptions(self):
        pass

    def _parse(self, description_line):
        line = description_line  # for convenience
        dh = Record.Description()
        
        # I need to separate the score and p-value from the title.
        # sp|P21297|FLBT_CAUCR FLBT PROTEIN     [snip]         284  7e-77
        # sp|P21297|FLBT_CAUCR FLBT PROTEIN     [snip]         284  7e-77  1
        # special cases to handle:
        #   - title must be preserved exactly (including whitespaces)
        #   - score could be equal to e-value (not likely, but what if??)
        #   - sometimes there's an "N" score of '1'.
        cols = line.split()
        if len(cols) < 3:
            raise SyntaxError, \
                  "Line does not appear to contain description:\n%s" % line
        if self.__has_n:
            i = line.rfind(cols[-1])        # find start of N
            i = line.rfind(cols[-2], 0, i)  # find start of p-value
            i = line.rfind(cols[-3], 0, i)  # find start of score
        else:
            i = line.rfind(cols[-1])        # find start of p-value
            i = line.rfind(cols[-2], 0, i)  # find start of score
        if self.__has_n:
            dh.title, dh.score, dh.e, dh.num_alignments = \
                      line[:i].rstrip(), cols[-3], cols[-2], cols[-1]
        else:
            dh.title, dh.score, dh.e, dh.num_alignments = \
                      line[:i].rstrip(), cols[-2], cols[-1], 1
        dh.num_alignments = _safe_int(dh.num_alignments)
        dh.score = _safe_int(dh.score)
        dh.e = _safe_float(dh.e)
        return dh

class _AlignmentConsumer:
    # This is a little bit tricky.  An alignment can either be a
    # pairwise alignment or a multiple alignment.  Since it's difficult
    # to know a-priori which one the blast record will contain, I'm going
    # to make one class that can parse both of them.
    def start_alignment(self):
        self._alignment = Record.Alignment()
        self._multiple_alignment = Record.MultipleAlignment()

    def title(self, line):
        self._alignment.title = "%s%s" % (self._alignment.title,
                                           line.lstrip())

    def length(self, line):
        self._alignment.length = line.split()[2]
        self._alignment.length = _safe_int(self._alignment.length)

    def multalign(self, line):
        # Standalone version uses 'QUERY', while WWW version uses blast_tmp.
        if line.startswith('QUERY') or line.startswith('blast_tmp'):
            # If this is the first line of the multiple alignment,
            # then I need to figure out how the line is formatted.
            
            # Format of line is:
            # QUERY 1   acttg...gccagaggtggtttattcagtctccataagagaggggacaaacg 60
            try:
                name, start, seq, end = line.split()
            except ValueError:
                raise SyntaxError, "I do not understand the line\n%s" \
                      % line
            self._start_index = line.index(start, len(name))
            self._seq_index = line.index(seq,
                                         self._start_index+len(start))
            # subtract 1 for the space
            self._name_length = self._start_index - 1
            self._start_length = self._seq_index - self._start_index - 1
            self._seq_length = line.rfind(end) - self._seq_index - 1
            
            #self._seq_index = line.index(seq)
            ## subtract 1 for the space
            #self._seq_length = line.rfind(end) - self._seq_index - 1
            #self._start_index = line.index(start)
            #self._start_length = self._seq_index - self._start_index - 1
            #self._name_length = self._start_index

        # Extract the information from the line
        name = line[:self._name_length]
        name = name.rstrip()
        start = line[self._start_index:self._start_index+self._start_length]
        start = start.rstrip()
        if start:
            start = _safe_int(start)
        end = line[self._seq_index+self._seq_length:].rstrip()
        if end:
            end = _safe_int(end)
        seq = line[self._seq_index:self._seq_index+self._seq_length].rstrip()
        # right pad the sequence with spaces if necessary
        if len(seq) < self._seq_length:
            seq = seq + ' '*(self._seq_length-len(seq))
            
        # I need to make sure the sequence is aligned correctly with the query.
        # First, I will find the length of the query.  Then, if necessary,
        # I will pad my current sequence with spaces so that they will line
        # up correctly.

        # Two possible things can happen:
        # QUERY
        # 504
        #
        # QUERY
        # 403
        #
        # Sequence 504 will need padding at the end.  Since I won't know
        # this until the end of the alignment, this will be handled in
        # end_alignment.
        # Sequence 403 will need padding before being added to the alignment.

        align = self._multiple_alignment.alignment  # for convenience
        align.append((name, start, seq, end))

        # This is old code that tried to line up all the sequences
        # in a multiple alignment by using the sequence title's as
        # identifiers.  The problem with this is that BLAST assigns
        # different HSP's from the same sequence the same id.  Thus,
        # in one alignment block, there may be multiple sequences with
        # the same id.  I'm not sure how to handle this, so I'm not
        # going to.
        
        # # If the sequence is the query, then just add it.
        # if name == 'QUERY':
        #     if len(align) == 0:
        #         align.append((name, start, seq))
        #     else:
        #         aname, astart, aseq = align[0]
        #         if name != aname:
        #             raise SyntaxError, "Query is not the first sequence"
        #         aseq = aseq + seq
        #         align[0] = aname, astart, aseq
        # else:
        #     if len(align) == 0:
        #         raise SyntaxError, "I could not find the query sequence"
        #     qname, qstart, qseq = align[0]
        #     
        #     # Now find my sequence in the multiple alignment.
        #     for i in range(1, len(align)):
        #         aname, astart, aseq = align[i]
        #         if name == aname:
        #             index = i
        #             break
        #     else:
        #         # If I couldn't find it, then add a new one.
        #         align.append((None, None, None))
        #         index = len(align)-1
        #         # Make sure to left-pad it.
        #         aname, astart, aseq = name, start, ' '*(len(qseq)-len(seq))
        # 
        #     if len(qseq) != len(aseq) + len(seq):
        #         # If my sequences are shorter than the query sequence,
        #         # then I will need to pad some spaces to make them line up.
        #         # Since I've already right padded seq, that means aseq
        #         # must be too short.
        #         aseq = aseq + ' '*(len(qseq)-len(aseq)-len(seq))
        #     aseq = aseq + seq
        #     if astart is None:
        #         astart = start
        #     align[index] = aname, astart, aseq

    def end_alignment(self):
        # Remove trailing newlines
        if self._alignment:
            self._alignment.title = self._alignment.title.rstrip()

        # This code is also obsolete.  See note above.
        # If there's a multiple alignment, I will need to make sure
        # all the sequences are aligned.  That is, I may need to
        # right-pad the sequences.
        # if self._multiple_alignment is not None:
        #     align = self._multiple_alignment.alignment
        #     seqlen = None
        #     for i in range(len(align)):
        #         name, start, seq = align[i]
        #         if seqlen is None:
        #             seqlen = len(seq)
        #         else:
        #             if len(seq) < seqlen:
        #                 seq = seq + ' '*(seqlen - len(seq))
        #                 align[i] = name, start, seq
        #             elif len(seq) > seqlen:
        #                 raise SyntaxError, \
        #                       "Sequence %s is longer than the query" % name
        
        # Clean up some variables, if they exist.
        try:
            del self._seq_index
            del self._seq_length
            del self._start_index
            del self._start_length
            del self._name_length
        except AttributeError:
            pass

class _HSPConsumer:
    def start_hsp(self):
        self._hsp = Record.HSP()

    def score(self, line):
        self._hsp.score, self._hsp.bits = _re_search(
            r"Score =\s*([0-9.e+]+) bits \(([0-9]+)\)", line,
            "I could not find the score in line\n%s" % line)
        self._hsp.score = _safe_float(self._hsp.score)
        self._hsp.bits = _safe_float(self._hsp.bits)

        x, y = _re_search(
            r"Expect\(?(\d*)\)? = +([0-9.e-]+)", line,
            "I could not find the expect in line\n%s" % line)
        if x:
            self._hsp.num_alignments = _safe_int(x)
        else:
            self._hsp.num_alignments = 1
        self._hsp.expect = _safe_float(y)

    def identities(self, line):
        x, y = _re_search(
            r"Identities = (\d+)\/(\d+)", line,
            "I could not find the identities in line\n%s" % line)
        self._hsp.identities = _safe_int(x), _safe_int(y)

        if line.find('Positives') != -1:
            x, y = _re_search(
                r"Positives = (\d+)\/(\d+)", line,
                "I could not find the positives in line\n%s" % line)
            self._hsp.positives = _safe_int(x), _safe_int(y)

        if line.find('Gaps') != -1:
            x, y = _re_search(
                r"Gaps = (\d+)\/(\d+)", line,
                "I could not find the gaps in line\n%s" % line)
            self._hsp.gaps = _safe_int(x), _safe_int(y)

        
    def strand(self, line):
        self._hsp.strand = _re_search(
            r"Strand = (\w+) / (\w+)", line,
            "I could not find the strand in line\n%s" % line)

    def frame(self, line):
        # Frame can be in formats:
        # Frame = +1
        # Frame = +2 / +2
        if line.find('/') != -1:
            self._hsp.frame = _re_search(
                r"Frame = ([-+][123]) / ([-+][123])", line,
                "I could not find the frame in line\n%s" % line)
        else:
            self._hsp.frame = _re_search(
                r"Frame = ([-+][123])", line,
                "I could not find the frame in line\n%s" % line)

    # Match a space, if one is available.  Masahir Ishikawa found a
    # case where there's no space between the start and the sequence:
    # Query: 100tt 101
    _query_re = re.compile(r"Query: (\d+)\s*(.+) \d")
    def query(self, line):
        m = self._query_re.search(line)
        if m is None:
            raise SyntaxError, "I could not find the query in line\n%s" % line
        start, seq = m.groups()
        self._hsp.query = self._hsp.query + seq
        if self._hsp.query_start is None:
            self._hsp.query_start = _safe_int(start)

        self._query_start_index = m.start(2)
        self._query_len = len(seq)

    def align(self, line):
        seq = line[self._query_start_index:].rstrip()
        if len(seq) < self._query_len:
            # Make sure the alignment is the same length as the query
            seq = seq + ' ' * (self._query_len-len(seq))
        elif len(seq) < self._query_len:
            raise SyntaxError, "Match is longer than the query in line\n%s" % \
                  line
        self._hsp.match = self._hsp.match + seq

    def sbjct(self, line):
        start, seq = _re_search(
            r"Sbjct: (\d+)\s*(.+) \d", line,
            "I could not find the sbjct in line\n%s" % line)
	#mikep 26/9/00
	#On occasion, there is a blast hit with no subject match
	#so far, it only occurs with 1-line short "matches"
	#I have decided to let these pass as they appear
	if not seq.strip():
            seq = ' ' * self._query_len
        self._hsp.sbjct = self._hsp.sbjct + seq
        if self._hsp.sbjct_start is None:
            self._hsp.sbjct_start = _safe_int(start)

        if len(seq) != self._query_len:
            raise SyntaxError, \
                  "QUERY and SBJCT sequence lengths don't match in line\n%s" \
                  % line

        del self._query_start_index   # clean up unused variables
        del self._query_len

    def end_hsp(self):
        pass

class _DatabaseReportConsumer:

    def start_database_report(self):
        self._dr = Record.DatabaseReport()

    def database(self, line):
        m = re.search(r"Database: (.+)$", line)
        if m:
            self._dr.database_name.append(m.group(1))
        elif self._dr.database_name:
            # This must be a continuation of the previous name.
            self._dr.database_name[-1] = "%s%s" % (self._dr.database_name[-1],
                                                   line.strip())

    def posted_date(self, line):
        self._dr.posted_date.append(_re_search(
            r"Posted date:\s*(.+)$", line,
            "I could not find the posted date in line\n%s" % line))

    def num_letters_in_database(self, line):
        letters, = _get_cols(
            line, (-1,), ncols=6, expected={2:"letters", 4:"database:"})
        self._dr.num_letters_in_database.append(_safe_int(letters))

    def num_sequences_in_database(self, line):
        sequences, = _get_cols(
            line, (-1,), ncols=6, expected={2:"sequences", 4:"database:"})
        self._dr.num_sequences_in_database.append(_safe_int(sequences))

    def ka_params(self, line):
        x = line.split()
        self._dr.ka_params = map(_safe_float, x)

    def gapped(self, line):
        self._dr.gapped = 1

    def ka_params_gap(self, line):
        x = line.split()
        self._dr.ka_params_gap = map(_safe_float, x)

    def end_database_report(self):
        pass
    
class _ParametersConsumer:
    def start_parameters(self):
        self._params = Record.Parameters()

    def matrix(self, line):
        self._params.matrix = line[8:].rstrip()

    def gap_penalties(self, line):
        x = _get_cols(
            line, (3, 5), ncols=6, expected={2:"Existence:", 4:"Extension:"})
        self._params.gap_penalties = map(_safe_float, x)

    def num_hits(self, line):
        if line.find('1st pass') != -1:
            x, = _get_cols(line, (-4,), ncols=11, expected={2:"Hits"})
            self._params.num_hits = _safe_int(x)
        else:
            x, = _get_cols(line, (-1,), ncols=6, expected={2:"Hits"})
            self._params.num_hits = _safe_int(x)

    def num_sequences(self, line):
        if line.find('1st pass') != -1:
            x, = _get_cols(line, (-4,), ncols=9, expected={2:"Sequences:"})
            self._params.num_sequences = _safe_int(x)
        else:
            x, = _get_cols(line, (-1,), ncols=4, expected={2:"Sequences:"})
            self._params.num_sequences = _safe_int(x)

    def num_extends(self, line):
        if line.find('1st pass') != -1:
            x, = _get_cols(line, (-4,), ncols=9, expected={2:"extensions:"})
            self._params.num_extends = _safe_int(x)
        else:
            x, = _get_cols(line, (-1,), ncols=4, expected={2:"extensions:"})
            self._params.num_extends = _safe_int(x)

    def num_good_extends(self, line):
        if line.find('1st pass') != -1:
            x, = _get_cols(line, (-4,), ncols=10, expected={3:"extensions:"})
            self._params.num_good_extends = _safe_int(x)
        else:
            x, = _get_cols(line, (-1,), ncols=5, expected={3:"extensions:"})
            self._params.num_good_extends = _safe_int(x)
        
    def num_seqs_better_e(self, line):
        self._params.num_seqs_better_e, = _get_cols(
            line, (-1,), ncols=7, expected={2:"sequences"})
        self._params.num_seqs_better_e = _safe_int(
            self._params.num_seqs_better_e)

    def hsps_no_gap(self, line):
        self._params.hsps_no_gap, = _get_cols(
            line, (-1,), ncols=9, expected={3:"better", 7:"gapping:"})
        self._params.hsps_no_gap = _safe_int(self._params.hsps_no_gap)

    def hsps_prelim_gapped(self, line):
        self._params.hsps_prelim_gapped, = _get_cols(
            line, (-1,), ncols=9, expected={4:"gapped", 6:"prelim"})
        self._params.hsps_prelim_gapped = _safe_int(
            self._params.hsps_prelim_gapped)

    def hsps_prelim_gapped_attempted(self, line):
        self._params.hsps_prelim_gapped_attempted, = _get_cols(
            line, (-1,), ncols=10, expected={4:"attempted", 7:"prelim"})
        self._params.hsps_prelim_gapped_attempted = _safe_int(
            self._params.hsps_prelim_gapped_attempted)

    def hsps_gapped(self, line):
        self._params.hsps_gapped, = _get_cols(
            line, (-1,), ncols=6, expected={3:"gapped"})
        self._params.hsps_gapped = _safe_int(self._params.hsps_gapped)
        
    def query_length(self, line):
        self._params.query_length, = _get_cols(
            line, (-1,), ncols=4, expected={0:"length", 2:"query:"})
        self._params.query_length = _safe_int(self._params.query_length)
        
    def database_length(self, line):
        self._params.database_length, = _get_cols(
            line, (-1,), ncols=4, expected={0:"length", 2:"database:"})
        self._params.database_length = _safe_int(self._params.database_length)

    def effective_hsp_length(self, line):
        self._params.effective_hsp_length, = _get_cols(
            line, (-1,), ncols=4, expected={1:"HSP", 2:"length:"})
        self._params.effective_hsp_length = _safe_int(
            self._params.effective_hsp_length)

    def effective_query_length(self, line):
        self._params.effective_query_length, = _get_cols(
            line, (-1,), ncols=5, expected={1:"length", 3:"query:"})
        self._params.effective_query_length = _safe_int(
            self._params.effective_query_length)

    def effective_database_length(self, line):
        self._params.effective_database_length, = _get_cols(
            line, (-1,), ncols=5, expected={1:"length", 3:"database:"})
        self._params.effective_database_length = _safe_int(
            self._params.effective_database_length)
        
    def effective_search_space(self, line):
        self._params.effective_search_space, = _get_cols(
            line, (-1,), ncols=4, expected={1:"search"})
        self._params.effective_search_space = _safe_int(
            self._params.effective_search_space)

    def effective_search_space_used(self, line):
        self._params.effective_search_space_used, = _get_cols(
            line, (-1,), ncols=5, expected={1:"search", 3:"used:"})
        self._params.effective_search_space_used = _safe_int(
            self._params.effective_search_space_used)

    def frameshift(self, line):
        self._params.frameshift = _get_cols(
           line, (4, 5), ncols=6, expected={0:"frameshift", 2:"decay"})

    def threshold(self, line):
        self._params.threshold, = _get_cols(
            line, (1,), ncols=2, expected={0:"T:"})
        self._params.threshold = _safe_int(self._params.threshold)
        
    def window_size(self, line):
        self._params.window_size, = _get_cols(
            line, (1,), ncols=2, expected={0:"A:"})
        self._params.window_size = _safe_int(self._params.window_size)
        
    def dropoff_1st_pass(self, line):
        score, bits = _re_search(
            r"X1: (\d+) \(\s*([0-9,.]+) bits\)", line,
            "I could not find the dropoff in line\n%s" % line)
        self._params.dropoff_1st_pass = _safe_int(score), _safe_float(bits)
        
    def gap_x_dropoff(self, line):
        score, bits = _re_search(
            r"X2: (\d+) \(\s*([0-9,.]+) bits\)", line,
            "I could not find the gap dropoff in line\n%s" % line)
        self._params.gap_x_dropoff = _safe_int(score), _safe_float(bits)
        
    def gap_x_dropoff_final(self, line):
        score, bits = _re_search(
            r"X3: (\d+) \(\s*([0-9,.]+) bits\)", line,
            "I could not find the gap dropoff final in line\n%s" % line)
        self._params.gap_x_dropoff_final = _safe_int(score), _safe_float(bits)

    def gap_trigger(self, line):
        score, bits = _re_search(
            r"S1: (\d+) \(\s*([0-9,.]+) bits\)", line,
            "I could not find the gap trigger in line\n%s" % line)
        self._params.gap_trigger = _safe_int(score), _safe_float(bits)
        
    def blast_cutoff(self, line):
        score, bits = _re_search(
            r"S2: (\d+) \(\s*([0-9,.]+) bits\)", line,
            "I could not find the blast cutoff in line\n%s" % line)
        self._params.blast_cutoff = _safe_int(score), _safe_float(bits)
        
    def end_parameters(self):
        pass
    

class _BlastConsumer(AbstractConsumer,
                     _HeaderConsumer,
                     _DescriptionConsumer,
                     _AlignmentConsumer,
                     _HSPConsumer,
                     _DatabaseReportConsumer,
                     _ParametersConsumer
                     ):
    # This Consumer is inherits from many other consumer classes that handle
    # the actual dirty work.  An alternate way to do it is to create objects
    # of those classes and then delegate the parsing tasks to them in a
    # decorator-type pattern.  The disadvantage of that is that the method
    # names will need to be resolved in this classes.  However, using
    # a decorator will retain more control in this class (which may or
    # may not be a bad thing).  In addition, having each sub-consumer as
    # its own object prevents this object's dictionary from being cluttered
    # with members and reduces the chance of member collisions.
    def __init__(self):
        self.data = None

    def round(self, line):
        # Make sure nobody's trying to pass me PSI-BLAST data!
        raise ValueError, \
              "This consumer doesn't handle PSI-BLAST data"
        
    def start_header(self):
        self.data = Record.Blast()
        _HeaderConsumer.start_header(self)

    def end_header(self):
        _HeaderConsumer.end_header(self)
        self.data.__dict__.update(self._header.__dict__)

    def end_descriptions(self):
        self.data.descriptions = self._descriptions

    def end_alignment(self):
        _AlignmentConsumer.end_alignment(self)
        if self._alignment.hsps:
            self.data.alignments.append(self._alignment)
        if self._multiple_alignment.alignment:
            self.data.multiple_alignment = self._multiple_alignment

    def end_hsp(self):
        _HSPConsumer.end_hsp(self)
        try:
            self._alignment.hsps.append(self._hsp)
        except AttributeError:
            raise SyntaxError, "Found an HSP before an alignment"

    def end_database_report(self):
        _DatabaseReportConsumer.end_database_report(self)
        self.data.__dict__.update(self._dr.__dict__)

    def end_parameters(self):
        _ParametersConsumer.end_parameters(self)
        self.data.__dict__.update(self._params.__dict__)

class _PSIBlastConsumer(AbstractConsumer,
                        _HeaderConsumer,
                        _DescriptionConsumer,
                        _AlignmentConsumer,
                        _HSPConsumer,
                        _DatabaseReportConsumer,
                        _ParametersConsumer
                        ):
    def __init__(self):
        self.data = None

    def start_header(self):
        self.data = Record.PSIBlast()
        _HeaderConsumer.start_header(self)

    def end_header(self):
        _HeaderConsumer.end_header(self)
        self.data.__dict__.update(self._header.__dict__)

    def start_descriptions(self):
        self._round = Record.Round()
        self.data.rounds.append(self._round)
        _DescriptionConsumer.start_descriptions(self)

    def end_descriptions(self):
        _DescriptionConsumer.end_descriptions(self)
        self._round.number = self._roundnum
        if self._descriptions:
            self._round.new_seqs.extend(self._descriptions)
        self._round.reused_seqs.extend(self._model_sequences)
        self._round.new_seqs.extend(self._nonmodel_sequences)
        if self._converged:
            self.data.converged = 1

    def end_alignment(self):
        _AlignmentConsumer.end_alignment(self)
        if self._alignment.hsps:
            self._round.alignments.append(self._alignment)
        if self._multiple_alignment:
            self._round.multiple_alignment = self._multiple_alignment

    def end_hsp(self):
        _HSPConsumer.end_hsp(self)
        try:
            self._alignment.hsps.append(self._hsp)
        except AttributeError:
            raise SyntaxError, "Found an HSP before an alignment"

    def end_database_report(self):
        _DatabaseReportConsumer.end_database_report(self)
        self.data.__dict__.update(self._dr.__dict__)

    def end_parameters(self):
        _ParametersConsumer.end_parameters(self)
        self.data.__dict__.update(self._params.__dict__)

class Iterator:
    """Iterates over a file of multiple BLAST results.

    Methods:
    next   Return the next record from the stream, or None.

    """
    def __init__(self, handle, parser=None):
        """__init__(self, handle, parser=None)

        Create a new iterator.  handle is a file-like object.  parser
        is an optional Parser object to change the results into another form.
        If set to None, then the raw contents of the file will be returned.

        """
        try:
            handle.readline
        except AttributeError:
            raise ValueError(
                "I expected a file handle or file-like object, got %s"
                % type(handle))
        self._uhandle = File.UndoHandle(handle)
        self._parser = parser

    def next(self):
        """next(self) -> object

        Return the next Blast record from the file.  If no more records,
        return None.

        """
        lines = []
        while 1:
            line = self._uhandle.readline()
            if not line:
                break
            # If I've reached the next one, then put the line back and stop.
            if lines and (line.startswith('BLAST')
                          or line.startswith('BLAST', 1)):
                self._uhandle.saveline(line)
                break
            lines.append(line)
            
        if not lines:
            return None
            
        data = ''.join(lines)
        if self._parser is not None:
            return self._parser.parse(File.StringHandle(data))
        return data

    def __iter__(self):
        return iter(self.next, None)

def blastall(blastcmd, program, database, infile, **keywds):
    """blastall(blastcmd, program, database, infile, **keywds) ->
    read, error Undohandles
    
    Execute and retrieve data from blastall.  blastcmd is the command
    used to launch the 'blastall' executable.  program is the blast program
    to use, e.g. 'blastp', 'blastn', etc.  database is the path to the database
    to search against.  infile is the path to the file containing
    the sequence to search with.

    You may pass more parameters to **keywds to change the behavior of
    the search.  Otherwise, optional values will be chosen by blastall.
    
        Scoring
    matrix              Matrix to use.
    gap_open            Gap open penalty.
    gap_extend          Gap extension penalty.
    nuc_match           Nucleotide match reward.  (BLASTN)
    nuc_mismatch        Nucleotide mismatch penalty.  (BLASTN)
    query_genetic_code  Genetic code for Query.
    db_genetic_code     Genetic code for database.  (TBLAST[NX])

        Algorithm
    gapped              Whether to do a gapped alignment. T/F (not for TBLASTX)
    expectation         Expectation value cutoff.
    wordsize            Word size.
    strands             Query strands to search against database.([T]BLAST[NX])
    keep_hits           Number of best hits from a region to keep.
    xdrop               Dropoff value (bits) for gapped alignments.
    hit_extend          Threshold for extending hits.
    region_length       Length of region used to judge hits.
    db_length           Effective database length.
    search_length       Effective length of search space.

        Processing
    filter              Filter query sequence?  T/F
    believe_query       Believe the query defline.  T/F
    restrict_gi         Restrict search to these GI's.
    nprocessors         Number of processors to use.

        Formatting
    html                Produce HTML output?  T/F
    descriptions        Number of one-line descriptions.
    alignments          Number of alignments.
    align_view          Alignment view.  Integer 0-6.
    show_gi             Show GI's in deflines?  T/F
    seqalign_file       seqalign file to output.

    """
    att2param = {
        'matrix' : '-M',
        'gap_open' : '-G',
        'gap_extend' : '-E',
        'nuc_match' : '-r',
        'nuc_mismatch' : '-q',
        'query_genetic_code' : '-Q',
        'db_genetic_code' : '-D',

        'gapped' : '-g',
        'expectation' : '-e',
        'wordsize' : '-W',
        'strands' : '-S',
        'keep_hits' : '-K',
        'xdrop' : '-X',
        'hit_extend' : '-f',
        'region_length' : '-L',
        'db_length' : '-z',
        'search_length' : '-Y',
        
        'program' : '-p',
        'database' : '-d',
        'infile' : '-i',
        'filter' : '-F',
        'believe_query' : '-J',
        'restrict_gi' : '-l',
        'nprocessors' : '-a',

        'html' : '-T',
        'descriptions' : '-v',
        'alignments' : '-b',
        'align_view' : '-m',
        'show_gi' : '-I',
        'seqalign_file' : '-O'
        }

    if not os.path.exists(blastcmd):
        raise ValueError, "blastall does not exist at %s" % blastcmd
    
    params = []

    params.extend([att2param['program'], program])
    params.extend([att2param['database'], database])
    params.extend([att2param['infile'], infile])

    for attr in keywds.keys():
        params.extend([att2param[attr], str(keywds[attr])])

    w, r, e = os.popen3(" ".join([blastcmd] + params))
    w.close()
    return File.UndoHandle(r), File.UndoHandle(e)


def blastpgp(blastcmd, database, infile, **keywds):
    """blastpgp(blastcmd, database, infile, **keywds) ->
    read, error Undohandles
    
    Execute and retrieve data from blastpgp.  blastcmd is the command
    used to launch the 'blastpgp' executable.  database is the path to the
    database to search against.  infile is the path to the file containing
    the sequence to search with.

    You may pass more parameters to **keywds to change the behavior of
    the search.  Otherwise, optional values will be chosen by blastpgp.

        Scoring
    matrix              Matrix to use.
    gap_open            Gap open penalty.
    gap_extend          Gap extension penalty.
    window_size         Multiple hits window size.
    npasses             Number of passes.
    passes              Hits/passes.  Integer 0-2.

        Algorithm
    gapped              Whether to do a gapped alignment.  T/F
    expectation         Expectation value cutoff.
    wordsize            Word size.
    keep_hits           Number of beset hits from a region to keep.
    xdrop               Dropoff value (bits) for gapped alignments.
    hit_extend          Threshold for extending hits.
    region_length       Length of region used to judge hits.
    db_length           Effective database length.
    search_length       Effective length of search space.
    nbits_gapping       Number of bits to trigger gapping.
    pseudocounts        Pseudocounts constants for multiple passes.
    xdrop_final         X dropoff for final gapped alignment.
    xdrop_extension     Dropoff for blast extensions.
    model_threshold     E-value threshold to include in multipass model.
    required_start      Start of required region in query.
    required_end        End of required region in query.

        Processing
    XXX should document default values
    program             The blast program to use. (PHI-BLAST)
    filter              Filter query sequence with SEG?  T/F
    believe_query       Believe the query defline?  T/F
    nprocessors         Number of processors to use.

        Formatting
    html                Produce HTML output?  T/F
    descriptions        Number of one-line descriptions.
    alignments          Number of alignments.
    align_view          Alignment view.  Integer 0-6.
    show_gi             Show GI's in deflines?  T/F
    seqalign_file       seqalign file to output.
    align_outfile       Output file for alignment.
    checkpoint_outfile  Output file for PSI-BLAST checkpointing.
    restart_infile      Input file for PSI-BLAST restart.
    hit_infile          Hit file for PHI-BLAST.
    matrix_outfile      Output file for PSI-BLAST matrix in ASCII.
    align_infile        Input alignment file for PSI-BLAST restart.
    
    """
    att2param = {
        'matrix' : '-M',
        'gap_open' : '-G',
        'gap_extend' : '-E',
        'window_size' : '-A',
        'npasses' : '-j',
        'passes' : '-P',

        'gapped' : '-g',
        'expectation' : '-e',
        'wordsize' : '-W',
        'keep_hits' : '-K',
        'xdrop' : '-X',
        'hit_extend' : '-f',
        'region_length' : '-L',
        'db_length' : '-Z',
        'search_length' : '-Y',
        'nbits_gapping' : '-N',
        'pseudocounts' : '-c',
        'xdrop_final' : '-Z',
        'xdrop_extension' : '-y',
        'model_threshold' : '-h',
        'required_start' : '-S',
        'required_end' : '-H',

        'program' : '-p',
        'database' : '-d',
        'infile' : '-i',
        'filter' : '-F',
        'believe_query' : '-J',
        'nprocessors' : '-a',

        'html' : '-T',
        'descriptions' : '-v',
        'alignments' : '-b',
        'align_view' : '-m',
        'show_gi' : '-I',
        'seqalign_file' : '-O',
        'align_outfile' : '-o',
        'checkpoint_outfile' : '-C',
        'restart_infile' : '-R',
        'hit_infile' : '-k',
        'matrix_outfile' : '-Q',
        'align_infile' : '-B'
        }
        
    if not os.path.exists(blastcmd):
        raise ValueError, "blastpgp does not exist at %s" % blastcmd
    
    params = []

    params.extend([att2param['database'], database])
    params.extend([att2param['infile'], infile])

    for attr in keywds.keys():
        params.extend([att2param[attr], str(keywds[attr])])

    w, r, e = os.popen3(" ".join([blastcmd] + params))
    w.close()
    return File.UndoHandle(r), File.UndoHandle(e)


def _re_search(regex, line, error_msg):
    m = re.search(regex, line)
    if not m:
        raise SyntaxError, error_msg
    return m.groups()

def _get_cols(line, cols_to_get, ncols=None, expected={}):
    cols = line.split()

    # Check to make sure number of columns is correct
    if ncols is not None and len(cols) != ncols:
        raise SyntaxError, "I expected %d columns (got %d) in line\n%s" % \
              (ncols, len(cols), line)

    # Check to make sure columns contain the correct data
    for k in expected.keys():
        if cols[k] != expected[k]:
            raise SyntaxError, "I expected '%s' in column %d in line\n%s" % (
                expected[k], k, line)

    # Construct the answer tuple
    results = []
    for c in cols_to_get:
        results.append(cols[c])
    return tuple(results)

def _safe_int(str):
    try:
        return int(str)
    except ValueError:
        # Something went wrong.  Try to clean up the string.
        # Remove all commas from the string
        str = str.replace(',', '')
    try:
        # try again.
        return int(str)
    except ValueError:
        pass
    # If it fails again, maybe it's too long?
    # XXX why converting to float?
    return long(float(str))

def _safe_float(str):
    # Thomas Rosleff Soerensen (rosleff@mpiz-koeln.mpg.de) noted that
    # float('e-172') does not produce an error on his platform.  Thus,
    # we need to check the string for this condition.
    
    # Sometimes BLAST leaves of the '1' in front of an exponent.
    if str and str[0] in ['E', 'e']:
        str = '1' + str
    try:
        return float(str)
    except ValueError:
        # Remove all commas from the string
        str = str.replace(',', '')
    # try again.
    return float(str)

class _BlastErrorConsumer(_BlastConsumer):
    def __init__(self):
        _BlastConsumer.__init__(self)
    def noevent(self, line):
        if line.find("Query must be at least wordsize") != -1:
            raise ShortQueryBlastError, "Query must be at least wordsize"
        # Now pass the line back up to the superclass.
        method = getattr(_BlastConsumer, 'noevent',
                         _BlastConsumer.__getattr__(self, 'noevent'))
        method(line)

class BlastErrorParser(AbstractParser):
    """Attempt to catch and diagnose BLAST errors while parsing.

    This utilizes the BlastParser module but adds an additional layer
    of complexity on top of it by attempting to diagnose SyntaxError's
    that may actually indicate problems during BLAST parsing.

    Current BLAST problems this detects are:
    o LowQualityBlastError - When BLASTing really low quality sequences
    (ie. some GenBank entries which are just short streches of a single
    nucleotide), BLAST will report an error with the sequence and be
    unable to search with this. This will lead to a badly formatted
    BLAST report that the parsers choke on. The parser will convert the
    SyntaxError to a LowQualityBlastError and attempt to provide useful
    information.
    
    """
    def __init__(self, bad_report_handle = None):
        """Initialize a parser that tries to catch BlastErrors.

        Arguments:
        o bad_report_handle - An optional argument specifying a handle
        where bad reports should be sent. This would allow you to save
        all of the bad reports to a file, for instance. If no handle
        is specified, the bad reports will not be saved.
        """
        self._bad_report_handle = bad_report_handle
        
        #self._b_parser = BlastParser()
        self._scanner = _Scanner()
        self._consumer = _BlastErrorConsumer()

    def parse(self, handle):
        """Parse a handle, attempting to diagnose errors.
        """
        results = handle.read()

        try:
            self._scanner.feed(File.StringHandle(results), self._consumer)
        except SyntaxError, msg:
            # if we have a bad_report_file, save the info to it first
            if self._bad_report_handle:
                # send the info to the error handle
                self._bad_report_handle.write(results)

            # now we want to try and diagnose the error
            self._diagnose_error(
                File.StringHandle(results), self._consumer.data)

            # if we got here we can't figure out the problem
            # so we should pass along the syntax error we got
            raise
        return self._consumer.data

    def _diagnose_error(self, handle, data_record):
        """Attempt to diagnose an error in the passed handle.

        Arguments:
        o handle - The handle potentially containing the error
        o data_record - The data record partially created by the consumer.
        """
        line = handle.readline()

        while line:
            # 'Searchingdone' instead of 'Searching......done' seems
            # to indicate a failure to perform the BLAST due to
            # low quality sequence
            if line.startswith('Searchingdone'):
                raise LowQualityBlastError("Blast failure occured on query: ",
                                           data_record.query)
            line = handle.readline()

