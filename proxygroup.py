#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections.abc import Iterable


class ProxyGroup(Iterable):
    def __init__(self, iterable):
        self._objs = list(iterable)

    def __iter__(self):
        return iter(self._objs)


if __name__ == '__main__':
    import unittest


    class TestProxyGroup(unittest.TestCase):
        def test_instantiation(self):
            group = ProxyGroup([1, 2, 3])
            self.assertIsInstance(group, Iterable)


    unittest.main()
