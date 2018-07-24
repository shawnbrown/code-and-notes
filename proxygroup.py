#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections.abc import Iterable
from collections.abc import Mapping


class ProxyGroup(Iterable):
    def __init__(self, iterable):
        if not isinstance(iterable, Iterable):
            msg = '{0!r} object is not iterable'
            raise TypeError(msg.format(iterable.__class__.__name__))

        if isinstance(iterable, str):
            msg = "expected non-string iterable, got 'str'"
            raise ValueError(msg)

        if isinstance(iterable, Mapping):
            self._keys = list(iterable.keys())
            self._objs = list(iterable.values())
        else:
            self._keys = None
            self._objs = list(iterable)

    def __iter__(self):
        if self._keys:
            return iter(zip(self._keys, self._objs))
        return iter(self._objs)

    def __repr__(self):
        cls_name = self.__class__.__name__
        if self._keys:
            zipped = zip(self._keys, self._objs)
            obj_reprs = ('{0!r}: {1!r}'.format(k, v) for k, v in zipped)
            obj_reprs = '{{{0}}}'.format(', '.join(obj_reprs))
        else:
            obj_reprs = (repr(x) for x in self._objs)
            obj_reprs = '[{0}]'.format(', '.join(obj_reprs))

        return '{0}({1})'.format(cls_name, obj_reprs)

    def __getattr__(self, name):
        group = self.__class__(getattr(x, name) for x in self._objs)
        group._keys = self._keys
        return group


if __name__ == '__main__':
    import unittest


    class TestProxyGroup(unittest.TestCase):
        def test_init_sequence(self):
            group = ProxyGroup([1, 2, 3])
            self.assertEqual(group._keys, None)
            self.assertEqual(group._objs, [1, 2, 3])

        def test_init_mapping(self):
            group = ProxyGroup({'a': 1, 'b': 2, 'c': 3})
            self.assertEqual(group._keys, ['a', 'b', 'c'])
            self.assertEqual(group._objs, [1, 2, 3])

        def test_init_exceptions(self):
            with self.assertRaises(TypeError):
                ProxyGroup(123)

            with self.assertRaises(ValueError):
                ProxyGroup('abc')

        def test_iter_sequence(self):
            group = ProxyGroup([1, 2, 3])
            self.assertEqual(list(group), [1, 2, 3])

        def test_iter_mapping(self):
            group = ProxyGroup({'a': 1, 'b': 2, 'c': 3})
            self.assertEqual(list(group), [('a', 1), ('b', 2), ('c', 3)])

        def test_repr(self):
            group = ProxyGroup([1, 2, 3])
            self.assertEqual(repr(group), 'ProxyGroup([1, 2, 3])')

            group = ProxyGroup({'a': 1, 'b': 2, 'c': 3})
            self.assertEqual(repr(group), "ProxyGroup({'a': 1, 'b': 2, 'c': 3})")

        def test_getattr(self):
            class MyClass(object):
                def __init__(self, arg):
                    self.attr = arg

            group = ProxyGroup([MyClass(123), MyClass(456)])
            group = group.attr
            self.assertIsInstance(group, ProxyGroup)
            self.assertEqual(group._objs, [123, 456])

    unittest.main()
