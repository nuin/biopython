#!/usr/bin/env python
"""Tests for Genetic Algorithm classes that provide selection capabilities.
"""
# standard library
import sys
import random

# biopython
from Bio.Seq import MutableSeq
from Bio.Alphabet import SingleLetterAlphabet

# local stuff
from Bio.GA.Organism import Organism
from Bio.GA.Selection.Diversity import DiversitySelection
from Bio.GA.Selection.Tournament import TournamentSelection
from Bio.GA.Selection.RouletteWheel import RouletteWheelSelection

# PyUnit
import unittest

def run_tests(argv):
    ALL_TESTS = [DiversitySelectionTest, TournamentSelectionTest,
                 RouletteWheelSelectionTest]
    
    runner = unittest.TextTestRunner(sys.stdout, verbosity = 2)
    test_loader = unittest.TestLoader()
    test_loader.testMethodPrefix = 't_'
    
    for test in ALL_TESTS:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        runner.run(cur_suite)

# --- helper classes and functions

class TestAlphabet(SingleLetterAlphabet):
    """Simple test alphabet.
    """                        
    letters = ["0", "1", "2", "3"]

def test_fitness(genome):
    """Simple class for calculating fitnesses.
    """
    genome_seq = genome.toseq()
    return int(genome_seq.data)

class NoSelection:
    """A simple 'selection' class that just returns the generated population.
    """
    def select(self, population):
        return population

class NoMutation:
    """Simple 'mutation' class that doesn't do anything.
    """
    def mutate(self, org):
        return org.copy()

class NoCrossover:
    """Simple 'crossover' class that doesn't do anything.
    """
    def do_crossover(self, org_1, org_2):
        return org_1.copy(), org_2.copy()

class NoRepair:
    """Simple 'repair' class that doesn't do anything.
    """
    def repair(self, org):
        return org.copy()

def random_genome():
    """Return a random genome string.
    """
    alphabet = TestAlphabet()

    new_genome = ""
    for letter in range(3):
        new_genome += random.choice(alphabet.letters)

    return MutableSeq(new_genome, alphabet)

def random_organism():
    """Generate a random organism.
    """
    genome = random_genome()
    return Organism(genome, test_fitness)

# --- the actual test classes

class AbstractSelectionTest(unittest.TestCase):
    """Some base tests that all selection classes should pass.
    """
    def setUp(self):
        raise NotImplementError("Need to subclass and define a selector.")

    def t_selection(self):
        """Test basic selection on a small population.
        """
        pop = []
        for org_num in range(50):
            pop.append(random_organism())

        new_pop = self.selector.select(pop)

        assert len(new_pop) == len(pop), "Did not maintain population size."

class DiversitySelectionTest(AbstractSelectionTest):
    """Test selection trying to maximize diversity.
    """
    def setUp(self):
        self.selector = DiversitySelection(NoSelection(), random_genome)

    def t_get_new_organism(self):
        """Getting a new organism not in the new population.
        """
        org = random_organism()
        old_pop = [org]
        new_pop = []

        new_org = self.selector._get_new_organism(new_pop, old_pop)
        assert new_org == org, "Got an unexpected organism %s" % new_org

    def t_no_retrive_organism(self):
        """Test not getting an organism already in the new population.
        """
        org = random_organism()
        old_pop = [org]
        new_pop = [org]

        new_org = self.selector._get_new_organism(new_pop, old_pop)
        #assert new_org != org, "Got organism already in the new population."

class TournamentSelectionTest(AbstractSelectionTest):
    """Test selection based on a tournament style scheme.
    """
    def setUp(self):
        self.selector = TournamentSelection(NoMutation(), NoCrossover(),
                                            NoRepair(), 2)

    def t_select_best(self):
        """Ensure selection of the best organism in a population of 2.
        """
        #Create any two non equal organisms
        org_1 = random_organism()
        while True:
            org_2 = random_organism()
            if org_2.fitness != org_1.fitness:
                break
        #Sort them so org_1 is most fit
        if org_2.fitness > org_1.fitness :
            org_1, org_2 = org_2, org_1
        assert org_1.fitness > org_2.fitness
        
        pop = [org_1, org_2]
        new_pop = self.selector.select(pop)
        for org in new_pop:
            assert org == org_1, "Got a worse organism selected."

        #Just to make sure the selector isn't doing something
        #silly with the order, try this with the input reserved:
        pop = [org_2, org_1]
        new_pop = self.selector.select(pop)
        for org in new_pop :
            assert org == org_1, "Got a worse organism selected."

class RouletteWheelSelectionTest(AbstractSelectionTest):
    """Test selection using a roulette wheel selection scheme.
    """
    def setUp(self):
        self.selector = RouletteWheelSelection(NoMutation(), NoCrossover(),
                                               NoRepair())

    def t_select_best(self):
        """Ensure selection of a best organism in a population of 2.
        """
        worst_genome = MutableSeq("0", TestAlphabet())
        worst_org = Organism(worst_genome, test_fitness)

        better_genome = MutableSeq("1", TestAlphabet())
        better_org = Organism(better_genome, test_fitness)

        new_pop = self.selector.select([worst_org, better_org])
        for org in new_pop:
            assert org == better_org, "Worse organism unexpectly selected."
        
if __name__ == "__main__":
   sys.exit(run_tests(sys.argv))
