from Bio import CAPS
import unittest
from Bio.Restriction import *
from Bio.Fasta import FastaAlign
from StringIO import StringIO

import sys
if sys.platform=="win32":
    from tempfile import mktemp
    import os
else :
    from tempfile import NamedTemporaryFile

def createAlignment(alignment):
  """Create a FastaAlignment from an alignment string"""
  alignment = alignment[alignment.find(">"):]

  if sys.platform=="win32":
      # On windows we cannot (re)open the tempfile to read it
      # while it is still open for writing.  And once closed,
      # it gets automatically deleted.
      #
      # This is a crude and potentially "unsafe" work around
      # (as in theory another program could use the same
      # filename in the instant before we open it)
      tmp_name = mktemp()
      tmp = open(tmp_name, "w")
      tmp.write(alignment)
      tmp.close()
  else :
      tmp = NamedTemporaryFile(bufsize=0)
      tmp_name = tmp.name
      tmp.write(alignment)
      #Don't close the file yet...
      tmp.flush()

  #import os
  #assert os.path.isfile(tmp_name), 'Missing temp file "%s"' % tmp_name

  align = FastaAlign.parse_file(tmp.name)

  if sys.platform=="win32":
      #We must remove the temp file ourselves.
      os.remove(tmp.name)
  else :
      #This will delete the temp file
      tmp.close()

  return align

class UnevenAlignment(unittest.TestCase):
  alignment = """
>foo1
aaaaaaaaaaaaaa
>foo2
aaaaaaaa
>foo3
aaaaaaaaaaaaaa
"""

  def setUp(self):
    self.align = createAlignment(self.alignment)

  def test(self):
    self.assertRaises(CAPS.AlignmentHasDifferentLengthsError, CAPS.CAPSMap, self.align)

class FastaAlignmentTest(unittest.TestCase):

  alignment = """"""
  
  enzymes = []
  
  def setUp(self):

    align = createAlignment(self.alignment)
    self.map = CAPS.CAPSMap(align, self.enzymes)

class NonExample(FastaAlignmentTest):

  alignment = """
>Sequence1
aaaaaaaaaaaaaaaaaaaa
>Sequence2
aaaaaaaaaaaaaaaaaaaa
"""
  
  def testNoCAPS(self):
    self.assertEqual(self.map.dcuts, [])

class ResultChecker(FastaAlignmentTest):
  """This class builds an alignment and then checks the results
  
  subclass it and expose fields:

  alignment - Text representation of the alignment to analyze
  enzymes - The enzymes to analyze this with

  
  """

  def check(self):
    self.assertEqual(len(self.map.dcuts), len(self.results))

    for i in range(0,len(self.results)):
      self.assertEqual(self.results[i][0], self.map.dcuts[i].enzyme)
      self.assertEqual(self.results[i][1], self.map.dcuts[i].start)
      self.assertEqual(self.results[i][2], self.map.dcuts[i].cuts_in)
      self.assertEqual(self.results[i][3], self.map.dcuts[i].blocked_in)

class Example1(ResultChecker):

  alignment = """
>0
AAAagaattcTAGATATACCAAACCAGAGAAAACAAATACATAATCGGAGAAATACAGAT
AGAGAGCGAGAGAGATCGACGGCGAAGCTCTTTACCCGGAAACCATTGAAATCGGACGGT
TTAGTGAAAATGGAGGATCAAGTagAtTTTGGGTTCCGTCCGAACGACGAGGAGCTCGTT
GGTCACTATCTCCGTAACAAAATCGAAGGAAACACTAGCCGCGACGTTGAAGTAGCCATC
AGCGAGGTCAACATCTGTAGCTACGATCCTTGGAACTTGCGCTGTAAGTTCCGAATTTTC
>1
AAAagaTttcTAGATATACCAAACCAGAGAAAACAAATACATAATCGGAGAAATACAGAT
AGAGAGCGAGAGAGATCGACGGCGAAGCTCTTTACCCGGAAACCATTGAAATCGGACGGT
TTAGTGAAAATGGAGGATCAAGTagctTTTGGGTTCCGTCCGAACGACGAGGAGCTCGTT
GGTCACTATCTCCGTAACAAAATCGAAGGAAACACTAGCCGCGACGTTGAAGTAGCCATC
AGCGAGGTCAACATCTGTAGCTACGATCCTTGGAACTTGCGCTGTAAGTTCCGAATTTTC
>2
AAAagaTttcTAGATATACCAAACCAGAGAAAACAAATACATAATCGGAGAAATACAGAT
AGAGAGCGAGAGAGATCGACGGCGAAGCTCTTTACCCGGAAACCATTGAAATCGGACGGT
TTAGTGAAAATGGAGGATCAAGTagctTTTGGGTTCCGTCCGAACGACGAGGAGCTCGTT
GGTCACTATCTCCGTAACAAAATCGAAGGAAACACTAGCCGCGACGTTGAAGTAGCCATC
AGCGAGGTCAACATCTGTAGCTACGATCCTTGGAACTTGCGCTGTAAGTTCCGAATTTTC
"""

  enzymes = [EcoRI, AluI]

  results = []
  results.append([EcoRI, 5, [0], [1,2]])
  results.append([AluI, 144, [1,2], [0]])
  
  def test(self):
    self.check()


class TrivialExample(FastaAlignmentTest):

  alignment = """
>1
gaattc
>2
gaactc
"""

  enzymes = [EcoRI]

  def testCAPS(self):
    self.assertEqual(len(self.map.dcuts), 1)
    self.assertEqual(self.map.dcuts[0].enzyme, EcoRI)
    self.assertEqual(self.map.dcuts[0].start, 1)
    self.assertEqual(self.map.dcuts[0].cuts_in, [0])
    self.assertEqual(self.map.dcuts[0].blocked_in, [1])
    
def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(UnevenAlignment("test"))
  suite.addTest(TrivialExample("testCAPS"))
  suite.addTest(Example1("test"))

  return suite


if __name__ == "__main__":
  runner = unittest.TextTestRunner()
  runner.run(test_suite())
