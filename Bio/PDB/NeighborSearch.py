from Bio.KDTree import *
from Selection import unfold_entities, get_unique_parents, entity_levels, uniqueify
from Numeric import array


class NeighborSearch:
	"""
	This module can be used in two ways:

	1. To find all atoms/residues/chains/models/structures within radius 
	of a given query vector. 

	2. To find all atoms/residues/chains/models/structures that are within 
	a fixed radius of each other.

	NeighborSearch makes use of the KD tree C++ module.
	"""
	def __init__(self, atom_list, bucket_size=10):
		"""
		o atom_list - list of atoms. This list is used in the queries.
		It can contain atoms from different structures.
		o bucket_size - bucket size of KD tree. You can play around 
		with this to optimize speed if you feel like it.
		"""
		self.atom_list=atom_list
		# get the coordinates
		coord_list=map(lambda a: a.get_coord(), atom_list) 
		# to Nx3 array of type float
		self.coords=array(coord_list).astype("f")
		assert(bucket_size>1)
		assert(self.coords.shape[1]==3)
		assert(self.coords.typecode()=="f")
		self.kdt=KDTree(3, bucket_size)
		self.kdt.set_coords(self.coords)
	
	# Private

	def _get_unique_parent_pairs(self, pair_list):
		# translate a list of (entity, entity) tuples to 
		# a list of (parent entity, parent entity) tuples,
		# thereby removing duplicate (parent entity, parent entity)
		# pairs.
		# o pair_list - a list of (entity, entity) tuples
		parent_pair_list=[]
		for (e1, e2) in pair_list:
			p1=e1.get_parent()
			p2=e2.get_parent()
			if p1==p2:
				continue
			elif p1<p2:
				parent_pair_list.append((p1, p2))
			else:
				parent_pair_list.append((p2, p1))
		return uniqueify(parent_pair_list)

	# Public

	def search(self, center, radius, level="A"):
		"""Neighbor search.

		Return all atoms/residues/chains/models/structures
		that have at least one atom within radius of center.
		What entitity level is returned (e.g. atoms or residues)
		is determined by level (A=atoms, R=residues, C=chains,
		M=models, S=structures).

		o center - Numpy array 
		o radius - float
		o level - char (A, R, C, M, S)
		"""
		if not level in entity_levels:
			raise Exception, "%s: Unknown level" % level
		self.kdt.search(center, radius)
		indices=self.kdt.get_indices()
		n_atom_list=[]
		atom_list=self.atom_list
		for i in indices:
			a=atom_list[i]
			n_atom_list.append(a)
		if level=="A":
			return n_atom_list
		else:
			return unfold_entities(n_atom_list, level)
			
	def search_all(self, radius, level="A"):
		"""All neighbor search.

		Search all entities that have atoms pairs within
		radius. 

		o radius - float
		o level - char (A, R, C, M, S)
		"""
		if not level in entity_levels:
			raise Exception, "%s: Unknown level" % level
		self.kdt.all_search(radius)
		indices=self.kdt.all_get_indices()
		atom_list=self.atom_list
		atom_pair_list=[]
		for i in indices.shape[0]:
			i1, i2=indices[i]
			a1=atom_list[i1]
			a2=atom_list[i2]
			n_atom_pair_list.append((a1, a2))
		if level=="A":
			# return atoms
			return atom_pair_list
		next_level_pair_list=atom_pair_list
		for l in ["R", "C", "M", "S"]:
			next_level_pair_list=self._get_unique_parent_pairs(next_level_pair_list)
			if level==l:
				return next_level_pair_list	
			

				
		
