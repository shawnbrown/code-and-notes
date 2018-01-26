
import itertools
import sqlite3
import unittest

import temptable
from temptable import table_exists
from temptable import new_table_name
from temptable import normalize_names
from temptable import create_table
from temptable import get_columns
from temptable import insert_records
from temptable import alter_table
from temptable import drop_table
from temptable import savepoint


class TestTableExists(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def test_empty_database(self):
        self.assertFalse(table_exists(self.cursor, 'table_a'))

    def test_persistent_table(self):
        self.cursor.execute('CREATE TABLE table_b (col1, col2)')
        self.assertTrue(table_exists(self.cursor, 'table_b'))

    def test_temporary_table(self):
        self.cursor.execute('CREATE TEMPORARY TABLE table_c (col1, col2)')
        self.assertTrue(table_exists(self.cursor, 'table_c'))


class TestNewTableName(unittest.TestCase):
    def setUp(self):
        # Rebuild internal generator.
        temptable._table_names = ('tbl{0}'.format(x) for x in itertools.count())

        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def test_empty_database(self):
        table_name = new_table_name(self.cursor)
        self.assertEqual(table_name, 'tbl0')

    def test_existing_temptable(self):
        self.cursor.execute('CREATE TEMPORARY TABLE tbl0 (col1, col2)')
        table_name = new_table_name(self.cursor)
        self.assertEqual(table_name, 'tbl1')

    def test_existing_table_and_temptable(self):
        self.cursor.execute('CREATE TABLE tbl0 (col1, col2)')
        self.cursor.execute('CREATE TEMPORARY TABLE tbl1 (col1, col2)')
        table_name = new_table_name(self.cursor)
        self.assertEqual(table_name, 'tbl2')


class TestNormalizeNames(unittest.TestCase):
    def test_single_value(self):
        normalized = normalize_names('A')
        self.assertEqual(normalized, '"A"')

    def test_list_of_values(self):
        normalized = normalize_names(['A', 'B'])
        expected = ['"A"', '"B"']
        self.assertEqual(normalized, expected)

    def test_non_strings(self):
        normalized = normalize_names(2.5)
        self.assertEqual(normalized, '"2.5"')

    def test_whitespace(self):
        normalized = normalize_names('  A  ')
        self.assertEqual(normalized, '"A"')

        normalized = normalize_names('    ')
        self.assertEqual(normalized, '""')

    def test_quote_escaping(self):
        normalized = normalize_names('Steve "The Woz" Wozniak')
        self.assertEqual(normalized, '"Steve ""The Woz"" Wozniak"')


class TestCreateTable(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def count_tables(self):  # <- Heper function.
        self.cursor.execute('''
            SELECT COUNT(*)
            FROM sqlite_temp_master
            WHERE type='table'
        ''')
        return self.cursor.fetchone()[0]

    def test_basic_creation(self):
        self.assertEqual(self.count_tables(), 0, msg='starting with zero tables')

        create_table(self.cursor, 'test_table1', ['A', 'B'])  # <- Create table!
        self.assertEqual(self.count_tables(), 1, msg='one table')

        create_table(self.cursor, 'test_table2', ['A', 'B'])  # <- Create table!
        self.assertEqual(self.count_tables(), 2, msg='two tables')

    def test_default_value(self):
        # When unspecified, default is empty string.
        create_table(self.cursor, 'test_table1', ['A', 'B'])
        self.cursor.execute("INSERT INTO test_table1 (A) VALUES ('foo')")
        self.cursor.execute("INSERT INTO test_table1 (B) VALUES ('bar')")

        self.cursor.execute('SELECT * FROM test_table1')
        expected = [
            ('foo', ''),  # <- Default in column B
            ('', 'bar'),  # <- Default in column A
        ]
        self.assertEqual(self.cursor.fetchall(), expected)

        # Setting default to None.
        create_table(self.cursor, 'test_table2', ['A', 'B'], default=None)
        self.cursor.execute("INSERT INTO test_table2 (A) VALUES ('foo')")
        self.cursor.execute("INSERT INTO test_table2 (B) VALUES ('bar')")

        self.cursor.execute('SELECT * FROM test_table2')
        expected = [
            ('foo', None),  # <- Default in column B
            (None, 'bar'),  # <- Default in column A
        ]
        self.assertEqual(self.cursor.fetchall(), expected)

    def test_sqlite3_errors(self):
        """Sqlite errors should not be caught."""
        # Table already exists.
        create_table(self.cursor, 'test_table1', ['A', 'B'])
        with self.assertRaises(sqlite3.OperationalError):
            create_table(self.cursor, 'test_table1', ['A', 'B'])

        # Duplicate column name.
        with self.assertRaises(sqlite3.OperationalError):
            create_table(self.cursor, 'test_table2', ['A', 'B', 'A'])

        # Duplicate column name (after normalization).
        with self.assertRaises(sqlite3.OperationalError):
            create_table(self.cursor, 'test_table3', ['A', 'B', '  A  '])

        # Duplicate empty/all-whitespace string columns (uses modified message).
        with self.assertRaises(sqlite3.OperationalError) as cm:
            create_table(self.cursor, 'test_table4', ['', 'B', '    '])


class TestGetColumns(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def test_get_columns(self):
        self.cursor.execute('CREATE TABLE test1 ("A", "B")')
        columns = get_columns(self.cursor, 'test1')
        self.assertEqual(columns, ['A', 'B'])

        self.cursor.execute('CREATE TEMPORARY TABLE test2 ("C", "D")')
        columns = get_columns(self.cursor, 'test2')
        self.assertEqual(columns, ['C', 'D'])

    def test_missing_table(self):
        with self.assertRaises(sqlite3.ProgrammingError):
            columns = get_columns(self.cursor, 'missing_table')


class TestInsertRecords(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def test_basic_insert(self):
        cursor = self.cursor

        cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        records = [
            ('x', 1),
            ('y', 2),
        ]
        insert_records(cursor, 'test_table', ['A', 'B'], records)

        cursor.execute('SELECT * FROM test_table')
        results = cursor.fetchall()

        self.assertEqual(results, records)

    def test_reordered_columns(self):
        cursor = self.cursor

        cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        records = [
            (1, 'x'),
            (2, 'y'),
        ]
        columns = ['B', 'A']  # <- Column order doesn't match how table was created.
        insert_records(cursor, 'test_table', columns, records)

        cursor.execute('SELECT * FROM test_table')
        results = cursor.fetchall()

        expected = [
            ('x', 1),
            ('y', 2),
        ]
        self.assertEqual(results, expected)

    def test_wrong_number_of_values(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')

        too_few = [('x',), ('y',)]
        with self.assertRaises(sqlite3.ProgrammingError):
            insert_records(self.cursor, 'test_table', ['A', 'B'], too_few)

        too_many = [('x', 1, 'foo'), ('y', 2, 'bar')]
        with self.assertRaises(sqlite3.ProgrammingError):
            insert_records(self.cursor, 'test_table', ['A', 'B'], too_many)

    def test_no_records(self):
        cursor = self.cursor

        cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        records = iter([])  # <- Empty, no data.
        insert_records(cursor, 'test_table', ['A', 'B'], records)

        cursor.execute('SELECT * FROM test_table')
        results = cursor.fetchall()

        self.assertEqual(results, [])

    def test_sqlite3_errors(self):
        """Sqlite errors should not be caught."""
        # No such table.
        with self.assertRaises(sqlite3.OperationalError):
            records = [('x', 1), ('y', 2)]
            insert_records(self.cursor, 'missing_table', ['A', 'B'], records)

        # No column named X.
        with self.assertRaises(sqlite3.OperationalError):
            self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
            records = [('a', 1), ('b', 2)]
            insert_records(self.cursor, 'test_table', ['X', 'B'], records)


class TestAlterTable(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def test_new_columns(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        alter_table(self.cursor, 'test_table', ['C', 'D'])

        columns = get_columns(self.cursor, 'test_table')
        self.assertEqual(columns, ['A', 'B', 'C', 'D'])

    def test_existing_columns(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        alter_table(self.cursor, 'test_table', ['A', 'B', 'C', 'D'])

        columns = get_columns(self.cursor, 'test_table')
        self.assertEqual(columns, ['A', 'B', 'C', 'D'])

    def test_ordering_behavior(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        alter_table(self.cursor, 'test_table', ['B', 'C', 'A', 'D'])

        # Columns A and B already exist in a specified order and
        # the new columns ('C' and 'D') are added in the order in
        # which they are encountered.
        columns = get_columns(self.cursor, 'test_table')
        self.assertEqual(columns, ['A', 'B', 'C', 'D'])


class TestDropTable(unittest.TestCase):
    def test_drop_table(self):
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()

        cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        self.assertTrue(table_exists(cursor, 'test_table'))

        drop_table(cursor, 'test_table')  # <- Drop table!
        self.assertFalse(table_exists(cursor, 'test_table'))


class TestSavepoint(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        connection.isolation_level = None
        self.cursor = connection.cursor()

    def test_transaction_status(self):
        connection = self.cursor.connection
        if not hasattr(connection, 'in_transaction'):  # New in 3.2.
            return

        self.assertFalse(connection.in_transaction)
        with savepoint(self.cursor):
            self.assertTrue(connection.in_transaction)
        self.assertFalse(connection.in_transaction)

    def test_release(self):
        cursor = self.cursor

        with savepoint(cursor):
            cursor.execute('CREATE TEMPORARY TABLE test_table ("A")')
            cursor.execute("INSERT INTO test_table VALUES ('one')")
            cursor.execute("INSERT INTO test_table VALUES ('two')")
            cursor.execute("INSERT INTO test_table VALUES ('three')")

        cursor.execute('SELECT * FROM test_table')
        self.assertEqual(cursor.fetchall(), [('one',), ('two',), ('three',)])

    def test_nested_releases(self):
        cursor = self.cursor

        with savepoint(cursor):
            cursor.execute('CREATE TEMPORARY TABLE test_table ("A")')
            cursor.execute("INSERT INTO test_table VALUES ('one')")
            with savepoint(cursor):  # <- Nested!
                cursor.execute("INSERT INTO test_table VALUES ('two')")
            cursor.execute("INSERT INTO test_table VALUES ('three')")

        cursor.execute('SELECT * FROM test_table')
        self.assertEqual(cursor.fetchall(), [('one',), ('two',), ('three',)])

    def test_rollback(self):
        cursor = self.cursor

        with savepoint(cursor):  # <- Released.
            cursor.execute('CREATE TEMPORARY TABLE test_table ("A")')

        try:
            with savepoint(cursor):  # <- Rolled back!
                cursor.execute("INSERT INTO test_table VALUES ('one')")
                cursor.execute("INSERT INTO test_table VALUES ('two')")
                cursor.execute("INSERT INTO missing_table VALUES ('three')")  # <- Bad table.
        except sqlite3.OperationalError:
            pass

        cursor.execute('SELECT * FROM test_table')
        self.assertEqual(cursor.fetchall(), [], 'Table should exist but contain no records.')

    def test_nested_rollback(self):
        cursor = self.cursor

        with savepoint(cursor):  # <- Released.
            cursor.execute('CREATE TEMPORARY TABLE test_table ("A")')
            cursor.execute("INSERT INTO test_table VALUES ('one')")
            try:
                with savepoint(cursor):  # <- Nested rollback!
                    cursor.execute("INSERT INTO test_table VALUES ('two')")
                    raise Exception()
            except Exception:
                pass
            cursor.execute("INSERT INTO test_table VALUES ('three')")

        cursor.execute('SELECT * FROM test_table')
        self.assertEqual(cursor.fetchall(), [('one',), ('three',)])

    def test_bad_isolation_level(self):
        connection = sqlite3.connect(':memory:')
        connection.isolation_level = 'DEFERRED'  # <- Expects None/autocommit!
        cursor = connection.cursor()

        with self.assertRaises(ValueError):
            with savepoint(cursor):
                pass


if __name__ == '__main__':
    unittest.main()
