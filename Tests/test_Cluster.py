from Numeric import *

import unittest
import sys



def run_tests(module="Pycluster"):
    if module==[]:
        module = "Bio.Cluster"
    if not module in ("Pycluster", "Bio.Cluster"):
        raise ValueError('Unknown module name: ' + module)
    TestCluster.module = module
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCluster)
    runner = unittest.TextTestRunner(sys.stdout, verbosity = 2)
    runner.run(suite)


class TestCluster(unittest.TestCase):

    def test_median_mean(self):
        if TestCluster.module=='Bio.Cluster':
            from Bio.Cluster import mean, median
        elif TestCluster.module=='Pycluster':
            from Pycluster import mean, median

        data = array([ 34.3, 3, 2 ])
        self.assertAlmostEqual(mean(data), 13.1, 3)
        self.assertAlmostEqual(median(data), 3.0, 3)

        data = [ 5, 10, 15, 20]
        self.assertAlmostEqual(mean(data), 12.5, 3)
        self.assertAlmostEqual(median(data), 12.5, 3)

        data = [ 1, 2, 3, 5, 7, 11, 13, 17]
        self.assertAlmostEqual(mean(data), 7.375, 3)
        self.assertAlmostEqual(median(data), 6.0, 3)

        data = [ 100, 19, 3, 1.5, 1.4, 1, 1, 1]
        self.assertAlmostEqual(mean(data), 15.988, 3)
        self.assertAlmostEqual(median(data), 1.45, 3)
      

    def test_matrix_parse(self):
        if TestCluster.module=='Bio.Cluster':
            from Bio.Cluster import treecluster
        elif TestCluster.module=='Pycluster':
            from Pycluster import treecluster

        # Normal matrix, no errors
        data1 = array([[ 1.1, 1.2 ],
                       [ 1.4, 1.3 ],
                       [ 1.1, 1.5 ],
                       [ 2.0, 1.5 ],
                       [ 1.7, 1.9 ],
                       [ 1.7, 1.9 ],
                       [ 5.7, 5.9 ],
                       [ 5.7, 5.9 ],
                       [ 3.1, 3.3 ],
                       [ 5.4, 5.3 ],
                       [ 5.1, 5.5 ],
                       [ 5.0, 5.5 ],
                       [ 5.1, 5.2 ]])
      
        # Another normal matrix, no errors; written as a list
        data2 =  [[  1.1, 2.2, 3.3, 4.4, 5.5 ], 
                  [  3.1, 3.2, 1.3, 2.4, 1.5 ], 
                  [  4.1, 2.2, 0.3, 5.4, 0.5 ], 
                  [ 12.1, 2.0, 0.0, 5.0, 0.0 ]]
      
        # Ragged matrix
        data3 =  [[ 91.1, 92.2, 93.3, 94.4, 95.5], 
                  [ 93.1, 93.2, 91.3, 92.4 ], 
                  [ 94.1, 92.2, 90.3 ], 
                  [ 12.1, 92.0, 90.0, 95.0, 90.0 ]]
      
        # Matrix with bad cells
        data4 =  [ [ 7.1, 7.2, 7.3, 7.4, 7.5, ],
                   [ 7.1, 7.2, 7.3, 7.4, 'snoopy' ], 
                   [ 7.1, 7.2, 7.3, None, None]] 

        # Matrix with a bad row
        data5 =  [ [ 23.1, 23.2, 23.3, 23.4, 23.5], 
                   None,
                   [ 23.1, 23.0, 23.0, 23.0, 23.0]]

        # Various references that don't point to matrices at all
        data6 = "snoopy"
        data7 = {'a': [[2.3,1.2],[3.3,5.6]]}
        data8 = []
        data9 = [None]
        data10 = [[None]]
      
        try:
            treecluster(data1)
        except:
            self.fail("treecluster failed to accept matrix data1")

        try:
            treecluster(data2)
        except:
            self.fail("treecluster failed to accept matrix data2")

        self.assertRaises(TypeError, lambda : treecluster(data3))
        self.assertRaises(TypeError, lambda : treecluster(data4))
        self.assertRaises(TypeError, lambda : treecluster(data5))
        self.assertRaises(TypeError, lambda : treecluster(data6))
        self.assertRaises(TypeError, lambda : treecluster(data7))
        self.assertRaises(TypeError, lambda : treecluster(data8))
        self.assertRaises(TypeError, lambda : treecluster(data9))
        self.assertRaises(TypeError, lambda : treecluster(data10))

    def test_kcluster(self):
        if TestCluster.module=='Bio.Cluster':
            from Bio.Cluster import kcluster
        elif TestCluster.module=='Pycluster':
            from Pycluster import kcluster

        nclusters = 3
        # First data set
        weight = array([1,1,1,1,1])
        data   = array([[ 1.1, 2.2, 3.3, 4.4, 5.5],
                        [ 3.1, 3.2, 1.3, 2.4, 1.5], 
                        [ 4.1, 2.2, 0.3, 5.4, 0.5], 
                        [12.1, 2.0, 0.0, 5.0, 0.0]]) 
        mask =  array([[ 1, 1, 1, 1, 1], 
                       [ 1, 1, 1, 1, 1], 
                       [ 1, 1, 1, 1, 1], 
                       [ 1, 1, 1, 1, 1]]) 
      
        clusterid, error, nfound = kcluster(data, nclusters=nclusters, mask=mask, weight=weight, transpose=0, npass=100, method='a', dist='e')
        self.assertEqual(len(clusterid), len(data))

        correct = [0,1,1,2]
        mapping = [clusterid[correct.index(i)] for i in range(nclusters)]
        for i in range(len(clusterid)):
            self.assertEqual(clusterid[i], mapping[correct[i]])
      
        # Second data set
        weight = array([1,1])
        data = array([[ 1.1, 1.2 ],
                      [ 1.4, 1.3 ],
                      [ 1.1, 1.5 ],
                      [ 2.0, 1.5 ],
                      [ 1.7, 1.9 ],
                      [ 1.7, 1.9 ],
                      [ 5.7, 5.9 ],
                      [ 5.7, 5.9 ],
                      [ 3.1, 3.3 ],
                      [ 5.4, 5.3 ],
                      [ 5.1, 5.5 ],
                      [ 5.0, 5.5 ],
                      [ 5.1, 5.2 ]])
        mask = array([[ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ]])

        clusterid, error, nfound = kcluster(data, nclusters=3, mask=mask, weight=weight, transpose=0, npass=100, method='a', dist='e')
        self.assertEqual(len(clusterid), len(data))

        correct = [0, 0, 0, 0, 0, 0, 1, 1, 2, 1, 1, 1, 1]
        mapping = [clusterid[correct.index(i)] for i in range(nclusters)]
        for i in range(len(clusterid)):
            self.assertEqual(clusterid[i], mapping[correct[i]])

    def test_clusterdistance(self):
        if TestCluster.module=='Bio.Cluster':
            from Bio.Cluster import clusterdistance
        elif TestCluster.module=='Pycluster':
            from Pycluster import clusterdistance

        # First data set
        weight = array([ 1,1,1,1,1 ])
        data   = array([[  1.1, 2.2, 3.3, 4.4, 5.5, ], 
                        [  3.1, 3.2, 1.3, 2.4, 1.5, ], 
                        [  4.1, 2.2, 0.3, 5.4, 0.5, ], 
                        [ 12.1, 2.0, 0.0, 5.0, 0.0, ]])
        mask   = array([[ 1, 1, 1, 1, 1], 
                        [ 1, 1, 1, 1, 1], 
                        [ 1, 1, 1, 1, 1], 
                        [ 1, 1, 1, 1, 1]])

        # Cluster assignments
        c1 = [0]
        c2 = [1,2]
        c3 = [3]

        distance = clusterdistance(data, mask=mask, weight=weight, index1=c1, index2=c2, dist='e', method='a', transpose=0);
        self.assertAlmostEqual(distance, 6.650, 3)
        distance = clusterdistance(data, mask=mask, weight=weight, index1=c1, index2=c3, dist='e', method='a', transpose=0);
        self.assertAlmostEqual(distance, 32.508, 3)
        distance = clusterdistance(data, mask=mask, weight=weight, index1=c2, index2=c3, dist='e', method='a', transpose=0);
        self.assertAlmostEqual(distance, 15.118, 3)

        # Second data set
        weight =  array([ 1,1 ])
        data   =  array([[ 1.1, 1.2 ],
                         [ 1.4, 1.3 ],
                         [ 1.1, 1.5 ],
                         [ 2.0, 1.5 ],
                         [ 1.7, 1.9 ],
                         [ 1.7, 1.9 ],
                         [ 5.7, 5.9 ],
                         [ 5.7, 5.9 ],
                         [ 3.1, 3.3 ],
                         [ 5.4, 5.3 ],
                         [ 5.1, 5.5 ],
                         [ 5.0, 5.5 ],
                         [ 5.1, 5.2 ]])
        mask = array([[ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ]])

        # Cluster assignments
        c1 = [ 0, 1, 2, 3 ]
        c2 = [ 4, 5, 6, 7 ]
        c3 = [ 8 ]

        distance = clusterdistance(data, mask=mask, weight=weight, index1=c1, index2=c2, dist='e', method='a', transpose=0);
        self.assertAlmostEqual(distance, 5.833, 3)
        distance = clusterdistance(data, mask=mask, weight=weight, index1=c1, index2=c3, dist='e', method='a', transpose=0);
        self.assertAlmostEqual(distance, 3.298, 3)
        distance = clusterdistance(data, mask=mask, weight=weight, index1=c2, index2=c3, dist='e', method='a', transpose=0);
        self.assertAlmostEqual(distance, 0.360, 3)


    def test_treecluster(self):
        if TestCluster.module=='Bio.Cluster':
            from Bio.Cluster import treecluster
        elif TestCluster.module=='Pycluster':
            from Pycluster import treecluster

        # First data set
        weight1 =  [ 1,1,1,1,1 ]
        data1   =  array([[  1.1, 2.2, 3.3, 4.4, 5.5], 
                          [  3.1, 3.2, 1.3, 2.4, 1.5], 
                          [  4.1, 2.2, 0.3, 5.4, 0.5], 
                          [ 12.1, 2.0, 0.0, 5.0, 0.0]])
        mask1 = array([[ 1, 1, 1, 1, 1], 
                       [ 1, 1, 1, 1, 1], 
                       [ 1, 1, 1, 1, 1], 
                       [ 1, 1, 1, 1, 1]])
      
        # test first data set
        # Pairwise average-linkage clustering"
        tree = treecluster(data=data1, mask=mask1, weight=weight1, transpose=0, method='a', dist='e')
        self.assertEqual(len(tree), len(data1)-1)
        self.assertEqual(tree[0].left, 2)
        self.assertEqual(tree[0].right, 1)
        self.assertAlmostEqual(tree[0].distance, 2.600, 3)
        self.assertEqual(tree[1].left, -1)
        self.assertEqual(tree[1].right, 0)
        self.assertAlmostEqual(tree[1].distance, 7.300, 3)
        self.assertEqual(tree[2].left, 3)
        self.assertEqual(tree[2].right, -2)
        self.assertAlmostEqual(tree[2].distance, 21.348, 3)

        # Pairwise single-linkage clustering
        tree = treecluster(data=data1, mask=mask1, weight=weight1, transpose=0, method='s', dist='e')
        self.assertEqual(len(tree), len(data1)-1)
        self.assertEqual(tree[0].left, 1)
        self.assertEqual(tree[0].right, 2)
        self.assertAlmostEqual(tree[0].distance, 2.600, 3)
        self.assertEqual(tree[1].left, 0)
        self.assertEqual(tree[1].right, -1)
        self.assertAlmostEqual(tree[1].distance, 5.800, 3)
        self.assertEqual(tree[2].left, -2)
        self.assertEqual(tree[2].right, 3)
        self.assertAlmostEqual(tree[2].distance, 12.908, 3)

        # Pairwise centroid-linkage clustering
        tree = treecluster(data=data1, mask=mask1, weight=weight1, transpose=0, method='c', dist='e')
        self.assertEqual(len(tree), len(data1)-1)
        self.assertEqual(tree[0].left, 1)
        self.assertEqual(tree[0].right, 2)
        self.assertAlmostEqual(tree[0].distance, 2.600, 3)
        self.assertEqual(tree[1].left, 0)
        self.assertEqual(tree[1].right, -1)
        self.assertAlmostEqual(tree[1].distance, 6.650, 3)
        self.assertEqual(tree[2].left, -2)
        self.assertEqual(tree[2].right, 3)
        self.assertAlmostEqual(tree[2].distance, 19.437, 3)

        # Pairwise maximum-linkage clustering
        tree = treecluster(data=data1, mask=mask1, weight=weight1, transpose=0, method='m', dist='e')
        self.assertEqual(len(tree), len(data1)-1)
        self.assertEqual(tree[0].left, 2)
        self.assertEqual(tree[0].right, 1)
        self.assertAlmostEqual(tree[0].distance, 2.600, 3)
        self.assertEqual(tree[1].left, -1)
        self.assertEqual(tree[1].right, 0)
        self.assertAlmostEqual(tree[1].distance, 8.800, 3)
        self.assertEqual(tree[2].left, 3)
        self.assertEqual(tree[2].right, -2)
        self.assertAlmostEqual(tree[2].distance, 32.508, 3)
      
        # Second data set
        weight2 =  [ 1,1 ]
        data2 = array([[ 0.8223, 0.9295 ],
                       [ 1.4365, 1.3223 ],
                       [ 1.1623, 1.5364 ],
                       [ 2.1826, 1.1934 ],
                       [ 1.7763, 1.9352 ],
                       [ 1.7215, 1.9912 ],
                       [ 2.1812, 5.9935 ],
                       [ 5.3290, 5.9452 ],
                       [ 3.1491, 3.3454 ],
                       [ 5.1923, 5.3156 ],
                       [ 4.7735, 5.4012 ],
                       [ 5.1297, 5.5645 ],
                       [ 5.3934, 5.1823 ]])
        mask2 = array([[ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ],
                       [ 1, 1 ]])
      
        # Test second data set
        # Pairwise average-linkage clustering
        tree = treecluster(data=data2, mask=mask2, weight=weight2, transpose=0, method='a', dist='e')
        self.assertEqual(len(tree), len(data2)-1)
        self.assertEqual(tree[0].left, 5)
        self.assertEqual(tree[0].right, 4)
        self.assertAlmostEqual(tree[0].distance, 0.003, 3)
        self.assertEqual(tree[1].left, 9)
        self.assertEqual(tree[1].right, 12)
        self.assertAlmostEqual(tree[1].distance, 0.029, 3)
        self.assertEqual(tree[2].left, 2)
        self.assertEqual(tree[2].right, 1)
        self.assertAlmostEqual(tree[2].distance, 0.061, 3)
        self.assertEqual(tree[3].left, 11)
        self.assertEqual(tree[3].right, -2)
        self.assertAlmostEqual(tree[3].distance, 0.070, 3)
        self.assertEqual(tree[4].left, -4)
        self.assertEqual(tree[4].right, 10)
        self.assertAlmostEqual(tree[4].distance, 0.128, 3)
        self.assertEqual(tree[5].left, 7)
        self.assertEqual(tree[5].right, -5)
        self.assertAlmostEqual(tree[5].distance, 0.224, 3)
        self.assertEqual(tree[6].left, -3)
        self.assertEqual(tree[6].right, 0)
        self.assertAlmostEqual(tree[6].distance, 0.254, 3)
        self.assertEqual(tree[7].left, -1)
        self.assertEqual(tree[7].right, 3)
        self.assertAlmostEqual(tree[7].distance, 0.391, 3)
        self.assertEqual(tree[8].left, -8)
        self.assertEqual(tree[8].right, -7)
        self.assertAlmostEqual(tree[8].distance, 0.532, 3)
        self.assertEqual(tree[9].left, 8)
        self.assertEqual(tree[9].right, -9)
        self.assertAlmostEqual(tree[9].distance, 3.234, 3)
        self.assertEqual(tree[10].left, -6)
        self.assertEqual(tree[10].right, 6)
        self.assertAlmostEqual(tree[10].distance, 4.636, 3)
        self.assertEqual(tree[11].left, -11)
        self.assertEqual(tree[11].right, -10)
        self.assertAlmostEqual(tree[11].distance, 12.741, 3)
      
        # Pairwise single-linkage clustering
        tree = treecluster(data=data2, mask=mask2, weight=weight2, transpose=0, method='s', dist='e')
        self.assertEqual(len(tree), len(data2)-1)
        self.assertEqual(tree[0].left, 4)
        self.assertEqual(tree[0].right, 5)
        self.assertAlmostEqual(tree[0].distance, 0.003, 3)
        self.assertEqual(tree[1].left, 9)
        self.assertEqual(tree[1].right, 12)
        self.assertAlmostEqual(tree[1].distance, 0.029, 3)
        self.assertEqual(tree[2].left, 11)
        self.assertEqual(tree[2].right, -2)
        self.assertAlmostEqual(tree[2].distance, 0.033, 3)
        self.assertEqual(tree[3].left, 1)
        self.assertEqual(tree[3].right, 2)
        self.assertAlmostEqual(tree[3].distance, 0.061, 3)
        self.assertEqual(tree[4].left, 10)
        self.assertEqual(tree[4].right, -3)
        self.assertAlmostEqual(tree[4].distance, 0.077, 3)
        self.assertEqual(tree[5].left, 7)
        self.assertEqual(tree[5].right, -5)
        self.assertAlmostEqual(tree[5].distance, 0.092, 3)
        self.assertEqual(tree[6].left, 0)
        self.assertEqual(tree[6].right, -4)
        self.assertAlmostEqual(tree[6].distance, 0.242, 3)
        self.assertEqual(tree[7].left, -7)
        self.assertEqual(tree[7].right, -1)
        self.assertAlmostEqual(tree[7].distance, 0.246, 3)
        self.assertEqual(tree[8].left, 3)
        self.assertEqual(tree[8].right, -8)
        self.assertAlmostEqual(tree[8].distance, 0.287, 3)
        self.assertEqual(tree[9].left, -9)
        self.assertEqual(tree[9].right, 8)
        self.assertAlmostEqual(tree[9].distance, 1.936, 3)
        self.assertEqual(tree[10].left, -10)
        self.assertEqual(tree[10].right, -6)
        self.assertAlmostEqual(tree[10].distance, 3.432, 3)
        self.assertEqual(tree[11].left, 6)
        self.assertEqual(tree[11].right, -11)
        self.assertAlmostEqual(tree[11].distance, 3.535, 3)
      
        # Pairwise centroid-linkage clustering
        tree = treecluster(data=data2, mask=mask2, weight=weight2, transpose=0, method='c', dist='e')
        self.assertEqual(len(tree), len(data2)-1)
        self.assertEqual(tree[0].left, 4)
        self.assertEqual(tree[0].right, 5)
        self.assertAlmostEqual(tree[0].distance, 0.003, 3)
        self.assertEqual(tree[1].left, 12)
        self.assertEqual(tree[1].right, 9)
        self.assertAlmostEqual(tree[1].distance, 0.029, 3)
        self.assertEqual(tree[2].left, 1)
        self.assertEqual(tree[2].right, 2)
        self.assertAlmostEqual(tree[2].distance, 0.061, 3)
        self.assertEqual(tree[3].left, -2)
        self.assertEqual(tree[3].right, 11)
        self.assertAlmostEqual(tree[3].distance, 0.063, 3)
        self.assertEqual(tree[4].left, 10)
        self.assertEqual(tree[4].right, -4)
        self.assertAlmostEqual(tree[4].distance, 0.109, 3)
        self.assertEqual(tree[5].left, -5)
        self.assertEqual(tree[5].right, 7)
        self.assertAlmostEqual(tree[5].distance, 0.189, 3)
        self.assertEqual(tree[6].left, 0)
        self.assertEqual(tree[6].right, -3)
        self.assertAlmostEqual(tree[6].distance, 0.239, 3)
        self.assertEqual(tree[7].left, 3)
        self.assertEqual(tree[7].right, -1)
        self.assertAlmostEqual(tree[7].distance, 0.390, 3)
        self.assertEqual(tree[8].left, -7)
        self.assertEqual(tree[8].right, -8)
        self.assertAlmostEqual(tree[8].distance, 0.382, 3)
        self.assertEqual(tree[9].left, -9)
        self.assertEqual(tree[9].right, 8)
        self.assertAlmostEqual(tree[9].distance, 3.063, 3)
        self.assertEqual(tree[10].left, 6)
        self.assertEqual(tree[10].right, -6)
        self.assertAlmostEqual(tree[10].distance, 4.578, 3)
        self.assertEqual(tree[11].left, -10)
        self.assertEqual(tree[11].right, -11)
        self.assertAlmostEqual(tree[11].distance, 11.536, 3)
      
        # Pairwise maximum-linkage clustering
        tree = treecluster(data=data2, mask=mask2, weight=weight2, transpose=0, method='m', dist='e')
        self.assertEqual(len(tree), len(data2)-1)
        self.assertEqual(tree[0].left, 5)
        self.assertEqual(tree[0].right, 4)
        self.assertAlmostEqual(tree[0].distance, 0.003, 3)
        self.assertEqual(tree[1].left, 9)
        self.assertEqual(tree[1].right, 12)
        self.assertAlmostEqual(tree[1].distance, 0.029, 3)
        self.assertEqual(tree[2].left, 2)
        self.assertEqual(tree[2].right, 1)
        self.assertAlmostEqual(tree[2].distance, 0.061, 3)
        self.assertEqual(tree[3].left, 11)
        self.assertEqual(tree[3].right, 10)
        self.assertAlmostEqual(tree[3].distance, 0.077, 3)
        self.assertEqual(tree[4].left, -2)
        self.assertEqual(tree[4].right, -4)
        self.assertAlmostEqual(tree[4].distance, 0.216, 3)
        self.assertEqual(tree[5].left, -3)
        self.assertEqual(tree[5].right, 0)
        self.assertAlmostEqual(tree[5].distance, 0.266, 3)
        self.assertEqual(tree[6].left, -5)
        self.assertEqual(tree[6].right, 7)
        self.assertAlmostEqual(tree[6].distance, 0.302, 3)
        self.assertEqual(tree[7].left, -1)
        self.assertEqual(tree[7].right, 3)
        self.assertAlmostEqual(tree[7].distance, 0.425, 3)
        self.assertEqual(tree[8].left, -8)
        self.assertEqual(tree[8].right, -6)
        self.assertAlmostEqual(tree[8].distance, 0.968, 3)
        self.assertEqual(tree[9].left, 8)
        self.assertEqual(tree[9].right, 6)
        self.assertAlmostEqual(tree[9].distance, 3.975, 3)
        self.assertEqual(tree[10].left, -10)
        self.assertEqual(tree[10].right, -7)
        self.assertAlmostEqual(tree[10].distance, 5.755, 3)
        self.assertEqual(tree[11].left, -11)
        self.assertEqual(tree[11].right, -9)
        self.assertAlmostEqual(tree[11].distance, 22.734, 3)

    def test_somcluster(self):
        if TestCluster.module=='Bio.Cluster':
            from Bio.Cluster import somcluster
        elif TestCluster.module=='Pycluster':
            from Pycluster import somcluster

        # First data set
        weight = [ 1,1,1,1,1 ]
        data = array([[  1.1, 2.2, 3.3, 4.4, 5.5], 
                      [  3.1, 3.2, 1.3, 2.4, 1.5], 
                      [  4.1, 2.2, 0.3, 5.4, 0.5], 
                      [ 12.1, 2.0, 0.0, 5.0, 0.0]])
        mask = array([[ 1, 1, 1, 1, 1], 
                      [ 1, 1, 1, 1, 1], 
                      [ 1, 1, 1, 1, 1], 
                      [ 1, 1, 1, 1, 1]])

        clusterid, celldata = somcluster(data=data, mask=mask, weight=weight, transpose=0, nxgrid=10, nygrid=10, inittau=0.02, niter=100, dist='e')
        self.assertEqual(len(clusterid), len(data))
        self.assertEqual(len(clusterid[0]), 2)

        # Second data set
        weight =  [ 1,1 ]
        data = array([[ 1.1, 1.2 ],
                      [ 1.4, 1.3 ],
                      [ 1.1, 1.5 ],
                      [ 2.0, 1.5 ],
                      [ 1.7, 1.9 ],
                      [ 1.7, 1.9 ],
                      [ 5.7, 5.9 ],
                      [ 5.7, 5.9 ],
                      [ 3.1, 3.3 ],
                      [ 5.4, 5.3 ],
                      [ 5.1, 5.5 ],
                      [ 5.0, 5.5 ],
                      [ 5.1, 5.2 ]])
        mask = array([[ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ],
                      [ 1, 1 ]])

        clusterid, celldata = somcluster(data=data, mask=mask, weight=weight, transpose=0, nxgrid=10, nygrid=10, inittau=0.02, niter=100, dist='e')
        self.assertEqual(len(clusterid), len(data))
        self.assertEqual(len(clusterid[0]), 2)

    def test_distancematrix_kmedoids(self):
        if TestCluster.module=='Bio.Cluster':
            from Bio.Cluster import distancematrix, kmedoids
        elif TestCluster.module=='Pycluster':
            from Pycluster import distancematrix, kmedoids

        data = array([[2.2, 3.3, 4.4],
                      [2.1, 1.4, 5.6],
                      [7.8, 9.0, 1.2],
                      [4.5, 2.3, 1.5],
                      [4.2, 2.4, 1.9],
                      [3.6, 3.1, 9.3],
                      [2.3, 1.2, 3.9],
                      [4.2, 9.6, 9.3],
                      [1.7, 8.9, 1.1]])
        mask = array([[1, 1, 1],
                      [1, 1, 1],
                      [0, 1, 1],
                      [1, 1, 1],
                      [1, 1, 1],
                      [0, 1, 0],
                      [1, 1, 1],
                      [1, 0, 1],
                      [1, 1, 1]])
        weight = array([2.0, 1.0, 0.5])
        matrix = distancematrix(data, mask=mask, weight=weight)

        self.assertAlmostEqual(matrix[1][0], 1.243, 3)

        self.assertAlmostEqual(matrix[2][0], 25.073, 3)
        self.assertAlmostEqual(matrix[2][1], 44.960, 3)

        self.assertAlmostEqual(matrix[3][0], 4.510, 3)
        self.assertAlmostEqual(matrix[3][1], 5.924, 3)
        self.assertAlmostEqual(matrix[3][2], 29.957, 3)

        self.assertAlmostEqual(matrix[4][0], 3.410, 3)
        self.assertAlmostEqual(matrix[4][1], 4.761, 3)
        self.assertAlmostEqual(matrix[4][2], 29.203, 3)
        self.assertAlmostEqual(matrix[4][3], 0.077, 3)

        self.assertAlmostEqual(matrix[5][0], 0.040, 3)
        self.assertAlmostEqual(matrix[5][1], 2.890, 3)
        self.assertAlmostEqual(matrix[5][2], 34.810, 3)
        self.assertAlmostEqual(matrix[5][3], 0.640, 3)
        self.assertAlmostEqual(matrix[5][4], 0.490, 3)

        self.assertAlmostEqual(matrix[6][0], 1.301, 3)
        self.assertAlmostEqual(matrix[6][1], 0.447, 3)
        self.assertAlmostEqual(matrix[6][2], 42.990, 3)
        self.assertAlmostEqual(matrix[6][3], 3.934, 3)
        self.assertAlmostEqual(matrix[6][4], 3.046, 3)
        self.assertAlmostEqual(matrix[6][5], 3.610, 3)

        self.assertAlmostEqual(matrix[7][0], 8.002, 3)
        self.assertAlmostEqual(matrix[7][1], 6.266, 3)
        self.assertAlmostEqual(matrix[7][2], 65.610, 3)
        self.assertAlmostEqual(matrix[7][3], 12.240, 3)
        self.assertAlmostEqual(matrix[7][4], 10.952, 3)
        self.assertAlmostEqual(matrix[7][5], 0.000, 3)
        self.assertAlmostEqual(matrix[7][6], 8.720, 3)

        self.assertAlmostEqual(matrix[8][0], 10.659, 3)
        self.assertAlmostEqual(matrix[8][1], 19.056, 3)
        self.assertAlmostEqual(matrix[8][2], 0.010, 3)
        self.assertAlmostEqual(matrix[8][3], 16.949, 3)
        self.assertAlmostEqual(matrix[8][4], 15.734, 3)
        self.assertAlmostEqual(matrix[8][5], 33.640, 3)
        self.assertAlmostEqual(matrix[8][6], 18.266, 3)
        self.assertAlmostEqual(matrix[8][7], 18.448, 3)
        clusterid, error, nfound = kmedoids(matrix, npass=1000)
        self.assertEqual(clusterid, array([5, 5, 2, 5, 5, 5, 5, 5, 2]))
        self.assertAlmostEqual(error, 7.680, 3)

if __name__ == "__main__" :
    print "test_Cluster"
    run_tests("Bio.Cluster")
