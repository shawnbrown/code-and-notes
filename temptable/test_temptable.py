
import sqlite3
import unittest

import temptable
from temptable import table_exists
from temptable import new_table_name
from temptable import normalize_names
from temptable import create_table
from temptable import get_columns
from temptable import insert_many
from temptable import add_columns



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
        temptable._table_counter = 0  # Reset internal counter.
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


class TestInsertMany(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def test_basic_insert(self):
        cursor = self.cursor

        cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        data = [
            ('x', 1),
            ('y', 2),
        ]
        insert_many(cursor, 'test_table', ['A', 'B'], data)

        cursor.execute('SELECT * FROM test_table')
        results = cursor.fetchall()

        self.assertEqual(results, data)

    def test_reordered_columns(self):
        cursor = self.cursor

        cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        data = [
            (1, 'x'),
            (2, 'y'),
        ]
        columns = ['B', 'A']  # <- Column order doesn't match how table was created.
        insert_many(cursor, 'test_table', columns, data)

        cursor.execute('SELECT * FROM test_table')
        results = cursor.fetchall()

        expected = [
            ('x', 1),
            ('y', 2),
        ]
        self.assertEqual(results, expected)

    def test_wrong_number_of_records(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')

        too_few = [('x',), ('y',)]
        with self.assertRaises(sqlite3.ProgrammingError):
            insert_many(self.cursor, 'test_table', ['A', 'B'], too_few)

        too_many = [('x', 1, 'foo'), ('y', 2, 'bar')]
        with self.assertRaises(sqlite3.ProgrammingError):
            insert_many(self.cursor, 'test_table', ['A', 'B'], too_many)

    def test_no_data(self):
        cursor = self.cursor

        cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        data = iter([])  # <- Empty, no data.
        insert_many(cursor, 'test_table', ['A', 'B'], data)

        cursor.execute('SELECT * FROM test_table')
        results = cursor.fetchall()

        self.assertEqual(results, [])

    def test_sqlite3_errors(self):
        """Sqlite errors should not be caught."""
        # No such table.
        with self.assertRaises(sqlite3.OperationalError):
            data = [('x', 1), ('y', 2)]
            insert_many(self.cursor, 'missing_table', ['A', 'B'], data)

        # No column named X.
        with self.assertRaises(sqlite3.OperationalError):
            self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
            data = [('a', 1), ('b', 2)]
            insert_many(self.cursor, 'test_table', ['X', 'B'], data)


class TestAddColuns(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(':memory:')
        self.cursor = connection.cursor()

    def test_new_columns(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        add_columns(self.cursor, 'test_table', ['C', 'D'])

        columns = get_columns(self.cursor, 'test_table')
        self.assertEqual(columns, ['A', 'B', 'C', 'D'])

    def test_existing_columns(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        add_columns(self.cursor, 'test_table', ['A', 'B', 'C', 'D'])

        columns = get_columns(self.cursor, 'test_table')
        self.assertEqual(columns, ['A', 'B', 'C', 'D'])

    def test_ordering_behavior(self):
        self.cursor.execute('CREATE TEMPORARY TABLE test_table ("A", "B")')
        add_columns(self.cursor, 'test_table', ['B', 'C', 'A', 'D'])

        # Columns A and B already exist in a specified order and
        # the new columns ('C' and 'D') are added in the order in
        # which they are encountered.
        columns = get_columns(self.cursor, 'test_table')
        self.assertEqual(columns, ['A', 'B', 'C', 'D'])


if __name__ == '__main__':
    unittest.main()
