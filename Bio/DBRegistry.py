# Copyright 2002 by Jeffrey Chang.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

import time

import _FmtUtils
from Bio.Tools import listfns
from Bio.Tools.MultiProc.copen import copen_fn
from ReseekFile import ReseekFile


class DBDef:
    # name
    # abbrev    (optional)
    # source    Source object
    # failure   (optional)
    # params    (optional)
    # key       (optional)
    def __init__(self, **keywds):
        self.name = keywds['name']
        self.abbrev = keywds.get("abbrev", self.name)
        self.source = keywds['source']
        self.failure_cases = keywds.get("failure", [])
        self.params = keywds.get("params", [])
        self.key = keywds.get("key", None)
    def _normalize_params(self, args, keywds):
        params = self.params[:]
        params.extend(keywds.items())
        if args:
            if len(args) > 1:
                raise ValueError, "I can't handle multiple arguments"
            elif self.key is None:
                raise ValueError, "I got an arg but no key"
            params.append((self.key, args[0]))
        # XXX check for missing parameters?
        return params
    def __call__(self, *args, **keywds):
        params = self._normalize_params(args, keywds)
        return self.source.get(params, self.failure_cases)
    def __getitem__(self, key):
        return self(key)
    def cache(self, handle, *args, **keywds):
        params = self._normalize_params(args, keywds)
        self.source.set(self.key, handle)

class DBGroup:
    # name
    # abbrev
    # behavior
    # cache
    # XXX NEED TO CHECK TO MAKE SURE NO EXTRANEOUS ARGS
    def __init__(self, **keywds):
        self.name = keywds['name']
        self.abbrev = keywds.get("abbrev", self.name)
        self.behavior = keywds['behavior']
        self.cache = keywds.get("cache", None)
        self.dbdefs = []
    def __call__(self, *args, **keywds):
        # first, check the cache.  If the cache lookup works, then
        # don't look at anything else.
        if self.cache:
            try:
                return self.cache(*args, **keywds)
            except IOError:
                pass
        if self.behavior.lower() == "concurrent":
            handle = self._run_concurrent(self.dbdefs, args, keywds)
        elif self.behavior.lower() == "serial":
            handle = self._run_serial(self.dbdefs, args, keywds)
        else:
            raise AssertionError, "Unknown grouping behavior (%s)" % \
                  self.behavior
        if self.cache:
            handle = ReseekFile.ReseekFile(handle)
            pos = handle.tell()
            self.cache.cache(handle, *args, **keywds)
            handle.seek(pos)
        return handle

    def _serialize(self, dbdef, args, keywds):
        handle = dbdef(*args, **keywds)
        return handle.read()

    def _run_concurrent(self, dbdefs, args, keywds):
        fnhandles = []
        for db in dbdefs:
            fnhandles.append(copen_fn(self._serialize, db, args, keywds))
        i = 0
        # Check each of the function handles until one of the
        # finishes or they all fails.
        while fnhandles:
            if i >= len(fnhandles):
                i -= len(fnhandles)
                time.sleep(0.1)
            try:
                ready = fnhandles[i].poll()
            except IOError:
                # This handle failed, so get rid of it.
                del fnhandles[i]
                continue
            if ready:
                handle = fnhandles[i]
                # Shut down all the other requests that didn't finish.
                for j in range(len(fnhandles)):
                    if j != i:
                        fnhandles[j].close()
                break
            else:
                i += 1
        else:
            raise IOError, "I could not get any results."
        return handle
            
    def _run_serial(self, dbdefs, args, keywds):
        for db in dbdefs:
            try:
                handle = db(*args, **keywds)
            except IOError:
                continue
            else:
                return handle
        raise IOError, "I could not get any results."

    def __getitem__(self, key):
        return self(key)
    
class DBRegistry:
    # This class should be merged with FormatRegistry.py
    def __init__(self, loadpath=None):
        self._name_table = {}
        self._abbrev_table = {}
        self.loadpath = loadpath
        self._autoloaded = 0
        self._autoloading = 0

    def _autoload(self):
        if not self.loadpath:
            return
        if self._autoloaded or self._autoloading:
            return
        self._autoloading = 1
        _FmtUtils.load_basemodule(self.loadpath, package="dbdefs")
        self.autoloading = 0
        self._autoloaded = 1

    # XXX need to check kwargs to make sure there's nothing extraneous
    def register_db(self, **kwargs):
        self._autoload()
        if kwargs.has_key("source"):
            format = DBDef(**kwargs)
        else:
            format = DBGroup(**kwargs)
        name = format.name
        abbrev = format.abbrev
        if self._name_table.has_key(name):
            raise TypeError("%r is a duplicate entry" % (name,))
        if self._abbrev_table.has_key(abbrev):
            raise TypeError("%r is a duplicate entry" % (abbrev,))
        
        self._name_table[name] = format
        self._abbrev_table[abbrev] = format

    def __getitem__(self, name):
        self._autoload()
        return self._name_table[name]  # raises KeyError for unknown formats

    def group(self, group_name, name):
        if not self._name_table.has_key(group_name):
            raise ValueError, "%s not found in registry" % group_name
        if not self._name_table.has_key(name):
            raise ValueError, "%s not found in registry" % name
        groupobj = self._name_table[group_name]
        groupobj.dbdefs.append(self._name_table[name])
            
    def get(self, name, default = None):
        self._autoload()
        return self._name_table.get(name, default)

    def keys(self):
        self._autoload()
        return self._name_table.keys()
    def values(self):
        self._autoload()
        return self._name_table.values()
    def items(self):
        self._autoload()
        return self._name_table.items()

    def __str__(self):
        locations = self.keys()
        locations.sort()
        if not locations:
            return "DBRegistry"
        return "DBRegistry, exporting %s" % ', '.join(map(repr, locations))
    __repr__ = __str__
