#!/usr/bin/env python
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

__version__ = "$Revision: 1.9 $"

import cStringIO
import doctest, unittest
import sys

if sys.modules.has_key('requires_wise'):
    del sys.modules['requires_wise']
import requires_wise

from Bio import MissingExternalDependencyError
if sys.version_info[:2] < (2, 4):
    #On python 2.3, doctest uses slightly different formatting
    #which would be a problem as the expected output won't match.
    #Also, it can't cope with <BLANKLINE> in a doctest string.
    raise MissingExternalDependencyError(\
          "This unit test requires Python 2.4 or later")

from Bio import Wise

class TestWiseDryRun(unittest.TestCase):
    def setUp(self):
        self.old_stdout = sys.stdout
        sys.stdout = cStringIO.StringIO()
        
    def test_dnal(self):
        """Call dnal, and do a trivial check on its output."""
        Wise.align(["dnal"], ("seq1.fna", "seq2.fna"), kbyte=100000, dry_run=True)
        self.assert_(sys.stdout.getvalue().startswith("dnal -kbyte 100000 seq1.fna seq2.fna"))

    def test_psw(self):
        """Call psw, and do a trivial check on its output."""
        Wise.align(["psw"], ("seq1.faa", "seq2.faa"), dry_run=True, kbyte=4)
        self.assert_(sys.stdout.getvalue().startswith("psw -kbyte 4 seq1.faa seq2.faa"))

    def tearDown(self):
        sys.stdout = self.old_stdout

class TestWise(unittest.TestCase):
    def test_align(self):
        """Call dnal with optional arguments, and do a trivial check on the output."""
        temp_file = Wise.align(["dnal"], ("Wise/human_114_g01_exons.fna_01", "Wise/human_114_g02_exons.fna_01"), kbyte=100000, force_type="DNA", quiet=True)
        line = temp_file.readline().rstrip()
        if line == "Score 114" :
            #Wise 2.4.1 includes a score line, even in quiet mode, ignore this
            line = temp_file.readline().rstrip()
        if line == "ENSG00000172135   AGGGAAAGCCCCTAAGCTC--CTGATCTATGCTGCATCCAGTTTGCAAAGTGGGGTCCC" :
            #This is what we expect from wise 2.2.0 (and earlier)
            pass
        elif line == "ENSG00000172135   AGGGAAAGCCCCTAAGCTC--CTGATCTATGCTGCATCCAGTTTGCAAAG-TGGGGTCC" :
            #This is what we expect from wise 2.4.1
            pass
        else :
            #Bad!
            self.assert_(False, line)

def run_tests(argv):
    test_suite = testing_suite()
    runner = unittest.TextTestRunner(sys.stdout, verbosity = 2)
    runner.run(test_suite)

def testing_suite():
    """Generate the suite of tests.
    """
    unittest_suite = unittest.TestSuite()

    test_loader = unittest.TestLoader()
    test_loader.testMethodPrefix = 'test_'
    tests = [TestWiseDryRun, TestWise]
    
    for test in tests:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        unittest_suite.addTest(cur_suite)

    doctest_suite = doctest.DocTestSuite(Wise)

    big_suite = unittest.TestSuite((unittest_suite, doctest_suite))

    return big_suite

if __name__ == "__main__":
    sys.exit(run_tests(sys.argv))
