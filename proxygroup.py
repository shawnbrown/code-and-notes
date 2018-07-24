#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections.abc import Iterable
from collections.abc import Mapping
from functools import partial


class ProxyGroup(Iterable):
    """
    Method calls and property references are passed to the individual
    objects and a new ProxyGroup is returned containing the results::

        >>> group = ProxyGroup(['foo', 'bar'])
        >>> group.upper()
        ProxyGroup(['FOO', 'BAR'])

    ProxyGroup is an iterable and individual items can be accessed
    through iteration or sequence unpacking. Below, the individual
    objects are unpacked into the variables ``x`` and ``y``::

        >>> group = ProxyGroup(['foo', 'bar'])
        >>> group = group.upper()
        >>> x, y = group
        >>> x
        'FOO'
        >>> y
        'BAR'
    """
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
        group = self.__class__(getattr(obj, name) for obj in self._objs)
        group._keys = self._keys
        return group

    def __call__(self, *args, **kwds):
        group = self.__class__(obj(*args, **kwds) for obj in self._objs)
        group._keys = self._keys
        return group


def _define_special_attribute_proxies(proxy_class):
    special_attributes = """
        add sub mul mod truediv floordiv div
        radd rsub rmul rmod rtruediv rfloordiv rdiv
        getitem setitem delitem
        lt le eq ne gt ge
    """.split()

    def proxy_getattr(self, name):
        group = self.__class__(getattr(obj, name) for obj in self._objs)
        group._keys = self._keys
        return group

    for name in special_attributes:
        dunder = '__{0}__'.format(name)
        method = partial(proxy_getattr, name=dunder)
        setattr(proxy_class, dunder, property(method))

_define_special_attribute_proxies(ProxyGroup)


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
            class ExampleClass(object):
                attr = 123

            group = ProxyGroup([ExampleClass(), ExampleClass()])
            group = group.attr
            self.assertIsInstance(group, ProxyGroup)
            self.assertEqual(group._objs, [123, 123])

        def test_call(self):
            group = ProxyGroup(['foo', 'bar'])
            result = group.upper()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, ['FOO', 'BAR'])

        def test__add__(self):
            group = ProxyGroup([1, 2])
            result = group + 100  # <- __add__()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, [101, 102])

        def test__radd__(self):
            group = ProxyGroup([1, 2])
            result = 100 + group  # <- __radd__()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, [101, 102])

        def test__getitem__(self):
            group = ProxyGroup(['abc', 'xyz'])
            result = group[:2]  # <- __getattr__()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, ['ab', 'xy'])


    unittest.main()
