# Copyright 1999 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

import os
import sys
import unittest
from types import *
from Bio import Fasta

from Bio import SeqRecord
from Bio import Seq
from Bio import Alphabet
from Bio.Alphabet import IUPAC

def run_tests(argv):
    test_suite = testing_suite()
    runner = unittest.TextTestRunner(sys.stdout, verbosity = 2)
    runner.run(test_suite)

def testing_suite():
    """Generate the suite of tests.
    """
    test_suite = unittest.TestSuite()

    test_loader = unittest.TestLoader()
    test_loader.testMethodPrefix = 't_'
    tests = [RecordTest, ParserTest, IteratorTest, DictionaryTest]
    
    for test in tests:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        test_suite.addTest(cur_suite)

    return test_suite

class RecordTest(unittest.TestCase):
    def t_record_basic(self):
        """Basic test on Record
        """
        def pbool(b):
            if b:
                return 1
            return 0

        r = Fasta.Record()
        assert pbool(type(r.title) is StringType)    # StringType
        assert pbool(type(r.sequence) is StringType) # StringType

class ParserTest(unittest.TestCase):
    def setUp(self):
        files = ["f001", "f002"]
        self.handles = []
        for filename in files:
            self.handles.append(open(os.path.join("Fasta", filename)))

        self.lengths = {0 : (96, 79),
                        1 : (100, 633)}

    def tearDown(self):
        for handle in self.handles:
            handle.close()

    def t_record_parser(self):
        """Basic operation of the Record Parser.
        """
        parser = Fasta.RecordParser()
        for index in range(len(self.handles)):
            handle = self.handles[index]
            rec = parser.parse(handle)
            assert isinstance(rec, Fasta.Record)
            assert len(rec.title) == self.lengths[index][0]
            assert len(rec.sequence) == self.lengths[index][1]

    def t_sequence_parser(self):
        """Basic operation of the Sequence Parser.
        """
        parser = Fasta.SequenceParser()
        for index in range(len(self.handles)):
            handle = self.handles[index]
            rec = parser.parse(handle)
            assert isinstance(rec, SeqRecord.SeqRecord)
            assert isinstance(rec.seq, Seq.Seq)
            assert rec.seq.alphabet == Alphabet.generic_alphabet
            assert len(rec.seq) == self.lengths[index][1]
            assert len(rec.description) == self.lengths[index][0]

    def t_sequence_alphabet(self):
        """Setting the alphabet for the Sequence Parser.
        """
        parser = Fasta.SequenceParser(alphabet =
                IUPAC.unambiguous_dna)
        rec = parser.parse(self.handles[0])
        assert rec.seq.alphabet == IUPAC.unambiguous_dna

    def t_sequence_title_convert(self):
        """Test title conversion for the Sequence Parser.
        """
        def test_title2ids(title):
            return "id", "name", "description"
        parser = Fasta.SequenceParser(title2ids = test_title2ids)
        rec = parser.parse(self.handles[0])
        assert rec.id == "id"
        assert rec.name == "name"
        assert rec.description == "description"

class IteratorTest(unittest.TestCase):
    def setUp(self):
        self.test_handle = open(os.path.join('Fasta', 'f002'))

    def tearDown(self):
        self.test_handle.close()

    def t_basic_iterator(self):
        """Ensure the Fasta iterator works returning text.
        """
        i = Fasta.Iterator(self.test_handle)
        rec_info = {0 : ">gi|1348912|gb|G26680|G26680",
                    1 : ">gi|1348917|gb|G26685|G26685",
                    2 : ">gi|1592936|gb|G29385|G29385"}
        for rec_num in range(3):
            rec = i.next()
            lines = rec.split("\n")
            title_part = lines[0].split()
            assert title_part[0] == rec_info[rec_num]

        # make sure we keep getting None when the iterator is done
        assert i.next() is None
        assert i.next() is None

    def t_new_iterator(self):
        """Ensure the Fasta iterator works like a Python 2.2 iterator.
        """
        n = 0
        iterator = Fasta.Iterator(self.test_handle)
        for rec in iter(iterator):
            n += 1
        assert n == 3

    def t_record_iterator(self):
        """Test the iterator with a Record Parser.
        """
        parser = Fasta.RecordParser()
        iterator = Fasta.Iterator(self.test_handle, parser)
        for rec in iter(iterator):
            assert isinstance(rec, Fasta.Record)

    def t_sequence_iterator(self):
        """Test the iterator with a Sequence Parser.
        """
        parser = Fasta.SequenceParser()
        iterator = Fasta.Iterator(self.test_handle, parser)
        for rec in iter(iterator):
            assert isinstance(rec, SeqRecord.SeqRecord)
    
    def t_parsing_comments(self):
        """Parse FASTA files with # style comment lines in them.
        """
        handle = open(os.path.join("Fasta", "f003"))
        iterator = Fasta.Iterator(handle, Fasta.RecordParser())
        num_recs = 0
        for rec in iter(iterator):
            num_recs += 1
        assert num_recs == 2

class DictionaryTest(unittest.TestCase):
    def setUp(self):
        self.filename = os.path.join("Fasta", "f002")
        self.indexname = self.filename + ".idx"

    def tearDown(self):
        try:
            os.remove(self.indexname) # remove files -- old Biopython
        except OSError: # is a directory -- new
            for filename in os.listdir(self.indexname):
                os.remove(os.path.join(self.indexname, filename))
            os.removedirs(self.indexname)

    def t_index_file(self):
        """Test indexing a file and retrieving from it.
        """
        def rec_to_ids(rec):
            """Just return the GI number to index by.
            """
            parts = rec.title.split()
            gi_parts = parts[0].split("|")
            return gi_parts[1]

        Fasta.index_file(self.filename, self.indexname, rec_to_ids)
        gis = ["1348912", "1348917", "1592936"]
        fasta_dict = Fasta.Dictionary(self.indexname, Fasta.RecordParser())
        assert len(fasta_dict) == len(gis), len(fasta_dict)
        dict_keys = fasta_dict.keys()
        dict_keys.sort()
        assert dict_keys == gis
        for gi in gis:
            rec = fasta_dict[gi]
            assert isinstance(rec, Fasta.Record)

if __name__ == "__main__":
    sys.exit(run_tests(sys.argv))
