"""
Classes that deal with macromolecular crystal structures. (eg.
PDB and mmCIF parsers, a Structure class, a module to keep 
a local copy of the PDB up-to-date, selective IO of PDB files,
etc.). Author: Thomas Hamelryck.  Additional code by Kristian 
Rother.
"""

# Get a Structure object from a PDB file
from PDBParser import PDBParser

# Get a Structure object from an mmCIF file
from MMCIFParser import MMCIFParser

# Download from the PDB
from PDBList import PDBList 

# Parse PDB header directly
from parse_pdb_header import parse_pdb_header

# Find connected polypeptides in a Structure
from Polypeptide import PPBuilder, CaPPBuilder, is_aa
# This is also useful :-)
from Bio.SCOP.Raf import to_one_letter_code

# IO of PDB files (including flexible selective output)
from PDBIO import PDBIO

# Some methods to eg. get a list of Residues
# from a list of Atoms.
import Selection

# Superimpose atom sets
from Superimposer import Superimposer

# 3D vector class
from Vector import Vector, calc_angle, calc_dihedral, refmat, rotmat, rotaxis

# Alignment module
from StructureAlignment import StructureAlignment

# DSSP handle
from DSSP import DSSP, make_dssp_dict

# Fast atom neighbor search
# Depends on KDTree C++ module
try:
    from NeighborSearch import NeighborSearch
except ImportError:
    pass
