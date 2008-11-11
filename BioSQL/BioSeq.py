# Copyright 2002 by Andrew Dalke.  All rights reserved.
# Revisions 2007-2008 by Peter Cock.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.
#
# Note that BioSQL (including the database schema and scripts) is
# available and licensed separately.  Please consult www.biosql.org
"""Implementations of Biopython-like Seq objects on top of BioSQL.

This allows retrival of items stored in a BioSQL database using
a biopython-like Seq interface.
"""

from Bio import Alphabet
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqFeature

class DBSeq(Seq):  # This implements the biopython Seq interface
    def __init__(self, primary_id, adaptor, alphabet, start, length):
        """Create a new DBSeq object referring to a BioSQL entry.

        You wouldn't normally create a DBSeq object yourself, this is done
        for you when retreiving a DBSeqRecord object from the database.
        """
        self.primary_id = primary_id
        self.adaptor = adaptor
        self.alphabet = alphabet
        self._length = length
        self.start = start

    def __len__(self):
        return self._length
    
    def __getitem__(self, index) :                 # Seq API requirement
        #Note since Python 2.0, __getslice__ is deprecated
        #and __getitem__ is used instead.
        #See http://docs.python.org/ref/sequence-methods.html
        if isinstance(index, int) :
            #Return a single letter as a string
            i = index
            if i < 0:
                if -i > self._length:
                    raise IndexError(i)
                i = i + self._length
            elif i >= self._length:
                raise IndexError(i)            
            return self.adaptor.get_subseq_as_string(self.primary_id,
                                                     self.start + i,
                                                     self.start + i + 1)
        if not isinstance(index, slice) :
            raise ValueError("Unexpected index type")

        #Return the (sub)sequence as another DBSeq or Seq object
        #(see the Seq obect's __getitem__ method)
        if index.start is None :
            i=0
        else :
            i = index.start
        if i < 0 :
            #Map to equavilent positive index
            if -i > self._length:
                raise IndexError(i)
            i = i + self._length
        elif i >= self._length:
            #Trivial case, should return empty string!
            i = self._length

        if index.stop is None :
            j = self._length
        else :
            j = index.stop
        if j < 0 :
            #Map to equavilent positive index
            if -j > self._length:
                raise IndexError(j)
            j = j + self._length
        elif j >= self._length:
            j = self._length

        if i >= j:
            #Trivial case, empty string.
            return Seq("", self.alphabet)
        elif index.step is None or index.step == 1 :
            #Easy case - can return a DBSeq with the start and end adjusted
            return self.__class__(self.primary_id, self.adaptor, self.alphabet,
                                  self.start + i, j - i)
        else :
            #Tricky.  Will have to create a Seq object because of the stride
            full = self.adaptor.get_subseq_as_string(self.primary_id,
                                                     self.start + i,
                                                     self.start + j)
            return Seq(full[::index.step], self.alphabet)
        
    def tostring(self):
        """Returns the full sequence as a python string.

        Although not formally deprecated, you are now encouraged to use
        str(my_seq) instead of my_seq.tostring()."""
        return self.adaptor.get_subseq_as_string(self.primary_id,
                                                 self.start,
                                                 self.start + self._length)
    def __str__(self):
        """Returns the full sequence as a python string."""
        return self.adaptor.get_subseq_as_string(self.primary_id,
                                                 self.start,
                                                 self.start + self._length)

    data = property(tostring, doc="Sequence as string (DEPRECATED)")

    def toseq(self):
        """Returns the full sequence as a Seq object."""
        #Note - the method name copies that of the MutableSeq object
        return Seq(str(self), self.alphabet)

    def __add__(self, other) :
        #Let the Seq object deal with the alphabet issues etc
        return self.toseq() + other

    def __radd__(self, other) :
        #Let the Seq object deal with the alphabet issues etc
        return other + self.toseq()


def _retrieve_seq(adaptor, primary_id):
    seqs = adaptor.execute_and_fetchall(
        "SELECT alphabet, length(seq) FROM biosequence" \
        " WHERE bioentry_id = %s", (primary_id,))
    if seqs:
        moltype, length = seqs[0]
        moltype = moltype.lower() #might be upper case in database
        #We have no way of knowing if these sequences will use IUPAC
        #alphabets, and we certainly can't assume they are unambiguous!
        if moltype == "dna":
            alphabet = Alphabet.generic_dna
        elif moltype == "rna":
            alphabet = Alphabet.generic_rna
        elif moltype == "protein":
            alphabet = Alphabet.generic_protein
        elif moltype == "unknown":
            #This is used in BioSQL/Loader.py and would happen
            #for any generic or nucleotide alphabets.
            alphabet = Alphabet.single_letter_alphabet
        else:
            raise AssertionError("Unknown moltype: %s" % moltype)
        seq = DBSeq(primary_id, adaptor, alphabet, 0, int(length))
        return seq
    else:
        return None

def _retrieve_dbxrefs(adaptor, primary_id):
    """Retrieve the database cross references for the sequence."""
    _dbxrefs = []
    dbxrefs = adaptor.execute_and_fetchall(
        "SELECT dbname, accession, version" \
        " FROM bioentry_dbxref join dbxref using (dbxref_id)" \
        " WHERE bioentry_id = %s" \
        " ORDER BY rank", (primary_id,))
    for dbname, accession, version in dbxrefs:
        if version and version != "0":
            v = "%s.%s" % (accession, version)
        else:
            v = accession
        _dbxrefs.append("%s:%s" % (dbname, v))
    return _dbxrefs

def _retrieve_features(adaptor, primary_id):
    sql = "SELECT seqfeature_id, type.name, rank" \
          " FROM seqfeature join term type on (type_term_id = type.term_id)" \
          " WHERE bioentry_id = %s" \
          " ORDER BY rank"
    results = adaptor.execute_and_fetchall(sql, (primary_id,))
    seq_feature_list = []
    for seqfeature_id, seqfeature_type, seqfeature_rank in results:
        # Get qualifiers [except for db_xref which is stored separately]
        qvs = adaptor.execute_and_fetchall(
            "SELECT name, value" \
            " FROM seqfeature_qualifier_value  join term using (term_id)" \
            " WHERE seqfeature_id = %s", (seqfeature_id,))
        qualifiers = {}
        for qv_name, qv_value in qvs:
            qualifiers.setdefault(qv_name, []).append(qv_value)
        # Get db_xrefs [special case of qualifiers]
        qvs = adaptor.execute_and_fetchall(
            "SELECT dbxref.dbname, dbxref.accession" \
            " FROM dbxref join seqfeature_dbxref using (dbxref_id)" \
            " WHERE seqfeature_dbxref.seqfeature_id = %s", (seqfeature_id,))
        for qv_name, qv_value in qvs:
            value = "%s:%s" % (qv_name, qv_value)
            qualifiers.setdefault("db_xref", []).append(value)
        # Get locations
        results = adaptor.execute_and_fetchall(
            "SELECT location_id, start_pos, end_pos, strand" \
            " FROM location" \
            " WHERE seqfeature_id = %s" \
            " ORDER BY rank", (seqfeature_id,))
        locations = []
        # convert to Python standard form
        for location_id, start, end, strand in results:
            if start:
                start -= 1
            locations.append( (location_id, start, end, strand) )
        # Get possible remote reference information
        remote_results = adaptor.execute_and_fetchall(
            "SELECT location_id, dbname, accession, version" \
            " FROM location join dbxref using (dbxref_id)" \
            " WHERE seqfeature_id = %s", (seqfeature_id,))
        lookup = {}
        for location_id, dbname, accession, version in remote_results:
            if version and version != "0":
                v = "%s.%s" % (accession, version)
            else:
                v = accession
            lookup[location_id] = (dbname, v)
        
        feature = SeqFeature.SeqFeature(type = seqfeature_type)
        feature.qualifiers = qualifiers
        if len(locations) == 0:
            pass
        elif len(locations) == 1:
            location_id, start, end, strand = locations[0]
            dbname, version = lookup.get(location_id, (None, None))

            feature.location = SeqFeature.FeatureLocation(start, end)
            feature.strand = strand
            feature.ref_db = dbname
            feature.ref = version
        else:
            min_start = locations[0][1]
            max_end = locations[0][2]
            sub_feature_list = []       # (start, sub feature) for sorting
            for location in locations:
                location_id, start, end, strand = location
                dbname, version = lookup.get(location_id, (None, None))
                min_start = min(min_start, start)
                max_end = max(max_end, end)

                subfeature = SeqFeature.SeqFeature()
                subfeature.type = seqfeature_type 
                subfeature.location_operator = "join"
                subfeature.location = SeqFeature.FeatureLocation(start, end)
                subfeature.strand = strand
                subfeature.ref_db = dbname
                subfeature.ref = version
                sub_feature_list.append((start, subfeature))
            sub_feature_list.sort()
            feature.sub_features = [sub_feature[1]
                                    for sub_feature in sub_feature_list]
            feature.location = SeqFeature.FeatureLocation(min_start, max_end)
            feature.strand = feature.sub_features[0].strand

        seq_feature_list.append(
            (seqfeature_rank, feature.location.start.position, feature) )

    # Primary sort is on the feature's rank
    #  .. then on the start position
    #  .. then arbitrary on the feature's id (SeqFeature has no __cmp__)
    seq_feature_list.sort()

    # Get just the SeqFeature
    return [x[2] for x in seq_feature_list]

def _retrieve_annotations(adaptor, primary_id, taxon_id):
    annotations = {}
    annotations.update(_retrieve_qualifier_value(adaptor, primary_id))
    annotations.update(_retrieve_reference(adaptor, primary_id))
    annotations.update(_retrieve_taxon(adaptor, primary_id, taxon_id))
    return annotations

def _retrieve_qualifier_value(adaptor, primary_id):
    qvs = adaptor.execute_and_fetchall(
        "SELECT name, value" \
        " FROM bioentry_qualifier_value JOIN term USING (term_id)" \
        " WHERE bioentry_id = %s" \
        " ORDER BY rank", (primary_id,))
    qualifiers = {}
    for name, value in qvs:
        if name == "keyword": name = "keywords"
        elif name == "date_changed": name = "dates"
        elif name == "secondary_accession": name = "accessions"
        qualifiers.setdefault(name, []).append(value)
    return qualifiers

def _retrieve_reference(adaptor, primary_id):
    # XXX dbxref_qualifier_value
 
    refs = adaptor.execute_and_fetchall(
        "SELECT start_pos, end_pos, " \
        " location, title, authors," \
        " dbname, accession" \
        " FROM bioentry_reference" \
        " JOIN reference USING (reference_id)" \
        " LEFT JOIN dbxref USING (dbxref_id)" \
        " WHERE bioentry_id = %s" \
        " ORDER BY rank", (primary_id,))
    references = []
    for start, end, location, title, authors, dbname, accession in refs:
        reference = SeqFeature.Reference()
        if start: start -= 1
        reference.location = [SeqFeature.FeatureLocation(start, end)]
        reference.authors = authors
        #Don't replace the default "" with None.
        if title : reference.title = title
        reference.journal = location
        if dbname == 'PUBMED':
            reference.pubmed_id = accession
        elif dbname == 'MEDLINE':
            reference.medline_id = accession
        references.append(reference)
    return {'references': references}

def _retrieve_taxon(adaptor, primary_id, taxon_id):
    a = {}
    common_names = adaptor.execute_and_fetch_col0(
        "SELECT name FROM taxon_name WHERE taxon_id = %s" \
        " AND name_class = 'genbank common name'", (taxon_id,))
    if common_names:
        a['source'] = common_names[0]
    scientific_names = adaptor.execute_and_fetch_col0(
        "SELECT name FROM taxon_name WHERE taxon_id = %s" \
        " AND name_class = 'scientific name'", (taxon_id,))
    if scientific_names:
        a['organism'] = scientific_names[0]
    ncbi_taxids = adaptor.execute_and_fetch_col0(
        "SELECT ncbi_taxon_id FROM taxon WHERE taxon_id = %s", (taxon_id,))
    if ncbi_taxids and ncbi_taxids[0] and ncbi_taxids[0] != "0":
        a['ncbi_taxid'] = ncbi_taxids[0]

    #Old code used the left/right values in the taxon table to get the
    #taxonomy lineage in one SQL command.  This was actually very slow,
    #and would fail if the (optional) left/right values were missing.
    #
    #The following code is based on a contribution from Eric Gibert, and
    #relies on the taxon table's parent_taxon_id field only (ignoring the
    #optional left/right values).  This means that it has to make a
    #separate SQL query for each entry in the lineage, but it does still
    #appear to be *much* faster.  See Bug 2494. 
    taxonomy = []
    while taxon_id :
        name, rank, parent_taxon_id = adaptor.execute_one(
        "SELECT taxon_name.name, taxon.node_rank, taxon.parent_taxon_id" \
        " FROM taxon, taxon_name" \
        " WHERE taxon.taxon_id=taxon_name.taxon_id" \
        " AND taxon_name.name_class='scientific name'" \
        " AND taxon.taxon_id = %s", (taxon_id,))
        if taxon_id == parent_taxon_id :
            # If the taxon table has been populated by the BioSQL script
            # load_ncbi_taxonomy.pl this is how top parent nodes are stored.
            # Personally, I would have used a NULL parent_taxon_id here.
            break
        if rank != "no rank" :
            #For consistency with older versions of Biopython, we are only
            #interested in taxonomy entries with a stated rank.
            #Add this to the start of the lineage list.
            taxonomy.insert(0, name)
        taxon_id = parent_taxon_id

    if taxonomy:
        a['taxonomy'] = taxonomy
    return a

class DBSeqRecord(SeqRecord):
    """BioSQL equivalent of the biopython SeqRecord object.
    """

    def __init__(self, adaptor, primary_id):
        self._adaptor = adaptor
        self._primary_id = primary_id

        (self._biodatabase_id, self._taxon_id, self.name,
         accession, version, self._identifier,
         self._division, self.description) = self._adaptor.execute_one(
            "SELECT biodatabase_id, taxon_id, name, accession, version," \
            " identifier, division, description" \
            " FROM bioentry" \
            " WHERE bioentry_id = %s", (self._primary_id,))
        if version and version != "0":
            self.id = "%s.%s" % (accession, version)
        else:
            self.id = accession

    def __get_seq(self):
        if not hasattr(self, "_seq"):
            self._seq = _retrieve_seq(self._adaptor, self._primary_id)
        return self._seq
    def __set_seq(self, seq): self._seq = seq
    def __del_seq(self):      del self._seq
    seq = property(__get_seq, __set_seq, __del_seq, "Seq object")

    def __get_dbxrefs(self):
        if not hasattr(self,"_dbxrefs"):
            self._dbxrefs = _retrieve_dbxrefs(self._adaptor, self._primary_id)
        return self._dbxrefs
    def __set_dbxrefs(self, dbxrefs): self._dbxrefs = dbxrefs
    def __del_dbxrefs(self):      del self._dbxrefs
    dbxrefs = property(__get_dbxrefs, __set_dbxrefs, __del_dbxrefs,
                       "Database cross references")

    def __get_features(self):
        if not hasattr(self, "_features"):
            self._features = _retrieve_features(self._adaptor,
                                                self._primary_id)
        return self._features
    def __set_features(self, features): self._features = features
    def __del_features(self):      del self._features
    features = property(__get_features, __set_features, __del_features,
                        "Features")

    def __get_annotations(self):
        if not hasattr(self, "_annotations"):
            self._annotations = _retrieve_annotations(self._adaptor,
                                                      self._primary_id,
                                                      self._taxon_id)
            if self._identifier:
                self._annotations["gi"] = self._identifier
            if self._division:
                self._annotations["data_file_division"] = self._division
        return self._annotations
    def __set_annotations(self, annotations): self._annotations = annotations
    def __del_annotations(self): del self._annotations
    annotations = property(__get_annotations, __set_annotations,
                           __del_annotations, "Annotations")
