# -*- coding: utf-8 -*-
import csv
import inspect
import io
import sys
from collections import Iterable
from collections import OrderedDict


try:
    string_types = basestring
except NameError:
    string_types = str


class IterDictReader(object):
    def __init__(self, iterable, fieldnames=None, cleanup=None, restkey=None,
                 restval=None):
        self._cleanup = cleanup
        self._cleanup_has_run = False
        self.iterator = iter(iterable)
        if not fieldnames:
            try:
                fieldnames = next(self.iterator)
            except StopIteration as err:
                self.cleanup()
                raise err
        self.fieldnames = fieldnames
        self.restkey = restkey
        self.restval = restval

    def cleanup(self):
        if self._cleanup and not self._cleanup_has_run:
            self._cleanup()
            self._cleanup_has_run = True  # <- Should only execute one time.

    def __del__(self):
        self.cleanup()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            row = next(self.iterator)      # Unlike the basic reader, we prefer
            while row == []:               # not to return blanks, because we
                row = next(self.iterator)  # will typically wind up with a dict
        except StopIteration as err:     # full of None values.
            self.cleanup()
            raise err

        d = OrderedDict(zip(self.fieldnames, row))  # This code is adapted
        lf = len(self.fieldnames)                   # from the csv.DictReader
        lr = len(row)                               # class in the Python
        if lf < lr:                                 # Standard Library.
            d[self.restkey] = row[lf:]
        elif lf > lr:
            for key in self.fieldnames[lr:]:
                d[key] = self.restval
        return d

    def next(self):  # Included for Python 2 support.
        return self.__next__()


########################################################################
# CSV Reader.
########################################################################
if sys.version_info[0] >= 3:
    def _from_csv(csvfile, fieldnames, encoding, **kwds):
        if isinstance(csvfile, str):
            restkey = kwds.pop('restkey', None)
            restval = kwds.pop('restval', None)

            csvfile = open(csvfile, 'rt', encoding=encoding, newline='')
            reader = csv.reader(csvfile, **kwds)
            return IterDictReader(reader, fieldnames, cleanup=csvfile.close,
                                  restkey=restkey, restval=restval)  # <- EXIT!

        if isinstance(csvfile, io.IOBase):
            if not isinstance(csvfile, io.TextIOBase):
                cls_name = csvfile.__class__.__name__
                raise TypeError('stream object must inherit from '
                                'io.TextIOBase, got {0}'.format(cls_name))
        elif not isinstance(csvfile, Iterable):
            cls_name = csvfile.__class__.__name__
            raise TypeError('unsupported type {0}'.format(cls_name))

        return csv.DictReader(csvfile, fieldnames, **kwds)

else:
    import codecs

    class UTF8Recoder(object):
        """Iterator that reads an encoded stream and reencodes the
        input to UTF-8.

        This class is adapted from example code in Python 2.7 docs
        for the csv module.
        """
        def __init__(self, f, encoding):
            self.reader = codecs.getreader(encoding)(f)

        def __iter__(self):
            return self

        def next(self):
            return self.reader.next().encode('utf-8')


    class UnicodeReader(object):
        """A CSV reader which will iterate over lines in the CSV
        file *f*, which is encoded in the given encoding.

        This class is adapted from example code in Python 2.7 docs
        for the csv module.
        """
        def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
            f = UTF8Recoder(f, encoding)
            self.reader = csv.reader(f, dialect=dialect, **kwds)

        @property
        def line_num(self):
            return self.reader.line_num

        @line_num.setter
        def line_num(self, value):
            self.reader.line_num = value

        def next(self):
            row = self.reader.next()
            return [unicode(s, 'utf-8') for s in row]

        def __iter__(self):
            return self


    def _from_csv(csvfile, fieldnames, encoding, **kwds):
        if isinstance(csvfile, basestring):
            csvfile = io.open(csvfile, 'rb')
        elif hasattr(csvfile, 'mode'):
            if 'b' not in csvfile.mode:
                raise TypeError('Python 2 compatibility expects binary-'
                                'mode file, got {0!r}'.format(csvfile.mode))
        elif isinstance(csvfile, io.IOBase):
            if isinstance(csvfile, io.TextIOBase):
                cls_name = csvfile.__class__.__name__
                raise TypeError('Python 2 compatibility expects byte '
                                'stream, got {0}'.format(cls_name))
        elif isinstance(csvfile, Iterable):
            raise TypeError('iterator input not supported in Python 2')
        else:
            cls_name = csvfile.__class__.__name__
            raise TypeError('unsupported type {0}'.format(cls_name))

        restkey = kwds.pop('restkey', None)
        restval = kwds.pop('restval', None)

        unicode_reader = UnicodeReader(csvfile, encoding=encoding, **kwds)
        return IterDictReader(unicode_reader, fieldnames, cleanup=csvfile.close,
                              restkey=restkey, restval=restval)


def from_csv(file, **kwds):
    """Return a csv.DictReader object which will iterate over lines in
    the given *file*. The *file* can be a file path, file-like object,
    or other object supported by the csv module.
    """
    fieldnames = kwds.pop('fieldnames', None)  # Emulate keyword-only args to
    encoding = kwds.pop('encoding', 'utf-8')   # support Python 2.7 and 2.6.
    return _from_csv(file, fieldnames, encoding, **kwds)


if hasattr(inspect, 'Signature'):  # inspect.Signature() is new in 3.3
    from_csv.__signature__ = inspect.Signature([
        inspect.Parameter('file', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter('fieldnames', inspect.Parameter.KEYWORD_ONLY, default=None),
        inspect.Parameter('encoding', inspect.Parameter.KEYWORD_ONLY, default='UTF-8'),
        inspect.Parameter('kwds', inspect.Parameter.VAR_KEYWORD),
    ])


########################################################################
# Pandas DataFrame Reader.
########################################################################
def from_pandas(df, index=True):
    """Takes a pandas DataFrame and returns a generator that operates
    like a csv.DictReader---it yields rows as OrderedDict objects whose
    keys are derived from the DataFrame's index and column names.
    """
    if index:
        fieldnames = list(df.index.names) + list(df.columns)
    else:
        fieldnames = list(df.columns)

    records = df.to_records(index=index)
    for record in records:
        yield OrderedDict(zip(fieldnames, record))


########################################################################
# MS Excel Reader.
########################################################################
def from_excel(path, worksheet=0):
    """Returns a generator that operates like a csv.DictReader---it
    yields rows as OrderedDict objects whose keys are derived from
    values in the first row of the specified *worksheet*.

    The given *path* must specify an XLSX or XLS file and *worksheet*
    must specify the index or name of the worksheet to load (defaults
    to the first worksheet).

    Load first worksheet::

        source = from_excel('somefile.xlsx')

    Specific worksheets can be loaded by name (a string) or
    index (an integer)::

        source = from_excel('somefile.xlsx', 'Sheet 2')

    .. note::
        This function requires the optional, third-party
        package `xlrd <https://pypi.python.org/pypi/xlrd>`_.
    """
    try:
        import xlrd
    except ImportError:
        raise ImportError(
            "No module named 'xlrd'\n"
            "\n"
            "This is an optional constructor that requires the "
            "third-party library 'xlrd'."
        )

    book = xlrd.open_workbook(path, on_demand=True)
    try:
        if isinstance(worksheet, int):
            sheet = book.sheet_by_index(worksheet)
        else:
            sheet = book.sheet_by_name(worksheet)
        data = (sheet.row(i) for i in range(sheet.nrows))
        data = ([x.value for x in row] for row in data)
        fieldnames = next(data)
        for row in data:
            yield OrderedDict(zip(fieldnames, row))
    finally:
        book.release_resources()


########################################################################
# Function Dispatching.
########################################################################
def get_reader(obj, *args, **kwds):
    """Returns a csv.DictReader or a DictReader-like iterator."""
    if isinstance(obj, string_types):
        if obj.endswith('.csv'):
            return from_csv(obj, *args, **kwds)
        if obj.endswith('.xlsx') or obj.endswith('.xls'):
            return from_excel(obj, *args, **kwds)
        raise TypeError('file {0!r} has no recognized extension'.format(obj))

    if isinstance(obj, io.IOBase) \
            and getattr(obj, 'name', '').endswith('.csv'):
        return from_csv(obj, *args, **kwds)

    if 'pandas' in sys.modules:
        if isinstance(obj, sys.modules['pandas'].DataFrame):
            return from_pandas(obj, *args, **kwds)

    raise TypeError('unsupported type {0}'.format(obj.__class__.__name__))
