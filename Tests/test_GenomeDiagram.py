#!/usr/bin/env python
"""Tests for GenomeDiagram general functionality.
"""

##########
# IMPORTS

# Builtins
import os
import unittest

# Do we have ReportLab?  Raise error if not present.
from Bio import MissingExternalDependencyError
try:
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import cm
except ImportError:
    raise MissingExternalDependencyError(\
            "Install reportlab if you want to use Bio.Graphics.")

# Biopython core
from Bio import SeqIO
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio import SeqUtils

# Bio.Graphics.GenomeDiagram
from Bio.Graphics.GenomeDiagram.FeatureSet import FeatureSet
from Bio.Graphics.GenomeDiagram.GraphSet import GraphSet
from Bio.Graphics.GenomeDiagram.Track import Track
#from Bio.Graphics.GenomeDiagram.Utilities import *
from Bio.Graphics.GenomeDiagram import Diagram
from Bio.Graphics.GenomeDiagram.Colors import ColorTranslator
from Bio.Graphics.GenomeDiagram.Graph import GraphData

###############################################################################
# Utility functions for graph plotting, originally in GenomeDiagram.Utilities #
# See Bug 2705 for discussion on where to put these functions in Biopython... #
###############################################################################
def apply_to_window(sequence, window_size, function, step=None):
    """ apply_to_window(sequence, window_size, function) -> [(int, float),(int, float),...]

        o sequence      Bio.Seq.Seq object

        o window_size   Int describing the length of sequence to consider

        o step          Int describing the step to take between windows
                        (default = window_size/2)

        o function      Method or function that accepts a Bio.Seq.Seq object
                        as its sole argument and returns a single value

        Returns a list of (position, value) tuples for fragments of the passed
        sequence of length window_size (stepped by step), calculated by the
        passed function.  Returned positions are the midpoint of each window.
    """
    seqlen = len(sequence)      # Total length of sequence to be used
    if step is None:    # No step specified, so use half window-width or 1 if larger
        step = max(window_size/2, 1)
    else:               # Use specified step, or 1 if greater
        step = max(step, 1)

    results = []    # Holds (position, value) results

    # Perform the passed function on as many windows as possible, short of
    # overrunning the sequence
    pos = 0
    while pos < seqlen-window_size+1:
        # Obtain sequence fragment
        start, middle, end = pos, (pos+window_size+pos)/2, pos+window_size
        fragment = sequence[start:end]
        # Apply function to the sequence fragment
        value = function(fragment)
        results.append((middle, value)) # Add results to list
        # Advance to next fragment
        pos += step

    # Use the last available window on the sequence, even if it means
    # re-covering old ground
    if pos != seqlen - window_size:
        # Obtain sequence fragment
        pos = seqlen - window_size
        start, middle, end = pos, (pos+window_size+pos)/2, pos+window_size
        fragment = sequence[start:end]
        # Apply function to sequence fragment
        value = function(fragment)
        results.append((middle, value)) # Add results to list
        
    # Check on last sequence
    #print fragment
    #print seq[-100:]
    return results      # Return the list of (position, value) results

def calc_gc_content(sequence):
    """ calc_gc_content(sequence)

        o sequence  A Bio.Seq.Seq object

        Returns the % G+C content in a passed sequence
    """
    d = {}
    for nt in ['A','T','G','C']:
        d[nt] = sequence.count(nt) + sequence.count(nt.lower())
    gc = d.get('G',0) + d.get('C',0)

    if gc == 0: return 0
    #print gc*100.0/(d['A'] +d['T'] + gc)
    return gc*1./(d['A'] +d['T'] + gc)


def calc_at_content(sequence):
    """ calc_at_content(sequence)

        o sequence  A Bio.Seq.Seq object

        Returns the % A+T content in a passed sequence
    """
    seq = sequence.data
    d = {}
    for nt in ['A','T','G','C']:
        d[nt] = sequence.count(nt) + sequence.count(nt.lower())
    at = d.get('A',0) + d.get('T',0)

    if at == 0: return 0
    return at*1./(d['G'] +d['G'] + at)


def calc_gc_skew(sequence):
    """ calc_gc_skew(sequence)

        o sequence   A Bio.Seq.Seq object

        Returns the (G-C)/(G+C) GC skew in a passed sequence
    """
    g = sequence.count('G') + sequence.count('g')
    c = sequence.count('C') + sequence.count('c')
    if g+c == 0 :
        return 0.0 #TODO - return NaN or None here?
    else :
        return (g-c)/float(g+c)


def calc_at_skew(sequence):
    """ calc_at_skew(sequence)

        o sequence   A Bio.Seq.Seq object

        Returns the (A-T)/(A+T) AT skew in a passed sequence
    """
    a = sequence.count('A') + sequence.count('a')
    t = sequence.count('T') + sequence.count('t')
    if a+t == 0 :
        return 0.0 #TODO - return NaN or None here?
    else :
        return (a-t)/float(a+t)

def calc_dinucleotide_counts(sequence):
    """Returns the total count of di-nucleotides repeats (e.g. "AA", "CC").

    This is purely for the sake of generating some non-random sequence
    based score for plotting, with no expected biological meaning.

    NOTE - Only considers same case pairs.
    NOTE - "AA" scores 1, "AAA" scores 2, "AAAA" scores 3 etc.
    """
    total = 0
    for letter in "ACTGUactgu" :
        total += sequence.count(letter+letter)
    return total
    

###############################################################################
# End of utility functions for graph plotting                                 #
###############################################################################

# Tests
class TrackTest(unittest.TestCase):
    # TODO Bring code from Track.py, unsure about what test does
    pass

class ColorsTest(unittest.TestCase):
    def test_color_conversions(self):
        """Test color translations.
        """
        translator = ColorTranslator()
        
        # Does the translate method correctly convert the passed argument?
        assert translator.float1_color((0.5, 0.5, 0.5)) == translator.translate((0.5, 0.5, 0.5)), \
            "Did not correctly translate colour from floating point RGB tuple"
        assert translator.int255_color((1, 75, 240)) == translator.translate((1, 75, 240)), \
            "Did not correctly translate colour from integer RGB tuple"
        assert translator.artemis_color(7) == translator.translate(7), \
            "Did not correctly translate colour from Artemis colour scheme"                        
        assert translator.scheme_color(2) == translator.translate(2), \
            "Did not correctly translate colour from user-defined colour scheme"

            
class GraphTest(unittest.TestCase):
    def setUp(self):
        self.data = [(1, 10), (5, 15), (20, 40)]
        
    def test_slicing(self):
        gd = GraphData()
        gd.set_data(self.data)
        gd.add_point((10, 20))
        
        assert gd[4:16] == [(5, 15), (10, 20)], \
                "Unable to insert and retrieve points correctly"


class DiagramTest(unittest.TestCase):
    """Creating feature sets, graph sets, tracks etc individually for the diagram."""
    def setUp(self) :
        """Test setup, just loads a GenBank file as a SeqRecord."""
        handle = open(os.path.join("GenBank","NC_005816.gb"), 'r')
        self.record = SeqIO.read(handle, "genbank")
        handle.close()

    def test_write_arguments(self) :
        """Check how the write methods respond to output format arguments."""
        gdd = Diagram('Test Diagram')
        filename = os.path.join("Graphics","error.txt")
        #We (now) allow valid formats in any case.
        for output in ["XXX","xxx",None,123,5.9] :
            try :
                gdd.write(filename, output)
                assert False, \
                       "Should have rejected %s as an output format" % output
            except ValueError, e :
                #Good!
                pass
            try :
                gdd.write_to_string(output)
                assert False, \
                       "Should have rejected %s as an output format" % output
            except ValueError, e :
                #Good!
                pass

    def test_partial_diagram(self) :
        """construct and draw PDF for just part of a SeqRecord."""
        genbank_entry = self.record
        start = 6500
        end = 8750
        
        gdd = Diagram('Test Diagram')
        #Add a track of features,
        gdt_features = gdd.new_track(1, greytrack=True,
                                     name="CDS Features",
                                     scale_largetick_interval=1000,
                                     scale_smalltick_interval=100,
                                     scale_format = "SInt",
                                     greytrack_labels=False,
                                     height=0.5)
        #We'll just use one feature set for these features,
        gds_features = gdt_features.new_set()
        for feature in genbank_entry.features:
            if feature.type <> "CDS" :
                #We're going to ignore these.
                continue
            if feature.location.end.position < start :
                #Out of frame (too far left)
                continue
            if feature.location.start.position > end :
                #Out of frame (too far right)
                continue
            #Note that I am using strings for color names, instead
            #of passing in color objects.  This should also work!
            if len(gds_features) % 2 == 0 :
                color = "white" #for testing the automatic black border!
            else :
                color = "red"
            #Checking it can cope with the old UK spelling colour.
            #Also show the labels perpendicular to the track.
            gds_features.add_feature(feature, colour=color,
                                     sigil="ARROW",
                                     label_position = "start",
                                     label_size = 8,
                                     label_angle = 90,
                                     label=True)

        #And draw it...
        gdd.draw(format='linear', orientation='landscape',
                 tracklines=False, pagesize=(10*cm,6*cm), fragments=1,
                 start=start, end=end)
        output_filename = os.path.join('Graphics', 'GD_region_linear.pdf')
        gdd.write(output_filename, 'PDF')

        #Also check the write_to_string method matches,
        #(Note the possible confusion over new lines on Windows)
        assert open(output_filename).read().replace("\r\n","\n") \
               == gdd.write_to_string('PDF').replace("\r\n","\n")

        #Circular with a particular start/end is a bit odd, but should work!
        gdd.draw(format='circular',
                 tracklines=False, pagesize=(10*cm,10*cm),
                 start=start, end=end)
        output_filename = os.path.join('Graphics', 'GD_region_circular.pdf')
        gdd.write(output_filename, 'PDF')

    def test_diagram_via_methods_pdf(self) :
        """Construct and draw PDF using method approach."""
        genbank_entry = self.record
        gdd = Diagram('Test Diagram')

        #Add a track of features,
        gdt_features = gdd.new_track(1, greytrack=True,
                                     name="CDS Features", greytrack_labels=0,
                                     height=0.5)
        #We'll just use one feature set for the genes and misc_features,
        gds_features = gdt_features.new_set()
        for feature in genbank_entry.features:
            if feature.type == "gene" :
                if len(gds_features) % 2 == 0 :
                    color = "blue"
                else :
                    color = "lightblue"
                gds_features.add_feature(feature, color=color,
                                            #label_position = "middle",
                                            #label_position = "end",
                                            label_position = "start",
                                            label_size = 11,
                                            #label_angle = 90,
                                            sigil="ARROW",
                                            label=True)

        #I want to include some strandless features, so for an example
        #will use EcoRI recognition sites etc.
        for site, name, color in [("GAATTC","EcoRI","green"),
                                  ("CCCGGG","SmaI","orange"),
                                  ("AAGCTT","HindIII","red"),
                                  ("GGATCC","BamHI","purple")] :
            index = 0
            while True :
                index  = genbank_entry.seq.find(site, start=index)
                if index == -1 : break
                feature = SeqFeature(FeatureLocation(index, index+6), strand=None)
                gds_features.add_feature(feature, color=color,
                                            #label_position = "middle",
                                            label_size = 10,
                                            label_color=color,
                                            #label_angle = 90,
                                            name=name,
                                            label=True)
                index += len(site)
            del index

        #Now add a graph track...
        gdt_at_gc = gdd.new_track(2, greytrack=True,
                                  name="AT and GC content",
                                  greytrack_labels=True)
        gds_at_gc = gdt_at_gc.new_set(type="graph")

        step = len(genbank_entry)/200
        gds_at_gc.new_graph(apply_to_window(genbank_entry.seq, step, calc_gc_content, step),
                        'GC content', style='line', 
                        color=colors.lightgreen,
                        altcolor=colors.darkseagreen)
        gds_at_gc.new_graph(apply_to_window(genbank_entry.seq, step, calc_at_content, step),
                        'AT content', style='line', 
                        color=colors.orange,
                        altcolor=colors.red)
        
        #Finally draw it in both formats,
        gdd.draw(format='linear', orientation='landscape',
             tracklines=0, pagesize='A4', fragments=3)
        output_filename = os.path.join('Graphics', 'GD_by_meth_linear.pdf')
        gdd.write(output_filename, 'PDF')

        #Change the order and leave an empty space in the center:
        gdd.move_track(1,3)

        gdd.draw(format='circular', tracklines=False,
                 pagesize=(20*cm,20*cm), circular=True)
        output_filename = os.path.join('Graphics', 'GD_by_meth_circular.pdf')
        gdd.write(output_filename, 'PDF')

    def test_diagram_via_object_pdf(self):
        """Construct and draw PDF using object approach."""
        genbank_entry = self.record
        gdd = Diagram('Test Diagram')

        #First add some feature sets:
        gdfs1 = FeatureSet(name='CDS features')
        gdfs2 = FeatureSet(name='gene features')
        gdfs3 = FeatureSet(name='misc_features')
        gdfs4 = FeatureSet(name='repeat regions')

        cds_count = 0
        for feature in genbank_entry.features:
            if feature.type == 'CDS':
                cds_count += 1
                if cds_count % 2 == 0 :
                    gdfs1.add_feature(feature, color=colors.pink)
                else :
                    gdfs1.add_feature(feature, color=colors.red)

            if feature.type == 'gene':
                gdfs2.add_feature(feature)

            if feature.type == 'misc_feature':
                gdfs3.add_feature(feature, color=colors.orange)

            if feature.type == 'repeat_region':
                gdfs4.add_feature(feature, color=colors.purple)


        gdfs1.set_all_features('label', 1)
        gdfs2.set_all_features('label', 1)
        gdfs3.set_all_features('label', 1)
        gdfs4.set_all_features('label', 1)

        gdfs3.set_all_features('hide', 0)
        gdfs4.set_all_features('hide', 0)

        #gdfs1.set_all_features('color', colors.red)
        gdfs2.set_all_features('color', colors.blue)

        gdt1 = Track('CDS features', greytrack=1,
            scale_largetick_interval=1e4,
            scale_smalltick_interval=1e3,
            scale_format = "SInt")
        gdt1.add_set(gdfs1)

        gdt2 = Track('gene features', greytrack=1,
                   scale_largetick_interval=1e4)
        gdt2.add_set(gdfs2)
                
        gdt3 = Track('misc features and repeats', greytrack=1,
                   scale_largetick_interval=1e4)
        gdt3.add_set(gdfs3)
        gdt3.add_set(gdfs4)

        #Now add some graph sets:

        #Use a fairly large step so we can easily tell the difference
        #between the bar and line graphs.
        step = len(genbank_entry)/200
        gdgs1 = GraphSet('GC skew')
        
        graphdata1 = apply_to_window(genbank_entry.seq, step, calc_gc_skew, step)
        gdgs1.new_graph(graphdata1, 'GC Skew', style='bar',
                color=colors.violet,
                altcolor=colors.purple)
        
        gdt4 = Track(\
                'GC Skew (bar)',
                height=1.94, greytrack=1,
                scale_largetick_interval=1e4)
        gdt4.add_set(gdgs1)


        gdgs2 = GraphSet('GC and AT Content')
        gdgs2.new_graph(apply_to_window(genbank_entry.seq, step, calc_gc_content, step),
                        'GC content', style='line', 
                        color=colors.lightgreen,
                        altcolor=colors.darkseagreen)

        gdgs2.new_graph(apply_to_window(genbank_entry.seq, step, calc_at_content, step),
                        'AT content', style='line', 
                        color=colors.orange,
                        altcolor=colors.red)    

        gdt5 = Track(\
                'GC Content(green line), AT Content(red line)',
                height=1.94, greytrack=1,
                scale_largetick_interval=1e4)
        gdt5.add_set(gdgs2)

        gdgs3 = GraphSet('Di-nucleotide count')
        step = len(genbank_entry)/400 #smaller step
        gdgs3.new_graph(apply_to_window(genbank_entry.seq, step, calc_dinucleotide_counts, step),
                        'Di-nucleotide count', style='heat', 
                        color=colors.red, altcolor=colors.orange)
        gdt6 = Track('Di-nucleotide count', height=0.5, greytrack=False, scale=False)
        gdt6.add_set(gdgs3)

        #Add the tracks (from both features and graphs)
        #Leave some white space in the middle
        gdd.add_track(gdt4, 3) # GC skew
        gdd.add_track(gdt5, 4) # GC and AT content
        gdd.add_track(gdt1, 5) # CDS features
        gdd.add_track(gdt2, 6) # Gene features
        gdd.add_track(gdt3, 7) # Misc features and repeat feature
        gdd.add_track(gdt6, 8) # Feature depth

        #Finally draw it in both formats,
        gdd.draw(format='circular', orientation='landscape',
             tracklines=0, pagesize='A0', circular=True)
        output_filename = os.path.join('Graphics', 'GD_by_obj_circular.pdf')
        gdd.write(output_filename, 'PDF')

        gdd.draw(format='linear', orientation='landscape',
             tracklines=0, pagesize='A0', fragments=3)
        output_filename = os.path.join('Graphics', 'GD_by_obj_linear.pdf')
        gdd.write(output_filename, 'PDF')

if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity = 2)
    unittest.main(testRunner=runner)
