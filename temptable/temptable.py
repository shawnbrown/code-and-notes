
import collections
import itertools
import sqlite3


# When not specified, a shared temporary database is used as the default
# connection. For faster insertions and commits, the synchronous flag is
# set to "OFF". Since the database is temporary, long-term integrity
# should not be a concern--in the unlikely event of data corruption, it
# should be entirely acceptable to simply rebuild the temporary tables.
DEFAULT_CONNECTION = sqlite3.connect('')  # <- Using '' makes a temp file.
DEFAULT_CONNECTION.execute('PRAGMA synchronous=OFF')


def table_exists(cursor, table):
    cursor.execute('''
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?

        UNION

        SELECT name
        FROM sqlite_temp_master
        WHERE type='table' AND name=?
    ''', (table, table))
    return bool(cursor.fetchall())


_table_counter = 0
def new_table_name(cursor):
    global _table_counter

    while True:
        new_name = 'tbl{0}'.format(_table_counter)  # Make new name and
        _table_counter += 1                         # iterate counter.

        if not table_exists(cursor, new_name):
            return new_name  # <- Breaks out of the loop.


def normalize_column_names(names):
    def normalize(position, name):
        name = str(name)
        name = name.strip()
        if name == '':
            msg = 'the value in position {0} is empty'.format(position)
            raise ValueError(msg)
        name = name.replace('"', '""')  # Escape quotes.
        return '"{0}"'.format(name)

    return [normalize(pos, nam) for pos, nam in enumerate(names, start=1)]


def create_table(cursor, table, columns):
    """Creates a temporary table using *table* and *columns* names."""
    if table_exists(cursor, table):
        raise ValueError('table named "{0}" already exists'.format(table))

    columns = normalize_column_names(columns)

    # Check for duplicate column names.
    counter = collections.Counter(columns)
    duplicates = [name for name, count in counter.items() if count > 1]
    if duplicates:
        msg = 'expected unique field names, got duplicates: {0}'
        raise ValueError(msg.format(', '.join(duplicates)))

    column_defs = ["{0} DEFAULT ''".format(col) for col in columns]
    column_defs = ', '.join(column_defs)

    statement = 'CREATE TEMPORARY TABLE {0} ({1})'.format(table, column_defs)
    cursor.execute(statement)


def get_columns(cursor, table):
    """Returns list of column names used in table."""
    cursor.execute('PRAGMA table_info({0})'.format(table))
    columns = [x[1] for x in cursor]
    if not columns:
        raise ValueError('table {0!r} does not exist'.format(table))
    return columns


def insert_many(cursor, table, columns, reader):
    parameters = iter(reader)
    if not columns:
        columns = next(parameters, [])
    columns = normalize_column_names(columns)

    sql = 'INSERT INTO {0} ({1}) VALUES ({2})'.format(
        table,
        ', '.join(columns),
        ', '.join(['?'] * len(columns)),
    )
    try:
        cursor.executemany(sql, parameters)
    except sqlite3.ProgrammingError as error:
        if 'incorrect number of bindings' in str(error).lower():
            msg = (
                '{0}\n\nThe reader {1!r} contains some rows with too '
                'few or too many values. Before loading, this data '
                'must be normalized so that each row contains a number '
                'of values equal to the number of columns being loaded.'
            ).format(error, reader)
            error = ValueError(msg)
        raise error


def add_column(cursor, table, column):
    pass


def drop_table(cursor, tablename):
    cursor.execute('DROP TABLE IF EXISTS {0}'.format(tablename))
