import sys, urllib
from xml.sax import saxutils
import ReseekFile

class FormatIOIterator:
    def __init__(self, obj):
        self.obj = obj
        self._n = 0
    def next(self):
        x = self.obj.next()
        if x is not None:
            self._n += 1
            return x.document
        return x
    def __getitem__(self, i):
        assert i == self._n, "forward iteration only"
        x = self.next()
        if x is None:
            raise IndexError(i)
        return x

class FormatIO:
    def __init__(self, name,
                 default_input_format = None,
                 default_output_format = None,
                 abbrev = None,
                 registery = None):
        if abbrev is None:
            abbrev = name
        if registery is None:
            import Bio
            registery = Bio.formats
        
        self.name = name
        self.abbrev = abbrev
        self.default_input_format = default_input_format
        self.default_output_format = default_output_format
        self.registery = registery

    def _find_builder(self, builder, resolver):
        if builder is None:
            builder = self.registery.find_builder(resolver, self)
##            if builder is None:
##                raise TypeError(
##                    "Could not find a %r builder for %r types" % \
##                    (self.name, resolver.format.name))
        return builder

    def _get_file_format(self, format, source):
        import Format        
        # By construction, this is the lowest we can go, so don't try
        if isinstance(format, Format.FormatDef):
            return format

        source = saxutils.prepare_input_source(source)
        infile = source.getCharacterStream() or source.getByteStream()
        
        is_reseek = 0
        try:
            infile.tell()
        except (AttributeError, IOError):
            infile = ReseekFile.ReseekFile(infile)
            is_reseek = 1

        format = format.identifyFile(infile)

        if is_reseek:
            infile.nobuffer()

        # returned file could be a ReseekFile!
        return format, infile
        

    def readFile(self, infile, format = None, builder = None, debug_level = 0):
        if format is None:
            format = self.default_input_format
        format = self.registery.normalize(format)

        format, infile = self._get_file_format(format, infile)
            
        if format is None:
            raise TypeError("Could not determine file type")

        builder = self._find_builder(builder, format)

        exp = format.expression

        if hasattr(builder, "uses_tags"):
            import Martel
            uses_tags = tuple(builder.uses_tags())
            exp = Martel.select_names(exp, uses_tags + ("record", "dataset"))
        
        iterator = exp.make_iterator("record", debug_level = debug_level)
        return FormatIOIterator(iterator.iterateFile(infile, builder))


    def readString(self, s, format = None, builder = None, debug_level = 0):
        if format is None:
            format = self.default_input_format
        format = self.registery.normalize(format)

        import Format
        if not isinstance(format, Format.FormatDef):
            format = format.identifyString(s)

        builder = self._find_builder(builder, format)

        iterator = format.make_iterator("record", debug_level = debug_level)
        
        return FormatIOIterator(iterator.iterateString(s, builder))
      
                  
    def read(self, systemID, format = None, builder = None, debug_level = 0):
        if isinstance(systemID, type("")):
            # URL
            infile = ReseekFile.ReseekFile(urllib.urlopen(systemID))
        else:
            infile = systemID
        return self.readFile(infile, format, builder, debug_level)

    def make_writer(self, outfile = sys.stdout, format = None):
        if format is None:
            format = self.default_output_format
        format = self.registery.normalize(format)
        return self.registery.find_writer(self, format, outfile)

    def convert(self, infile = sys.stdin, outfile = sys.stdout,
                input_format = None, output_format = None):
        if input_format is None:
            input_format = self.default_input_format
        input_format = self.registery.normalize(input_format)

        input_format, infile = self._get_file_format(input_format, infile)
        if input_format is None:
            raise TypeError("Could not not determine file type")

        builder = self._find_builder(None, input_format)

        writer = self.make_writer(outfile, output_format)

        exp = input_format.expression
        if hasattr(builder, "uses_tags"):
            import Martel
            uses_tags = tuple(builder.uses_tags())
            exp = Martel.select_names(exp, uses_tags + ("record", "dataset"))
        
        parser = exp.make_parser()

        import StdHandler        
        parser.setContentHandler(StdHandler.ConvertHandler(builder, writer))
            
        parser.parseFile(infile)

