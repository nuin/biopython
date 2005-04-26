#! /usr/bin/python
#
# parse_pdb_header.py
# parses header of PDB files into a python dictionary.
# emerged from the Columba database project www.columba-db.de.
# 
# author: Kristian Rother
# 
# license: same as BioPython, read LICENSE.TXT from current BioPython release.
# 
# last modified: 9.2.2004
#
# Added some small changes: the whole PDB file is not read in anymore, but just
# until the first ATOM record (faster). I also split parse_pdb_header into 
# parse_pdb_header and parse_pdb_header_list, because parse_pdb_header_list
# can be more easily reused in PDBParser.
#
# Thomas, 19/03/04
#
# Renamed some clearly private functions to _something (ie. parse_pdb_header_list
# is now _parse_pdb_header_list)
# Thomas 9/05/04

__doc__="Parse the header of a PDB file."

import sys
import os,string,re
import urllib
import types


def _get_journal(inl):
    # JRNL        AUTH   L.CHEN,M.DOI,F.S.MATHEWS,A.Y.CHISTOSERDOV,           2BBK   7
    journal=""
    for l in inl:
        if re.search("\AJRNL",l):
            journal+=string.lower(l[19:72])
    journal=re.sub("\s\s+"," ",journal)
    return journal

def _get_references(inl):
    # REMARK   1 REFERENCE 1                                                  1CSE  11
    # REMARK   1  AUTH   W.BODE,E.PAPAMOKOS,D.MUSIL                           1CSE  12
    references=[]
    actref=""
    for l in inl:        
        if re.search("\AREMARK   1",l):
            if re.search("\AREMARK   1 REFERENCE",l):
                if actref!="":
                    actref=re.sub("\s\s+"," ",actref)
                    if actref!=" ":
                        references.append(actref)
                    actref=""
            else:
                actref+=string.lower(l[19:72])

    if actref!="":
        actref=re.sub("\s\s+"," ",actref)
        if actref!=" ":
            references.append(actref)
    return references
    
      
# bring dates to format: 1909-01-08
def _format_date(pdb_date):
    """Converts dates from DD-Mon-YY to YYYY-MM-DD format."""
    date=""
    year=int(pdb_date[7:])
    if year<50:
        century=2000
    else:
        century=1900            
    date=str(century+year)+"-"
    all_months=['xxx','Jan','Feb','Mar','Apr','May','Jun','Jul',\
    'Aug','Sep','Oct','Nov','Dec']        
    month=str(all_months.index(pdb_date[3:6]))
    if len(month)==1:
        month = '0'+month
    date = date+month+'-'+pdb_date[:2]
    return date


def _chop_end_codes(line):
    """Chops lines ending with  '     1CSA  14' and the like."""
    import re
    return re.sub("\s\s\s\s+[\w]{4}.\s+\d*\Z","",line)

def _chop_end_misc(line):
    """Chops lines ending with  '     14-JUL-97  1CSA' and the like."""
    import re
    return re.sub("\s\s\s\s+.*\Z","",line)

def _nice_case(line):
    """Makes A Lowercase String With Capitals."""
    import string
    l=string.lower(line)
    s=""
    i=0
    nextCap=1
    while i<len(l):
        c=l[i]
        if c>='a' and c<='z' and nextCap:
            c=string.upper(c)
            nextCap=0
        elif c==' ' or c=='.' or c==',' or c==';' or c==':' or c=='\t' or\
            c=='-' or c=='_':
            nextCap=1            
        s+=c
        i+=1
    return s

def parse_pdb_header(file):
    """
    Returns the header lines of a pdb file as a dictionary.

    Dictionary keys are: head, deposition_date, release_date, structure_method,
    resolution, structure_reference, journal_reference, author and
    compound.
    """
    header=[]
    if type(file)==types.StringType:
        f=open(file,'r')
    else:
        f=file
    while f:
        l=f.readline()
        record_type=l[0:6]
        if record_type=='ATOM  ' or record_type=='HETATM' or record_type=='MODEL ':
            break
        else:
            header.append(l)    
    f.close()
    return _parse_pdb_header_list(header)

def _parse_pdb_header_list(header):
    # database fields
    dict={'name':"",
        'head':'',
        'deposition_date' : "1909-01-08",
        'release_date' : "1909-01-08",
        'structure_method' : "unknown",
        'resolution' : 0.0,
        'structure_reference' : "unknown",
        'journal_reference' : "unknown",
        'author' : "",
        'compound':{'1':{'misc':''}},'source':{'1':{'misc':''}}}

    dict['structure_reference'] = _get_references(header)
    dict['journal_reference'] = _get_journal(header)
    comp_molid="1"
    src_molid="1"
    last_comp_key="misc"
    last_src_key="misc"

    for hh in header:
        h=re.sub("[\s\n\r]*\Z","",hh) # chop linebreaks off
        key=re.sub("\s.+\s*","",h)
        tail=re.sub("\A\w+\s+\d*\s*","",h)
        # print key+":"+tail
        
        # From here, all the keys from the header are being parsed
        if key=="TITLE":
            name=string.lower(_chop_end_codes(tail))
            if dict.has_key('name'):
                dict['name'] += " "+name
            else:
                dict['name']=name
        elif key=="HEADER":            
            rr=re.search("\d\d-\w\w\w-\d\d",tail)
            if rr!=None:
                dict['deposition_date']=_format_date(_nice_case(rr.group()))
            head=string.lower(_chop_end_misc(tail))
            dict['head']=head
        elif key=="COMPND":            
            tt=string.lower(re.sub("\;\s*\Z","",_chop_end_codes(tail)))
            # look for E.C. numbers in COMPND lines
            rec = re.search('\d+\.\d+\.\d+\.\d+',tt)
            if rec:
                dict['compound'][comp_molid]['ec_number']=rec.group()
                tt=re.sub("\((e\.c\.)*\d+\.\d+\.\d+\.\d+\)","",tt)
            tok=tt.split(":")
            if len(tok)>=2:
                ckey=tok[0]
                cval=re.sub("\A\s*","",tok[1])
                if ckey=='mol_id':
                    dict['compound'][cval]={'misc':''}
                    comp_molid=cval
                    last_comp_key="misc"
                else:
                    dict['compound'][comp_molid][ckey]=cval            
                    last_comp_key=ckey
            else:
                dict['compound'][comp_molid][last_comp_key]+=tok[0]+" "
        elif key=="SOURCE":
            tt=string.lower(re.sub("\;\s*\Z","",_chop_end_codes(tail)))
            tok=tt.split(":")
            # print tok
            if len(tok)>=2:
                ckey=tok[0]
                cval=re.sub("\A\s*","",tok[1])
                if ckey=='mol_id':
                    dict['source'][cval]={'misc':''}
                    comp_molid=cval
                    last_src_key="misc"
                else:
                    dict['source'][comp_molid][ckey]=cval            
                    last_src_key=ckey
            else:
                dict['source'][comp_molid][last_src_key]+=tok[0]+" "
        elif key=="KEYWDS":
            kwd=string.lower(_chop_end_codes(tail))
            if dict.has_key('keywords'):
                dict['keywords']+=" "+kwd
            else:
                dict['keywords']=kwd
        elif key=="EXPDTA":
            expd=_chop_end_codes(tail)
            # chop junk at end of lines for some structures
            expd=re.sub('\s\s\s\s\s\s\s.*\Z','',expd)
            # if re.search('\Anmr',expd,re.IGNORECASE): expd='nmr'
            # if re.search('x-ray diffraction',expd,re.IGNORECASE): expd='x-ray diffraction'
            dict['structure_method']=string.lower(expd)
        elif key=="CAVEAT":
            # make Annotation entries out of these!!!
            pass
        elif key=="REVDAT":
            rr=re.search("\d\d-\w\w\w-\d\d",tail)
            if rr!=None:
                dict['release_date']=_format_date(_nice_case(rr.group()))
        elif key=="JRNL":
            # print key,tail
            if dict.has_key('journal'):
                dict['journal']+=tail
            else:
                dict['journal']=tail
        elif key=="AUTHOR":
            auth = _nice_case(_chop_end_codes(tail))
            if dict.has_key('author'):
                dict['author']+=auth
            else:
                dict['author']=auth
        elif key=="REMARK":
            if re.search("REMARK   2 RESOLUTION.",hh):
                r=_chop_end_codes(re.sub("REMARK   2 RESOLUTION.",'',hh))
                r=re.sub("\s+ANGSTROMS.*","",r)
                try:
                    dict['resolution']=float(r)
                except:
                    #print 'nonstandard resolution',r
                    dict['resolution']=None
        else:
            # print key
            pass
    if dict['structure_method']=='unknown': 
        if dict['resolution']>0.0: dict['structure_method']='x-ray diffraction'
    return dict

if __name__=='__main__':
    """
    Reads a PDB file passed as argument, parses its header, extracts
    some data and returns it as a dictionary.
    """
    filename = sys.argv[1]
    file = open(filename,'r')
    dict = parse_pdb_header(file)
    
    # print the dictionary
    for d in dict.keys():
        print "-"*40
        print d
        print dict[d]
        

