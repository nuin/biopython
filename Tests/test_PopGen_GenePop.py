# Copyright 2007 by Tiago Antao <tiagoantao@gmail.com>.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.


import os
import sys
import unittest
from Bio.PopGen import GenePop

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
    tests = [RecordTest, ParserTest, UtilsTest]
    
    for test in tests:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        test_suite.addTest(cur_suite)

    return test_suite

class RecordTest(unittest.TestCase):
    def t_record_basic(self):
        """Basic test on Record
        """

        r = GenePop.Record()
        assert type(r.marker_len)   == int
        assert type(r.comment_line) == str
        assert type(r.loci_list)    == list
        assert type(r.populations)  == list

class ParserTest(unittest.TestCase):
    def setUp(self):
        files = ["c2line.gen", "c3line.gen", "c2space.gen", "c3space.gen"]
        self.handles = []
        for filename in files:
            self.handles.append(open(os.path.join("PopGen", filename)))

        self.pops_indivs = [
            (3, [4, 3, 5]),
            (3, [4, 3, 5]),
            (3, [4, 3, 5]),
            (3, [4, 3, 5])
        ]
        self.num_loci = [3, 3, 3, 3]
        self.marker_len = [2, 3, 2, 3]

    def tearDown(self):
        for handle in self.handles:
            handle.close()

    def t_record_parser(self):
        """Basic operation of the Record Parser.
        """
        for index in range(len(self.handles)):
            handle = self.handles[index]
            rec = GenePop.parse(handle)
            assert isinstance(rec, GenePop.Record)
            assert len(rec.loci_list) == self.num_loci[index]
            assert rec.marker_len == self.marker_len[index]
            assert len(rec.populations) == self.pops_indivs[index][0]
            for i in range(self.pops_indivs[index][0]):
                assert len(rec.populations[i]) == \
                           self.pops_indivs[index][1][i]

    def t_wrong_file_parser(self):
        """Testing the ability to deal with wrongly formatted files
        """
        f = open(os.path.join("PopGen", "fdist1"))
        try:
            rec = GenePop.parse(f)
            raise Error("Should have raised exception")
        except ValueError:
            pass
        f.close()

class UtilsTest(unittest.TestCase):
    def setUp(self):
        #All files have to have at least 3 loci and 2 pops
        files = ["c2line.gen"]
        self.handles = []
        for filename in files:
            self.handles.append(open(os.path.join("PopGen", filename)))


    def tearDown(self):
        for handle in self.handles:
            handle.close()

    def t_utils(self):
        """Basic operation of GenePop Utils.
        """
        for index in range(len(self.handles)):
            handle = self.handles[index]
            rec = GenePop.parse(handle)
        initial_pops = len(rec.populations)
        initial_loci = len(rec.loci_list)
        first_loci = rec.loci_list[0]
        rec.remove_population(0)
        assert len(rec.populations) == initial_pops - 1
        rec.remove_locus_by_name(first_loci)
        assert len(rec.loci_list) == initial_loci - 1
        assert rec.loci_list[0] != first_loci
        rec.remove_locus_by_position(0)
        assert len(rec.loci_list) == initial_loci - 2

if __name__ == "__main__":
    sys.exit(run_tests(sys.argv))
