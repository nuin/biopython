# Copyright (C) 2002, Thomas Hamelryck (thamelry@vub.ac.be)
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.  

from Numeric import Float0

from PDBExceptions import PDBConstructionException


class Entity:
	"""
	Basic container object. Structure, Model, Chain and Residue
	are subclasses of Entity. It deals with storage and lookup.
	"""
	def __init__(self, id):
		self.id=id
		self.full_id=None
		self.parent=None
		self.child_list=[]
		self.child_dict={}
	
	# Special methods	

	def __len__(self):
		"Return the number of children."
		return len(self.child_list)

	def __getitem__(self, id):
		"Return the child with given id."
		return self.child_dict[id]

	def __delitem__(self, id):
		"Delete (and destroy) the child with given id."
		child=self[id]
		child.destroy()
		del self.child_dict[id]
		self.child_list=self.child_dict.values()
		self.child_list.sort(self._sort)

	# Private methods

	def _sort(self, e1, e2):
		"""Sort the children in the Entity object.

		This method is implemented by the Entity subclasses. A Chain object
		e.g. sorts Residue objects according to hetero field, sequence
		identifier and insertion code.
		"""
		raise NotImplementedError

	# Public methods	

	def sort(self, sort_function=None):
		"""Sort the children in the Entity object.

		Arguments:
		o sort_function - Optional. A function that compares two Entities. If this
		argument is present, the default sort method is replaced with this function.
		"""
		if sort_function is None:
			self.child_list.sort(self._sort)
		else:
			self.child_list.sort(sort_function)
		for child in self.child_list:
			child.sort()

	def set_parent(self, entity):
		"Set the parent Entity object."
		self.parent=entity

	def detach_parent(self):
		"Detach the parent."
		self.parent=None

	def detach_child(self, id):
		"Remove (but do not destroy) a child."
		child=self.child_dict[id] 
		child.detach_parent()
		del self.child_dict[id]
		self.child_list=self.child_dict.values()
		self.child_list.sort(self._sort)

	def destroy(self):
		"""Destroy the Entity.

		This trashes the Entity object and breaks all circular references
		(eh, yes, I'm still using 1.5).
		"""
		for child in self.child_list:
			child.destroy()
		del self.parent
		del self.child_list
		del self.child_dict
		del self.id

	def add(self, entity):
		"Add a child to the Entity."
		entity_id=entity.get_id()
		assert(not self.has_id(entity_id))
		entity.set_parent(self)
		self.child_list.append(entity)
		#self.child_list.sort(self._sort)
		self.child_dict[entity_id]=entity

	def get_list(self):
		"Return the list of children."
		return self.child_list

	def has_id(self, id):
		"Return 1 if a child with given id exists, otherwise 0."
		return self.child_dict.has_key(id)

	def get_parent(self):
		"Return the parent Entity object."
		return self.parent

	def get_id(self):
		"Return the id."
		return self.id

	def get_full_id(self):
		"""Return the full id.

		The full id is a tuple containing all id's starting from
		the top object (Structure) down to the current object. A full id for
		a Residue object e.g. is something like:

		("1abc", 0, "A", (" ", 10, "A"))

		This corresponds to:

		Structure with id "1abc"
		Model with id 0
		Chain with id "A"
		Residue with id (" ", 10, "A")

		The Residue id indicates that the residue is not a hetero-residue 
		(or a water) beacuse it has a blanc hetero field, that its sequence 
		identifier is 10 and its insertion code "A".
		"""
		if self.full_id==None:
			entity_id=self.get_id()
			l=[entity_id]	
			parent=self.get_parent()
			while parent!=None:
				entity_id=parent.get_id()
				l.append(entity_id)
				parent=parent.get_parent()
			l.reverse()
			self.full_id=tuple(l)
		return self.full_id



class DisorderedEntityWrapper:
	"""
	This class is a simple wrapper class that groups a number of equivalent
	Entities and forwards all method calls to one of them (the currently selected 
	object). DisorderedResidue and DisorderedAtom are subclasses of this class.
	
	E.g.: A DisorderedAtom object contains a number of Atom objects,
	where each Atom object represents a specific position of a disordered
	atom in the structure.
	"""
	def __init__(self, id):
		self.id=id
		self.child_dict={}
		self.selected_child=None
		self.parent=None	

	# Special methods

	def __getattr__(self, method):
		"Forward the method call to the selected child."
		return getattr(self.selected_child, method)

	def __setitem__(self, id, child):
		"Add a child, associated with a certain id."
		self.child_dict[id]=child

	# Public methods	

	def get_id(self):
		"Return the id."
		return self.id

	def disordered_has_id(self, id):
		"Return 1 if there is an object present associated with this id."
		return self.child_dict.has_key(id)

	def destroy(self):
		"Destroy the object (and its children)."
		for child in self.disordered_get_list():
			child.destroy()
		del self.parent
		del self.selected_child
		del self.id
		del self.child_dict

	def detach_parent(self):
		"Detach the parent"
		self.parent=None
		for child in self.disordered_get_list():
			child.detach_parent()

	def set_parent(self, parent):
		"Set the parent for the object and its children."
		self.parent=parent
		for child in self.disordered_get_list():
			child.set_parent(parent)

	def disordered_select(self, id):
		"""Select the object with given id as the currently active object.

		Uncaught method calls are forwarded to the selected child object.
		"""
		self.selected_child=self.child_dict[id]
	
	def disordered_add(self, child):
		"This is implemented by DisorderedAtom and DisorderedResidue."
		raise NotImplementedError

	def is_disordered(self):
		"""
		Return 2, indicating that this Entity is a collection of Entities.
		"""
		return 2

	def disordered_get_id_list(self):
		"Return a list of id's."
		return self.child_dict.keys()
		
	def disordered_get(self, id=None):
		"""Get the child object associated with id.

		If id is None, the currently selected child is returned.
		"""
		if id==None:
			return self.selected_child
		return self.child_dict[id]

	def disordered_get_list(self):
		"Return list of children."
		return self.child_dict.values()

		
