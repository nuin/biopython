#!/usr/bin/env python
"""Tests for Primer-based programs in the Emboss suite.
"""
# standard library
import sys
import os

# PyUnit
import unittest

# local stuff
from Bio.Emboss.Primer import Primer3Parser, PrimerSearchParser
from Bio.Emboss.Primer import PrimerSearchInputRecord

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
    tests = [Primer3ParseTest, PrimersearchParseTest,
             PrimerSearchInputTest]
    
    for test in tests:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        test_suite.addTest(cur_suite)

    return test_suite

class Primer3ParseTest(unittest.TestCase):
    def setUp(self):
        self.test_files = \
          [os.path.join("Emboss", "bac_find.primer3"),
           os.path.join("Emboss", "cds_forward.primer3"),
           os.path.join("Emboss", "cds_reverse.primer3"),
           os.path.join("Emboss", "short.primer3")]

    def t_simple_parse(self):
        """Make sure that we can parse all primer3 files.
        """
        parser = Primer3Parser(debug_level = 0)
        for file in self.test_files:
            h = open(file, "r")
            parser.parse(h)
            h.close()

    def t_indepth_regular_parse(self):
        """Make sure we get the data from normal primer3 files okay.
        """
        regular_file = self.test_files[0]
        parser = Primer3Parser()
        h = open(regular_file, "r")
        primer_info = parser.parse(h)
        h.close()

        assert len(primer_info.primers) == 5, \
          "Wrong number of primers: %s" % len(primer_info.primers)

        assert primer_info.primers[1].forward_seq \
          == "CCGGTTTCTCTGGTTGAAAA"
        assert primer_info.primers[2].reverse_seq == \
          "TCACATTCCCAAATGTAGATCG"
        assert primer_info.primers[0].size == 218
        assert primer_info.primers[3].forward_start == 112
        assert primer_info.primers[3].forward_length == 20
        assert primer_info.primers[3].forward_tm == 59.57
        assert primer_info.primers[3].forward_gc == 45.00

        assert primer_info.primers[4].reverse_start == 304
        assert primer_info.primers[4].reverse_length == 22
        assert primer_info.primers[4].reverse_tm == 59.61
        assert primer_info.primers[4].reverse_gc == 40.91

    def t_in_depth_single_parse(self):
        """Make sure we get info right from a single primer find.
        """
        file = self.test_files[1]
        parser = Primer3Parser()
        h = open(file, "r")
        primer_info = parser.parse(h)
        h.close()

        assert len(primer_info.primers) == 5
        assert primer_info.primers[1].reverse_seq == ""

        assert primer_info.primers[3].forward_seq == "TGTGATTGCTTGAGCTGGAC"
        assert primer_info.primers[3].forward_start == 253

class PrimersearchParseTest(unittest.TestCase):
    def setUp(self):
        self.test_files = \
          [os.path.join("Emboss", "bac_find.psearch")]

    def t_simple_parse(self):
        """Make sure that we can parse all primersearch files.
        """
        parser = PrimerSearchParser(debug_level = 0)
        for file in self.test_files:
            h = open(file, "r")
            parser.parse(h)
            h.close()

    def t_in_depth_normal_parse(self):
        """Make sure the output from a simple primersearch file is correct.
        """
        file = self.test_files[0]
        parser = PrimerSearchParser()
        h = open(file, "r")
        amp_info = parser.parse(h)
        h.close()

        assert len(amp_info.amplifiers.keys()) == 1
        assert "Test" in amp_info.amplifiers.keys()
        assert len(amp_info.amplifiers["Test"]) == 1

        assert amp_info.amplifiers["Test"][0].length == 218
        assert amp_info.amplifiers["Test"][0].hit_info == \
          "AC074298 AC074298 \n" + \
          "\tTelomere associated sequence for Arabidopsis thaliana " + \
          "TEL1N from chromosome I, complete sequence.\n" + \
          "\tCCGGTTTCTCTGGTTGAAAA hits forward strand at 114 with " + \
          "0 mismatches\n" + \
          "\tTCACATTCCCAAATGTAGATCG hits reverse strand at [114] with " + \
          "0 mismatches"

class PrimerSearchInputTest(unittest.TestCase):
    """Test creating input files for primersearch.
    """
    def setUp(self):
        pass

    def t_primer_representation(self):
        """Make sure we can output primer information correctly.
        """
        p_info = PrimerSearchInputRecord()
        p_info.add_primer_set("Test", "GATC", "CATG")
        p_info.add_primer_set("Test2", "AATA", "TTAT")

        output = str(p_info)
        assert output == "Test GATC CATG\n" + \
                         "Test2 AATA TTAT\n"

if __name__ == "__main__":
    sys.exit(run_tests(sys.argv))
