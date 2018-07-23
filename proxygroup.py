#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections.abc import Iterable
from collections.abc import Mapping


class ProxyGroup(Iterable):
    def __init__(self, iterable):
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


if __name__ == '__main__':
    import unittest


    class TestProxyGroup(unittest.TestCase):
        def test_instantiation(self):
            group = ProxyGroup([1, 2, 3])
            self.assertEqual(group._keys, None)
            self.assertEqual(group._objs, [1, 2, 3])

            group = ProxyGroup({'a': 1, 'b': 2, 'c': 3})
            self.assertEqual(group._keys, ['a', 'b', 'c'])
            self.assertEqual(group._objs, [1, 2, 3])

        def test_iteration(self):
            group = ProxyGroup([1, 2, 3])
            self.assertEqual(list(group), [1, 2, 3])

            group = ProxyGroup({'a': 1, 'b': 2, 'c': 3})
            self.assertEqual(list(group), [('a', 1), ('b', 2), ('c', 3)])


    unittest.main()
