# Copyright 2007 by Tiago Antao.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

'''
SimCoal2 execution module and support functions.
'''

from os import sep, access, F_OK
from sys import path

#This is a workaround to work with the test system
#In any case the problem is with the test system
for instance in path:
    test_path = instance + sep + sep.join(['Bio', 'PopGen', 'SimCoal', 'data'])
    if access(test_path, F_OK):
        builtin_tpl_dir = test_path
        break
