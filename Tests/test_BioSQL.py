#!/usr/bin/env python
"""Tests for dealing with storage of biopython objects in a relational db.

Currently these tests require a MySQL db loaded with the GenBank info
in GenBank/cor6_6.gb. This loading can be done with bioperl-db.
"""
# standard library
import sys
import os

# PyUnit
import unittest

# local stuff
import Bio
from Bio.Seq import Seq
from Bio import Alphabet
from Bio import GenBank

from BioSQL import BioSeqDatabase
from BioSQL import BioSeq

# Constants for the MySQL database
DBHOST = 'localhost'
DBUSER = 'chapmanb'
DBPASSWD = ''
TESTDB = 'biosql'
# XXX I need to put these SQL files somewhere in biopython
SQL_FILE = os.path.join(os.pardir, os.pardir, "biosql-schema", "sql",
                        "biosqldb-mysql.sql")

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
    tests = [LoaderTest, ReadTest, SeqInterfaceTest, InDepthLoadTest]
    
    for test in tests:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        test_suite.addTest(cur_suite)

    return test_suite

def load_database(gb_handle):
    """Load a GenBank file into a BioSQL database.
    
    This is useful for running tests against a newly created database.
    """
    # first open a connection to create the database
    server = BioSeqDatabase.open_database(user = DBUSER, passwd = DBPASSWD,
                                          host = DBHOST)
    
    # drop anything in the database
    try:
        sql = r"DROP DATABASE " + TESTDB
        server.adaptor.cursor.execute(sql, ())
    except server.module.OperationalError: # the database doesn't exist
        pass
    
    # create a new database
    sql = r"CREATE DATABASE " + TESTDB
    server.adaptor.execute_one(sql, ())
    
    # now open a connection to load the database
    db_name = "biosql-test"
    server = BioSeqDatabase.open_database(user = DBUSER, passwd = DBPASSWD,
                                          host = DBHOST, db = TESTDB)
    server.load_database_sql(SQL_FILE)
    db = server.new_database(db_name)
    
    # get the GenBank file we are going to put into it
    parser = GenBank.FeatureParser()
    iterator = GenBank.Iterator(gb_handle, parser)
    # finally put it in the database
    db.load(iterator)

class ReadTest(unittest.TestCase):
    """Test reading a database from an already built database.
    """
    loaded_db = 0
    
    def setUp(self):
        """Connect to and load up the database.
        """
        gb_file = os.path.join(os.getcwd(), "GenBank", "cor6_6.gb")
        gb_handle = open(gb_file, "r")
        load_database(gb_handle)
        gb_handle.close()
            
        server = BioSeqDatabase.open_database(user = DBUSER, 
                     passwd = DBPASSWD, host = DBHOST, db = TESTDB)
            
        self.db = server["biosql-test"]

    def t_get_db_items(self):
        """Get a list of all items in the database.
        """
        items = self.db.values()

    def t_lookup_items(self):
        """Test retrieval of items using various ids.
        """
        item = self.db.lookup(accession = "X62281")
        try:
            item = self.db.lookup(accession = "Not real")
            raise Assertionerror("No problem on fake id retrieval")
        except IndexError:
            pass
        item = self.db.lookup(display_id = "ATKIN2")
        try:
            item = self.db.lookup(display_id = "Not real")
            raise AssertionError("No problem on fake id retrieval")
        except IndexError:
            pass
        
        # primary id doesn't work right now
        try:
            item = self.db.lookup(primary_id = "16353")
            raise AssertionError("Need to write tests for primary_id fetch")
        except NotImplementedError:
            pass

class SeqInterfaceTest(unittest.TestCase):
    """Make sure the BioSQL objects implement the expected biopython interfaces
    """
    def setUp(self):
        """Load a database.
        """
        gb_file = os.path.join(os.getcwd(), "GenBank", "cor6_6.gb")
        gb_handle = open(gb_file, "r")
        load_database(gb_handle)
        gb_handle.close()

        server = BioSeqDatabase.open_database(user = DBUSER, passwd = DBPASSWD,
                                              host = DBHOST, db = TESTDB)
        db = server["biosql-test"]
        self.item = db.lookup(accession = "X62281")
    
    def t_seq_record(self):
        """Make sure SeqRecords from BioSQL implement the right interface.
        """
        test_record = self.item
        assert isinstance(test_record.seq, BioSeq.DBSeq), \
          "Seq retrieval is not correct"
        assert test_record.id == "X62281"
        assert test_record.name == "ATKIN2"
        assert test_record.description == "A.thaliana kin2 gene."

        annotations = test_record.annotations
        # XXX should do something with annotations once they are like
        # a dictionary
        for feature in test_record.features:
            assert isinstance(feature, Bio.SeqFeature.SeqFeature)

    def t_seq(self):
        """Make sure Seqs from BioSQL implement the right interface.
        """
        test_seq = self.item.seq
        alphabet = test_seq.alphabet
        assert isinstance(alphabet, Alphabet.Alphabet)

        data = test_seq.data
        assert type(data) == type("")
    
        string_rep = test_seq.tostring()
        assert type(string_rep) == type("")
    
        assert len(test_seq) == 880, len(test_seq)

    def t_seq_slicing(self):
        """Check that slices of sequences are retrieved properly.
        """
        test_seq = self.item.seq
        new_seq = test_seq[:10]
        assert isinstance(new_seq, BioSeq.DBSeq)

        # simple slicing
        assert test_seq[:5].tostring() == 'ATTTG'
        assert test_seq[0:5].tostring() == 'ATTTG'
        assert test_seq[2:3].tostring() == 'T'
        assert test_seq[2:4].tostring() == 'TT'
        assert test_seq[870:].tostring() == 'TTGAATTATA'

        # getting more fancy
        assert test_seq[-1] == 'A'
        assert test_seq[1] == 'T'
        assert test_seq[-10:][5:].tostring() == "TTATA"

    def t_seq_features(self):
        """Check SeqFeatures of a sequence.
        """
        test_features = self.item.features
        cds_feature = test_features[6]
        assert cds_feature.type == "CDS", cds_feature.type
        assert str(cds_feature.location) == "(103..579)", \
            str(cds_feature.location)
        for sub_feature in cds_feature.sub_features:
            assert sub_feature.type == "CDS"
            assert sub_feature.location_operator == "join"
       
        ann = cds_feature.qualifiers["gene"]
        assert ann == ["kin2"]
        multi_ann = cds_feature.qualifiers["db_xref"]
        assert len(multi_ann) == 2
        assert "GI:16354" in multi_ann
        assert "SWISS-PROT:P31169" in multi_ann

class LoaderTest(unittest.TestCase):
    """Load a database from a GenBank file.
    """
    def setUp(self):
        # load the database
        db_name = "biosql-test"
        server = BioSeqDatabase.open_database(user = DBUSER, passwd = DBPASSWD,
                                              host = DBHOST, db = TESTDB)
        
        # remove the database if it already exists
        try:
            server[db_name]
            server.remove_database(db_name)
        except KeyError:
            pass
        
        self.db = server.new_database(db_name)

        # get the GenBank file we are going to put into it
        input_file = os.path.join(os.getcwd(), "GenBank", "cor6_6.gb")
        handle = open(input_file, "r")
        parser = GenBank.FeatureParser()
        self.iterator = GenBank.Iterator(handle, parser)

    def t_load_database(self):
        """Load SeqRecord objects into a BioSQL database.
        """
        self.db.load(self.iterator)

        # do some simple tests to make sure we actually loaded the right
        # thing. More advanced tests in a different module.
        items = self.db.values()
        assert len(items) == 6
        item_names = []
        item_ids = []
        for item in items:
            item_names.append(item.name)
            item_ids.append(item.id)
        item_names.sort()
        item_ids.sort()
        assert item_names == ['AF297471', 'ARU237582', 'ATCOR66M', 
                              'ATKIN2', 'BNAKINI', 'BRRBIF72']
        assert item_ids == ['AF297471', 'AJ237582', 'L31939', 'M81224', 
                            'X55053', 'X62281']

class InDepthLoadTest(unittest.TestCase):
    """Make sure we are loading and retreiving in a semi-lossless fashion.
    """
    def setUp(self):
        gb_file = os.path.join(os.getcwd(), "GenBank", "cor6_6.gb")
        gb_handle = open(gb_file, "r")
        load_database(gb_handle)
        gb_handle.close()

        server = BioSeqDatabase.open_database(user = DBUSER, passwd = DBPASSWD,
                                              host = DBHOST, db = TESTDB)
        self.db = server["biosql-test"]

    def t_record_loading(self):
        """Make sure all records are correctly loaded.
        """
        test_record = self.db.lookup(accession = "X55053")
        assert test_record.name == "ATCOR66M"
        assert test_record.id == "X55053"
        assert test_record.description == "A.thaliana cor6.6 mRNA."
        assert isinstance(test_record.seq.alphabet, Alphabet.RNAAlphabet)
        assert test_record.seq[:10].tostring() == 'AACAAAACAC'

        test_record = self.db.lookup(accession = "X62281")
        assert test_record.name == "ATKIN2"
        assert test_record.id == "X62281"
        assert test_record.description == "A.thaliana kin2 gene."
        assert isinstance(test_record.seq.alphabet, Alphabet.DNAAlphabet)
        assert test_record.seq[:10].tostring() == 'ATTTGGCCTA'

    def t_seq_feature(self):
        """Indepth check that SeqFeatures are transmitted through the db.
        """
        test_record = self.db.lookup(accession = "AJ237582")
        features = test_record.features
        assert len(features) == 7
       
        # test single locations
        test_feature = features[0]
        assert test_feature.type == "source"
        assert str(test_feature.location) == "(0..206)"
        assert len(test_feature.qualifiers.keys()) == 3
        assert test_feature.qualifiers.has_key("organism")
        assert test_feature.qualifiers["organism"] == ["Armoracia rusticana"]

        # test split locations
        test_feature = features[4]
        assert test_feature.type == "CDS", test_feature.type
        assert str(test_feature.location) == "(0..206)"
        assert len(test_feature.sub_features) == 2
        assert str(test_feature.sub_features[0].location) == "(0..48)"
        assert test_feature.sub_features[0].type == "CDS"
        assert test_feature.sub_features[0].location_operator == "join"
        assert str(test_feature.sub_features[1].location) == "(142..206)"
        assert test_feature.sub_features[1].type == "CDS"
        assert test_feature.sub_features[1].location_operator == "join"
        assert len(test_feature.qualifiers.keys()) == 6
        assert test_feature.qualifiers.has_key("product")
        assert test_feature.qualifiers["product"] == ["cold shock protein"]

        # test passing strand information
        # XXX We should be testing complement as well
        test_record = self.db.lookup(accession = "AJ237582")
        test_feature = test_record.features[4] # DNA, no complement
        assert test_feature.strand == 1
        for sub_feature in test_feature.sub_features:
            assert sub_feature.strand == 1

        test_record = self.db.lookup(accession = "X55053")
        test_feature = test_record.features[0] # RNA, so no strand info
        assert test_feature.strand == 0

if __name__ == "__main__":
    sys.exit(run_tests(sys.argv))
