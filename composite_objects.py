#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections.abc import Sequence
from collections.abc import Mapping


class SequenceComposite(Sequence):
    """A container to treat a group of objects as a single object.

    Method calls and property references are passed to the individual
    objects and a new SequenceComposite is returned that contains the
    results::

        >>> group = SequenceComposite('foo', 'bar')
        >>> group.upper()
        SequenceComposite('FOO', 'BAR')

    SequenceComposite is a well-behaved sequence and individual items
    can be accessed by index, iteration, or sequence unpacking. Below,
    the individual items are unpacked into separate variables::

        >>> group = SequenceComposite('foo', 'bar')
        >>> group = group.upper()
        >>> x, y = group
    """
    def __init__(self, obj, *objs):
        self._objs = (obj,) + objs

    def __getitem__(self, index):
        return self._objs[index]

    def __len__(self):
        return len(self._objs)


class MappingComposite(Mapping):
    pass


if __name__ == '__main__':
    import unittest


    class TestSequenceComposite(unittest.TestCase):
        def test_instantiation(self):
            composite = SequenceComposite('foo', 'bar')
            self.assertIsInstance(composite, Sequence)


    unittest.main()
