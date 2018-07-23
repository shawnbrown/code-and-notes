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
    """A container to treat a group of objects as a single object.

    Method calls and property references are passed to the individual
    values and a new MappingComposite is returned that contains the
    resulting values associated with the original keys::

        >>> group = MappingComposite({'x': 'foo', 'y': 'bar'})
        >>> group.upper()
        MappingComposite({'x': 'FOO', 'y': 'BAR'})

    MappingComposite is a well-behaved mapping and its contents can
    be accessed by obj[key] or calls to keys(), values() or items()
    methods::

        >>> group = MappingComposite({'x': 'foo', 'y': 'bar'})
        >>> group = group.upper()
        >>> x = group['x']
        >>> y = group['y']
    """
    def __init__(self, obj=None, **kwds):
        if not (obj or kwds):
            cls_name = self.__class__.__name__
            raise TypeError('{0} requires at least 1 item'.format(cls_name))

        if obj:
            self._objs = dict(obj, **kwds)
        else:
            self._objs = dict(**kwds)

    def __getitem__(self, key):
        return self._objs[key]

    def __iter__(self):
        return iter(self._objs)

    def __len__(self):
        return len(self._objs)


if __name__ == '__main__':
    import unittest


    class TestSequenceComposite(unittest.TestCase):
        def test_instantiation(self):
            composite = SequenceComposite('foo', 'bar')
            self.assertIsInstance(composite, Sequence)


    class TestMappingComposite(unittest.TestCase):
        def test_instantiation(self):
            composite = MappingComposite({'x': 'foo', 'y': 'bar'})
            self.assertIsInstance(composite, Mapping)


    unittest.main()
