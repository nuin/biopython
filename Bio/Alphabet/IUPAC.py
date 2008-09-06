# Define the IUPAC Alphabets you know and love
"""Standard nucleotide and protein alphabets defined by IUPAC."""

from Bio import Alphabet
from Bio.Data import IUPACData

##################### Protein

# From the IUPAC definition at:
#   http://www.chem.qmw.ac.uk/iupac/AminoAcid/A2021.html#AA21

# If you use X for selenocysteines, then you'll need a new alphabet.
class ExtendedIUPACProtein(Alphabet.ProteinAlphabet):
    """Extended IUPAC protein single letter alphabet including X etc.

    In addition to the standard 20 single letter protein codes, this includes:
    
    B = "Asx";  Aspartic acid (R) or Asparagine (N)
    X = "Xxx";  Unknown or 'other' amino acid
    Z = "Glx";  Glutamic acid (E) or Glutamine (Q)
    J = "Xle";  Leucine (L) or Isoleucine (I), used in mass-spec (NMR)
    U = "Sec";  Selenocysteine
    O = "Pyl";  Pyrrolysine
    """
    letters = IUPACData.extended_protein_letters

extended_protein = ExtendedIUPACProtein()

class IUPACProtein(ExtendedIUPACProtein):
    """IUPAC protein single letter alphabet of the 20 standard amino acids."""
    letters = IUPACData.protein_letters

protein = IUPACProtein()

##################### DNA

# The next two are the IUPAC definitions, from:
#   http://www.chem.qmw.ac.uk/iubmb/misc/naseq.html
class IUPACAmbiguousDNA(Alphabet.DNAAlphabet):
    letters = IUPACData.ambiguous_dna_letters

ambiguous_dna = IUPACAmbiguousDNA()

class IUPACUnambiguousDNA(IUPACAmbiguousDNA):
    letters = IUPACData.unambiguous_dna_letters

unambiguous_dna = IUPACUnambiguousDNA()


# Also from the URL, but not part of the standard
class ExtendedIUPACDNA(Alphabet.DNAAlphabet):
    letters = IUPACData.extended_dna_letters
    #   B == 5-bromouridine
    #   D == 5,6-dihydrouridine
    #   S == thiouridine
    #   W == wyosine

extended_dna = ExtendedIUPACDNA()

##################### RNA

class IUPACAmbiguousRNA(Alphabet.RNAAlphabet):
    letters = IUPACData.ambiguous_rna_letters

ambiguous_rna = IUPACAmbiguousRNA()

class IUPACUnambiguousRNA(IUPACAmbiguousRNA):
    letters = IUPACData.unambiguous_rna_letters

unambiguous_rna = IUPACUnambiguousRNA()

# are there extended forms?
#class ExtendedIUPACRNA(Alphabet.RNAAlphabet):
#    letters = extended_rna_letters
#    #   B == 5-bromouridine
#    #   D == 5,6-dihydrouridine
#    #   S == thiouridine
#    #   W == wyosine


# We need to load the property resolution information, but we need to
# wait until after the systems have been loaded. (There's a nasty loop
# where, eg, translation objects need an alphabet, which need to be
# assocated with translators.)

from Bio.PropertyManager import default_manager

def _bootstrap(manager, klass, property):
    assert manager is default_manager
    del default_manager.class_resolver[IUPACProtein]
    del default_manager.class_resolver[ExtendedIUPACProtein]
    del default_manager.class_resolver[IUPACAmbiguousDNA]
    del default_manager.class_resolver[IUPACUnambiguousDNA]
    del default_manager.class_resolver[ExtendedIUPACDNA]
    del default_manager.class_resolver[IUPACAmbiguousRNA]
    del default_manager.class_resolver[IUPACUnambiguousRNA]

    from Bio.Encodings import IUPACEncoding

    return manager.resolve_class(klass, property)

default_manager.class_resolver[IUPACProtein] = _bootstrap
default_manager.class_resolver[ExtendedIUPACProtein] = _bootstrap
default_manager.class_resolver[IUPACAmbiguousDNA] = _bootstrap
default_manager.class_resolver[IUPACUnambiguousDNA] = _bootstrap
default_manager.class_resolver[ExtendedIUPACDNA] = _bootstrap
default_manager.class_resolver[IUPACAmbiguousRNA] = _bootstrap
default_manager.class_resolver[IUPACUnambiguousRNA] = _bootstrap
