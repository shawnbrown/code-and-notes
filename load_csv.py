#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import warnings

from get_reader import get_reader
from temptable.temptable import load_data
from temptable.temptable import savepoint

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)

try:
    file_types = (file, io.IOBase)
except NameError:
    file_types = (io.IOBase,)


def exhaustible(iterable):
    return iter(iterable) is iter(iterable)


preferred_encoding = 'utf-8'
fallback_encoding = ['latin-1']


def load_csv(cursor, table, csvfile, encoding=None, **kwds):
    """Load *csvfile* and insert data into *table*."""
    global preferred_encoding
    global fallback_encoding

    if encoding:
        # When an encoding is specified, use it to load *csvfile* or
        # fail if there are errors (no fallback recovery):
        with savepoint(cursor):
            reader = get_reader.from_csv(csvfile, encoding, **kwds)
            load_data(cursor, table, reader)

        return  # <- EXIT!

    # When the encoding is unspecified, try to load *csvfile* using the
    # preferred encoding and failing that, try the fallback encodings:

    if isinstance(csvfile, file_types) and csvfile.seekable():
        position = csvfile.tell()  # Get current position if
    else:                          # csvfile is file-like and
        position = None            # supports random access.

    try:
        with savepoint(cursor):
            reader = get_reader.from_csv(csvfile, preferred_encoding, **kwds)
            load_data(cursor, table, reader)

        return  # <- EXIT!

    except UnicodeDecodeError as orig_error:
        if exhaustible(csvfile) and position is None:
            encoding, object_, start, end, reason = orig_error.args  # Unpack args.
            reason = (
                '{0}: unable to load {1!r}, cannot attempt fallback with '
                '{2!r} type: must specify an appropriate text encoding'
            ).format(reason, csvfile, csvfile.__class__.__name__)
            raise UnicodeDecodeError(encoding, object_, start, end, reason)

        if isinstance(fallback_encoding, list):
            fallback_list = fallback_encoding
        else:
            fallback_list = [fallback_encoding]

        for fallback in fallback_list:
            if position is not None:
                csvfile.seek(position)

            try:
                with savepoint(cursor):
                    reader = get_reader.from_csv(csvfile, fallback, **kwds)
                    load_data(cursor, table, reader)

                msg = (
                    '{0}: loaded {1!r} using fallback {2!r}: specify an '
                    'appropriate text encoding to assure correct operation'
                ).format(orig_error, csvfile, fallback)
                warnings.warn(msg)

                return  # <- EXIT!

            except UnicodeDecodeError:
                pass

        # Note: DO NOT refactor this section using a for-else. I swear...
        encoding, object_, start, end, reason = orig_error.args  # Unpack args.
        reason = (
            '{0}: unable to load {1!r}, fallback recovery unsuccessful: '
            'must specify an appropriate text encoding'
        ).format(reason, csvfile)
        raise UnicodeDecodeError(encoding, object_, start, end, reason)


if __name__ == '__main__':
    import io
    import sqlite3
    import sys
    import unittest

    PY2 = sys.version_info[0] == 2

    try:
        chr = unichr
    except NameError:
        pass


    class TestLoadCsv(unittest.TestCase):
        def setUp(self):
            connection = sqlite3.connect(':memory:')
            connection.execute('PRAGMA synchronous=OFF')
            connection.isolation_level = None
            self.cursor = connection.cursor()

        @staticmethod
        def get_stream(string, encoding=None):
            """Accepts a string and returns a file-like stream object.

            In Python 2, Unicode files should be opened in binary-mode
            but in Python 3, they should be opened in text-mode. This
            function emulates the appropriate opening behavior.
            """
            fh = io.BytesIO(string)
            if PY2:
                return fh
            return io.TextIOWrapper(fh, encoding=encoding)

        def test_encoding_with_stream(self):
            csvfile = self.get_stream((
                b'col1,col2\n'
                b'1,\xe6\n'  # '\xe6' -> æ (ash)
                b'2,\xf0\n'  # '\xf0' -> ð (eth)
                b'3,\xfe\n'  # '\xfe' -> þ (thorn)
            ), encoding='latin-1')
            load_csv(self.cursor, 'testtable1', csvfile, encoding='latin-1')

            expected = [
                ('1', chr(0xe6)),  # chr(0xe6) -> æ
                ('2', chr(0xf0)),  # chr(0xf0) -> ð
                ('3', chr(0xfe)),  # chr(0xfe) -> þ
            ]
            self.cursor.execute('SELECT col1, col2 FROM testtable1')
            self.assertEqual(list(self.cursor), expected)

        def test_encoding_with_file(self):
            path = 'get_reader/sample_text_iso88591.csv'
            load_csv(self.cursor, 'testtable', path, encoding='latin-1')

            expected = [
                ('iso88591', chr(0xe6)),  # chr(0xe6) -> æ
            ]
            self.cursor.execute('SELECT col1, col2 FROM testtable')
            self.assertEqual(list(self.cursor), expected)

        def test_encoding_mismatch(self):
            path = 'get_reader/sample_text_iso88591.csv'
            wrong_encoding = 'utf-8'  # <- Doesn't match file.

            with self.assertRaises(UnicodeDecodeError):
                load_csv(self.cursor, 'testtable', path, wrong_encoding)

        def test_fallback_with_stream(self):
            with warnings.catch_warnings(record=True):  # Catch warnings issued
                csvfile = self.get_stream((             # when running Python 2.
                    b'col1,col2\n'
                    b'1,\xe6\n'  # '\xe6' -> æ (ash)
                    b'2,\xf0\n'  # '\xf0' -> ð (eth)
                    b'3,\xfe\n'  # '\xfe' -> þ (thorn)
                ), encoding='latin-1')
                load_csv(self.cursor, 'testtable1', csvfile)  # <- No encoding arg.

            expected = [
                ('1', chr(0xe6)),  # chr(0xe6) -> æ
                ('2', chr(0xf0)),  # chr(0xf0) -> ð
                ('3', chr(0xfe)),  # chr(0xfe) -> þ
            ]
            self.cursor.execute('SELECT col1, col2 FROM testtable1')
            self.assertEqual(list(self.cursor), expected)

        def test_fallback_with_file(self):
            with warnings.catch_warnings(record=True) as warning_list:
                warnings.simplefilter('always')
                path = 'get_reader/sample_text_iso88591.csv'
                load_csv(self.cursor, 'testtable', path)  # <- No encoding arg.

            self.assertEqual(len(warning_list), 1)
            expected = "using fallback 'latin-1'"
            self.assertIn(expected, str(warning_list[0].message))

            expected = [
                ('iso88591', chr(0xe6)),  # chr(0xe6) -> æ
            ]
            self.cursor.execute('SELECT col1, col2 FROM testtable')
            self.assertEqual(list(self.cursor), expected)

        def test_fallback_with_exhaustible_object(self):
            """Exhaustible iterators and unseekable file-like objects
            can only be iterated over once. This means that the usual
            fallback behavior can not be applied and the function must
            raise an exception.
            """
            if not PY2:
                return

            csvfile = self.get_stream((
                b'col1,col2\n'
                b'1,\xe6\n'  # '\xe6' -> æ (ash)
                b'2,\xf0\n'  # '\xf0' -> ð (eth)
                b'3,\xfe\n'  # '\xfe' -> þ (thorn)
            ), encoding='latin-1')
            generator = (x for x in csvfile)  # <- Make stream unseekable.

            with self.assertRaises(UnicodeDecodeError) as cm:
                load_csv(self.cursor, 'testtable', generator)

            error_message = str(cm.exception)
            self.assertIn('cannot attempt fallback', error_message.lower())


    unittest.main()
