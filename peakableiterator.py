# -*- coding: utf-8 -*-
try:
    from collections.abc import Iterator
except ImportError:
    from collections import Iterator


_empty = object()


class PeekableIterator(Iterator):
    """An iterator that can lookahead by one element."""
    def __init__(self, iterable):
        if isinstance(iterable, self.__class__):
            self._iterator = iterable._iterator
            self._buffer = iterable._buffer
        else:
            self._iterator = iter(iterable)
            self._buffer = _empty

    def __iter__(self):
        return self

    def __next__(self):
        if self._buffer is _empty:
            return next(self._iterator)
        else:
            value = self._buffer
            self._buffer = _empty
            return value

    def next(self):  # For Python 2.
        return self.__next__()

    def peek(self):
        """Returns the next value or raises StopIteration."""
        if self._buffer is _empty:
            self._buffer = next(self._iterator)
        return self._buffer

    def has_next(self):
        """Returns True if iterator is not yet exhausted."""
        try:
            self.peek()
        except StopIteration:
            return False
        return True
