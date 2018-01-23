
import sqlite3
import unittest

import temptable
from temptable import table_exists
from temptable import new_table_name
from temptable import normalize_column_names
from temptable import create_table
from temptable import get_columns


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


class TestNormalizeColumnNames(unittest.TestCase):
    def test_simple_case(self):
        normalized = normalize_column_names(['A', 'B'])
        expected = ['"A"', '"B"']
        self.assertEqual(normalized, expected)

    def test_non_strings(self):
        normalized = normalize_column_names([1, 2.5])
        expected = ['"1"', '"2.5"']
        self.assertEqual(normalized, expected)

    def test_whitespace(self):
        normalized = normalize_column_names(['  A  ', '  B  '])
        expected = ['"A"', '"B"']
        self.assertEqual(normalized, expected)

    def test_empty_values(self):
        with self.assertRaises(ValueError):
            normalize_column_names([''])  # <- Empty string.

        with self.assertRaises(ValueError):
            normalize_column_names(['     '])  # <- All whitespace.

    def test_quotes(self):
        normalized = normalize_column_names(['x "y"'])
        expected = ['"x ""y"""']  # Escaped by doubling '"' -> '""'
        self.assertEqual(normalized, expected)


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
        create_table(self.cursor, 'test_table', ['A', 'B'])
        self.cursor.execute("INSERT INTO test_table (A) VALUES ('foo')")
        self.cursor.execute("INSERT INTO test_table (B) VALUES ('bar')")

        self.cursor.execute('SELECT * FROM test_table')
        expected = [
            ('foo', ''),  # <- Default in column B
            ('', 'bar'),  # <- Default in column A
        ]
        self.assertEqual(self.cursor.fetchall(), expected)

    def test_table_already_exists(self):
        create_table(self.cursor, 'test_table', ['A', 'B'])

        with self.assertRaises(ValueError):
            create_table(self.cursor, 'test_table', ['A', 'B'])

    def test_duplicate_columns(self):
        with self.assertRaises(ValueError):
            create_table(self.cursor, 'test_table1', ['A', 'B', 'A'])

        with self.assertRaises(ValueError):
            create_table(self.cursor, 'test_table2', ['A', 'B', '  A  '])


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
        with self.assertRaises(ValueError):
            columns = get_columns(self.cursor, 'missing_table')


class TestInsertMany(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
