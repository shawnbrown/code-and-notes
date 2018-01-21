
import sqlite3


DEFAULT_CONNECTION = sqlite3.connect('')  # <- Using '' for temp file.


def create_table(cursor, tablename, columns):
    pass


def add_column(cursor, tablename, column):
    pass


def insert_values(cursor, tablename, reader, columns=None):
    pass


class TemporaryTable(object)
    def __init__(reader, columns=None, connection=None):
        pass
