"""Represent a Sequence Feature holding info about a part of a sequence.

This is heavily modeled after the Biocorba SeqFeature objects, and
may be pretty biased towards GenBank stuff since I'm writing it
for the GenBank parser output...

What's here:

Base class to hold a Feature.
----------------------------
classes:
o SeqFeature

Hold information about a Reference.
----------------------------------

This is an attempt to create a General class to hold Reference type
information.

classes:
o Reference

Specify locations of a feature on a Sequence.
---------------------------------------------

This aims to handle, in Ewan's words, 'the dreaded fuzziness issue' in
much the same way as Biocorba. This has the advantages of allowing us
to handle fuzzy stuff in case anyone needs it, and also be compatible
with Biocorba.

classes:
o FeatureLocation - Specify the start and end location of a feature.

o ExactPosition - Specify the position as being exact.
o WithinPosition - Specify a position occuring within some range.
o BetweenPosition - Specify a position occuring between a range.
o BeforePosition - Specify the position as being found before some base.
o AfterPosition - Specify the position as being found after some base.
"""

class SeqFeature:
    """Represent a Sequence Feature on an object.

    Attributes:
    o location - the location of the feature on the sequence
    o type - the specified type of the feature (ie. CDS, exon, repeat...)
    o location_operator - a string specifying how this SeqFeature may
    be related to others. For example, in the example GenBank feature
    shown below, the location_operator would be "join"
    o ref - A reference to another sequence. This could be an accession
    number for some different sequence.
    o ref_db - A different database for the reference accession number.
    o qualifier - A dictionary of qualifiers on the feature. These are
    analagous to the qualifiers from a GenBank feature table. The keys of
    the dictionary are qualifier names, the values are the qualifier
    values.
    o sub_features - Additional SeqFeatures which fall under this 'parent'
    feature. For instance, if we having something like:

    CDS    join(1..10,30..40,50..60)

    The the top level feature would be a CDS from 1 to 60, and the sub
    features would be of 'CDS_join' type and would be from 1 to 10, 30 to
    40 and 50 to 60, respectively.
    """
    def __init__(self, location = None, type = '', location_operator = '',
                 strand = None, qualifiers = {}, sub_features = [],
                 ref = None, ref_db = None):
        """Initialize a SeqFeature on a Sequence.
        """
        self.location = location

        self.type = type
        self.location_operator = location_operator
        self.ref = ref 
        self.ref_db = ref_db
        self.strand = strand
        self.qualifiers = qualifiers
        self.sub_features = sub_features

    def __str__(self):
        """Make it easier to debug features.
        """
        out = "type: %s\n" % self.type
        out += "location: %s\n" % self.location
        out += "ref: %s:%s\n" % (self.ref, self.ref_db)
        out += "strand: %s\n" % self.strand
        out += "qualifiers: \n"
        qualifier_keys = self.qualifiers.keys()
        qualifier_keys.sort()
        for qual_key in qualifier_keys:
            out += "\tKey: %s, Value: %s\n" % (qual_key,
                                               self.qualifiers[qual_key])
        if len(self.sub_features) != 0:
            out += "Sub-Features\n"
            for sub_feature in self.sub_features:
                out +="%s\n" % sub_feature

        return out

# --- References

# TODO -- Will this hold PubMed and Medline information decently?
class Reference:
    """Represent a Generic Reference object.

    Attributes:
    o location - A list of Location objects specifying regions of
    the sequence that the references correspond to. If no locations are
    specified, the entire sequence is assumed.
    o authors - A big old string, or a list split by author, of authors
    for the reference.
    o title - The title of the reference.
    o journal - Journal the reference was published in.
    o medline_id - A medline reference for the article.
    o pubmed_id - A pubmed reference for the article.
    o comment - A place to stick any comments about the reference.
    """
    def __init__(self):
        self.location = []
        self.authors = ''
        self.title = ''
        self.journal = ''
        self.medline_id = ''
        self.pubmed_id = ''
        self.comment = ''

    def __str__(self):
        """Output an informative string for debugging.
        """
        out = ""
        for single_location in self.location:
            out += "location: %s\n" % single_location
        out += "authors: %s\n" % self.authors
        out += "title: %s\n" % self.title
        out += "journal: %s\n" % self.journal
        out += "medline id: %s\n" % self.medline_id
        out += "pubmed id: %s\n" % self.pubmed_id
        out += "comment: %s\n" % self.comment

        return out

# --- Handling feature locations

class FeatureLocation:
    """Specify the location of a feature along a sequence.

    This attempts to deal with fuzziness of position ends, but also
    make it easy to get the start and end in the 'normal' case (no
    fuzziness).

    You should access the start and end attributes with
    your_location.start and your_location.end. If the start and
    end are exact, this will return the positions, if not, we'll return
    the approriate Fuzzy class with info about the position and fuzziness.
    """
    def __init__(self, start, end):
        """Specify the start and end of a sequence feature.

        start and end arguments specify the values where the feature begins
        and ends. These can either by any of the *Position objects that
        inherit from AbstractPosition, or can just be integers specifying the
        position. In the case of integers, the values are assumed to be
        exact and are converted in ExactPosition arguments. This is meant
        to make it easy to deal with non-fuzzy ends.
        """
        if isinstance(start, AbstractPosition):
            self._start = start
        else:
            self._start = ExactPosition(start)

        if isinstance(end, AbstractPosition):
            self._end = end
        else:
            self._end = ExactPosition(end)

    def __str__(self):
        return "(%s..%s)" % (self._start, self._end)

    def __getattr__(self, attr):
        """Make it easy to get non-fuzzy starts and ends.

        We override get_attribute here so that in non-fuzzy cases we
        can just return the start and end position without any hassle.

        To get fuzzy start and ends, just ask for item.start and
        item.end. To get non-fuzzy attributes (ie. the position only)
        ask for 'item.nofuzzy_start', 'item.nofuzzy_end'. These should return
        the largest range of the fuzzy position. So something like:
        (10.20)..(30.40) should return 10 for start, and 40 for end.
        """
        if attr == 'start':
            return self._start
        elif attr == 'end':
            return self._end
        elif attr == 'nofuzzy_start':
            return min(self._start.position,
                       self._start.position + self._start.extension)
        elif attr == 'nofuzzy_end':
            return max(self._end.position,
                       self._end.position + self._end.extension)
        else:
            raise AttributeError("Cannot evaluate attribute %s." % attr)

class AbstractPosition:
    """Abstract base class representing a position.
    """
    def __init__(self, position, extension):
        self.position = position
        self.extension = extension
            
class ExactPosition(AbstractPosition):
    """Specify the specific position of a boundary.

    o position - The position of the boundary.
    o extension - An optional argument which must be zero since we don't
    have an extension. The argument is provided so that the same number of
    arguments can be passed to all position types.

    In this case, there is no fuzziness associated with the position.
    """
    def __init__(self, position, extension = 0):
        if extension != 0:
            raise AttributeError("Non-zero extension %s for exact position."
                                 % extension)
        AbstractPosition.__init__(self, position, 0)

    def __str__(self):
        return str(self.position)

class WithinPosition(AbstractPosition):
    """Specify the position of a boundary within some coordinates.

    Arguments:
    o position - The start position of the boundary
    o extension - The range to which the boundary can extend.

    This allows dealing with a position like ((1.4)..100). This
    indicates that the start of the sequence is somewhere between 1
    and 4. To represent that with this class we would set position as
    1 and extension as 3.
    """
    def __init__(self, position, extension = 0):
        AbstractPosition.__init__(self, position, extension)

    def __str__(self):
        return "(%s.%s)" % (self.position, self.position + self.extension)

class BetweenPosition(AbstractPosition):
    """Specify the position of a boundary between two coordinates.

    Arguments:
    o position - The start position of the boundary.
    o extension - The range to the other position of a boundary.

    This specifies a coordinate which is found between the two positions.
    So this allows us to deal with a position like ((1^2)..100). To
    represent that with this class we set position as 1 and the
    extension as 1.
    """
    def __init__(self, position, extension = 0):
        AbstractPosition.__init__(self, position, extension)

    def __str__(self):
        return "(%s^%s)" % (self.position, self.position + self.extension)

class BeforePosition(AbstractPosition):
    """Specify a position where the actual location occurs before it.

    Arguments:
    o position - The upper boundary of where the location can occur.
    o extension - An optional argument which must be zero since we don't
    have an extension. The argument is provided so that the same number of
    arguments can be passed to all position types.

    This is used to specify positions like (<10..100) where the location
    occurs somewhere before position 10.
    """
    def __init__(self, position, extension = 0):
        if extension != 0:
            raise AttributeError("Non-zero extension %s for exact position."
                                 % extension)
        AbstractPosition.__init__(self, position, 0)

    def __str__(self):
        return "<%s" % self.position

class AfterPosition(AbstractPosition):
    """Specify a position where the actual location is found after it.

    Arguments:
    o position - The lower boundary of where the location can occur.
    o extension - An optional argument which must be zero since we don't
    have an extension. The argument is provided so that the same number of
    arguments can be passed to all position types.

    This is used to specify positions like (>10..100) where the location
    occurs somewhere after position 10.
    """
    def __init__(self, position, extension = 0):
        if extension != 0:
            raise AttributeError("Non-zero extension %s for exact position."
                                 % extension)
        AbstractPosition.__init__(self, position, 0)

    def __str__(self):
        return ">%s" % self.position
