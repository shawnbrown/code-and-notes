#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import io
import os
import sys
import unittest

try:
    import pandas
except ImportError:
    pandas = None

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import dbfread
except ImportError:
    dbfread = None


from get_reader import _dict_generator
from get_reader import _from_csv_iterable
from get_reader import _from_csv_path
#from get_reader import from_csv
from get_reader import from_pandas
from get_reader import from_excel
from get_reader import from_dbf
from get_reader import get_reader


PY2 = sys.version_info[0] == 2


try:
    chr = unichr
except NameError:
    pass

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def get_stream(string, encoding=None):
    """Test-helper to return file-like object for *string* data.

    In Python 2, Unicode files should be opened in binary-mode but
    in Python 3, they should be opened in text-mode. This function
    emulates the appropriate mode using the file-like stream objects.
    """
    fh = io.BytesIO(string)
    if PY2:
        return fh
    return io.TextIOWrapper(fh, encoding=encoding)


class TestDictGenerator(unittest.TestCase):
    def test_defaults(self):
        """A _dict_generator() should yield the same values as an
        actual csv.DictReader instance.
        """
        iterable = [
            'col1,col2',  # This iterable should yield the following rows:
            '1,a',        #   {'col1': '1', 'col2': 'a'},
            '2,b,x',      #   {'col1': '2', 'col2': 'b', None: ['x']},
            '3',          #   {'col1': '3', 'col2': None}
        ]
        generator = _dict_generator(csv.reader(iterable))
        dict_reader = csv.DictReader(iterable)  # <- Reference implementation.
        self.assertEqual(list(generator), list(dict_reader))


class TestFromCsvIterable(unittest.TestCase):
    """Test Unicode CSV support.

    Calling _from_csv_iterable() on Python 2 uses the UnicodeReader
    and UTF8Recoder classes internally for consistent behavior across
    versions.
    """
    def test_ascii(self):
        stream = get_stream((
            b'col1,col2\n'
            b'1,a\n'
            b'2,b\n'
            b'3,c\n'
        ), encoding='ascii')

        reader = _from_csv_iterable(stream, encoding='ascii')
        expected = [
            {'col1': '1', 'col2': 'a'},
            {'col1': '2', 'col2': 'b'},
            {'col1': '3', 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

    def test_iso88591(self):
        stream = get_stream((
            b'col1,col2\n'
            b'1,\xe6\n'  # '\xe6' -> æ (ash)
            b'2,\xf0\n'  # '\xf0' -> ð (eth)
            b'3,\xfe\n'  # '\xfe' -> þ (thorn)
        ), encoding='iso8859-1')

        reader = _from_csv_iterable(stream, encoding='iso8859-1')
        expected = [
            {'col1': '1', 'col2': chr(0xe6)},  # chr(0xe6) -> æ
            {'col1': '2', 'col2': chr(0xf0)},  # chr(0xf0) -> ð
            {'col1': '3', 'col2': chr(0xfe)},  # chr(0xfe) -> þ
        ]
        self.assertEqual(list(reader), expected)

    def test_utf8(self):
        stream = get_stream((
            b'col1,col2\n'
            b'1,\xce\xb1\n'          # '\xce\xb1'         -> α (Greek alpha)
            b'2,\xe0\xa5\x90\n'      # '\xe0\xa5\x90'     -> ॐ (Devanagari Om)
            b'3,\xf0\x9d\x94\xb8\n'  # '\xf0\x9d\x94\xb8' -> 𝔸 (mathematical double-struck A)
        ), encoding='utf-8')

        reader = _from_csv_iterable(stream, encoding='utf-8')
        expected = [
            {'col1': '1', 'col2': chr(0x003b1)},  # chr(0x003b1) -> α
            {'col1': '2', 'col2': chr(0x00950)},  # chr(0x00950) -> ॐ
            {'col1': '3', 'col2': chr(0x1d538)},  # chr(0x1d538) -> 𝔸
        ]
        self.assertEqual(list(reader), expected)

    def test_bad_types(self):
        bytes_literal = (
            b'col1,col2\n'
            b'1,a\n'
            b'2,b\n'
            b'3,c\n'
        )
        if PY2:
            bytes_stream = io.BytesIO(bytes_literal)
            text_stream = io.TextIOWrapper(bytes_stream, encoding='ascii')
            with self.assertRaises(TypeError):
                reader = _from_csv_iterable(text_stream, 'ascii')
        else:
            bytes_stream = io.BytesIO(bytes_literal)
            with self.assertRaises((csv.Error, TypeError)):
                reader = _from_csv_iterable(bytes_stream, 'ascii')
                list(reader)  # Trigger evaluation.

    def test_empty_file(self):
        stream = get_stream(b'', encoding='ascii')
        reader = _from_csv_iterable(stream, encoding='ascii')
        expected = []
        self.assertEqual(list(reader), expected)


class TestFromCsvPath(unittest.TestCase):
    def test_utf8(self):
        reader = _from_csv_path('sample_text_utf8.csv', encoding='utf-8')
        expected = [
            {'col1': 'utf8', 'col2': chr(0x003b1)},  # chr(0x003b1) -> α
        ]
        self.assertEqual(list(reader), expected)

    def test_iso88591(self):
        reader = _from_csv_path('sample_text_iso88591.csv', encoding='iso8859-1')
        expected = [
            {'col1': 'iso88591', 'col2': chr(0xe6)},  # chr(0xe6) -> æ
        ]
        self.assertEqual(list(reader), expected)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            reader = _from_csv_path('missing_file.csv', encoding='iso8859-1')
            list(reader)  # Trigger evaluation.


@unittest.skipIf(not pandas, 'pandas not found')
class TestFromPandas(unittest.TestCase):
    def setUp(self):
        self.df = pandas.DataFrame({
            'col1': (1, 2, 3),
            'col2': ('a', 'b', 'c'),
        })

    def test_automatic_indexing(self):
        reader = from_pandas(self.df)  # <- Includes index by default.
        expected = [
            {None: 0, 'col1': 1, 'col2': 'a'},
            {None: 1, 'col1': 2, 'col2': 'b'},
            {None: 2, 'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

        reader = from_pandas(self.df, index=False)  # <- Omits index.
        expected = [
            {'col1': 1, 'col2': 'a'},
            {'col1': 2, 'col2': 'b'},
            {'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

    def test_simple_index(self):
        self.df.index = pandas.Index(['x', 'y', 'z'], name='col0')

        reader = from_pandas(self.df)
        expected = [
            {'col0': 'x', 'col1': 1, 'col2': 'a'},
            {'col0': 'y', 'col1': 2, 'col2': 'b'},
            {'col0': 'z', 'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

        reader = from_pandas(self.df, index=False)
        expected = [
            {'col1': 1, 'col2': 'a'},
            {'col1': 2, 'col2': 'b'},
            {'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

    def test_multiindex(self):
        index_values = [('x', 'one'), ('x', 'two'), ('y', 'three')]
        index = pandas.MultiIndex.from_tuples(index_values, names=['A', 'B'])
        self.df.index = index

        reader = from_pandas(self.df)
        expected = [
            {'A': 'x', 'B': 'one',   'col1': 1, 'col2': 'a'},
            {'A': 'x', 'B': 'two',   'col1': 2, 'col2': 'b'},
            {'A': 'y', 'B': 'three', 'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

        reader = from_pandas(self.df, index=False)
        expected = [
            {'col1': 1, 'col2': 'a'},
            {'col1': 2, 'col2': 'b'},
            {'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)


@unittest.skipIf(not xlrd, 'xlrd not found')
class TestFromExcel(unittest.TestCase):
    def setUp(self):
        dirname = os.path.dirname(__file__)
        self.filepath = os.path.join(dirname, 'sample_multiworksheet.xlsx')

    def test_default_worksheet(self):
        reader = from_excel(self.filepath)  # <- Defaults to 1st worksheet.

        expected = [
            {'col1': 1, 'col2': 'a'},
            {'col1': 2, 'col2': 'b'},
            {'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

    def test_specified_worksheet(self):
        reader = from_excel(self.filepath, 'Sheet2')  # <- Specified worksheet.

        expected = [
            {'col1': 4, 'col2': 'd'},
            {'col1': 5, 'col2': 'e'},
            {'col1': 6, 'col2': 'f'},
        ]
        self.assertEqual(list(reader), expected)


@unittest.skipIf(not dbfread, 'dbfread not found')
class TestFromDbf(unittest.TestCase):
    def test_dbf(self):
        dirname = os.path.dirname(__file__)
        filepath = os.path.join(dirname, 'sample_dbase.dbf')

        reader = from_dbf(filepath)
        expected = [
            {'COL1': 'dBASE', 'COL2': 1},
        ]
        self.assertEqual(list(reader), expected)


class TestFunctionDispatching(unittest.TestCase):
    def setUp(self):
        self._orig_dir = os.getcwd()
        os.chdir(os.path.dirname(__file__) or '.')

        def restore_dir():
            os.chdir(self._orig_dir)
        self.addCleanup(restore_dir)

    def test_csv(self):
        reader = get_reader('sample_text_utf8.csv', encoding='utf-8')
        expected = [
            {'col1': 'utf8', 'col2': chr(0x003b1)},  # chr(0x003b1) -> α
        ]
        self.assertEqual(list(reader), expected)

        reader = get_reader('sample_text_iso88591.csv', encoding='iso8859-1')
        expected = [
            {'col1': 'iso88591', 'col2': chr(0xe6)},  # chr(0xe6) -> æ
        ]
        self.assertEqual(list(reader), expected)

        path = 'sample_text_utf8.csv'
        encoding = 'utf-8'
        if PY2:
            fh = io.open(path, 'rb')
        else:
            fh = open(path, 'rt', encoding=encoding, newline='')

        with fh:
            reader = get_reader(fh, encoding=encoding)
            expected = [
                {'col1': 'utf8', 'col2': chr(0x003b1)},  # chr(0x003b1) -> α
            ]
            self.assertEqual(list(reader), expected)

    @unittest.skipIf(not xlrd, 'xlrd not found')
    def test_excel(self):
        reader = get_reader('sample_excel2007.xlsx')
        expected = [
            {'col1': 'excel2007', 'col2': 1},
        ]
        self.assertEqual(list(reader), expected)

        reader = get_reader('sample_excel1997.xls')
        expected = [
            {'col1': 'excel1997', 'col2': 1},
        ]
        self.assertEqual(list(reader), expected)

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_pandas(self):
        df = pandas.DataFrame({
            'col1': (1, 2, 3),
            'col2': ('a', 'b', 'c'),
        })
        reader = get_reader(df, index=False)
        expected = [
            {'col1': 1, 'col2': 'a'},
            {'col1': 2, 'col2': 'b'},
            {'col1': 3, 'col2': 'c'},
        ]
        self.assertEqual(list(reader), expected)

    @unittest.skipIf(not dbfread, 'dbfread not found')
    def test_dbf(self):
        reader = get_reader('sample_dbase.dbf')
        expected = [
            {'COL1': 'dBASE', 'COL2': 1},
        ]
        self.assertEqual(list(reader), expected)

    def test_unidentifiable_type(self):
        with self.assertRaises(TypeError):
            obj = object()
            reader = get_reader(obj)


if __name__ == '__main__':
    unittest.main()
