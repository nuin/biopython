# Copyright 2002 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

from Bio.config.DBRegistry import CGIDB, DBGroup
from _support import *

swissprot_expasy_cgi = CGIDB(
    name="swissprot-expasy-cgi",
    doc="Retrieve a swiss-prot entry by ID",
    cgi="http://www.expasy.ch/cgi-bin/get-sprot-raw.pl",
    delay=5.0,
    timeout=10,
    params=[],
    key="",
    failure_cases=[(blank_expr, "no results")]
    )

swissprot = DBGroup(
    name="swissprot",
    behavior="serial",
    )
swissprot.add(swissprot_expasy_cgi)
