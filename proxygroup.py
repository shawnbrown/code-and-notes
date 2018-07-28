#!/usr/bin/env python
# -*- coding: utf-8 -*-
from functools import partial
from itertools import chain

try:
    from collections.abc import Iterable
    from collections.abc import Mapping
except ImportError:
    from collections import Iterable
    from collections import Mapping

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest


class ProxyGroupBase(Iterable):
    """A base class to provide magic methods that operate directly
    on a ProxyGroup itself (rather than on the objects it contains).

    These methods must be accessed using super()::

        >>> group1 = ProxyGroup(['foo', 'bar'])
        >>> group2 = ProxyGroup(['foo', 'bar'])
        >>> super(ProxyGroup, group1).__eq__(group2)
        True
    """
    def __eq__(self, other):
        return (isinstance(other, ProxyGroupBase)
                and self._objs == getattr(other, '_objs', None)
                and self._keys == getattr(other, '_keys', None))

    def __ne__(self, other):
        return not self.__eq__(other)


class ProxyGroup(ProxyGroupBase):
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
            self._keys = list()
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

    def _expand_args(self, *args, **kwds):
        objs_len = len(self._objs)
        keys_set = set(self._keys)

        def is_expandable(arg):
            if not isinstance(arg, ProxyGroup):
                return False
            if len(arg._objs) != objs_len:
                return False
            if set(arg._keys) != keys_set:
                return False
            return True

        if not any(is_expandable(x) for x in chain(args, kwds.values())):
            return None  # <- EXIT!

        def expand_arg(arg):
            if not is_expandable(arg):
                return [arg] * objs_len

            if arg._keys:
                order = (self._keys.index(x) for x in arg._keys)
                _, objs = zip(*sorted(zip(order, arg._objs)))
                return objs
            return arg._objs

        if args:
            expanded_args = (expand_arg(arg) for arg in args)
            zipped_args = zip(*expanded_args)
        else:
            zipped_args = [()] * objs_len

        if kwds:
            expanded_values = (expand_arg(v) for v in kwds.values())
            zipped_values = zip(*expanded_values)
            zipped_kwds = (dict(zip(kwds.keys(), x)) for x in zipped_values)
        else:
            zipped_kwds = [{}] * objs_len

        return list(zip(zipped_args, zipped_kwds))

    def __call__(self, *args, **kwds):
        expanded = self._expand_args(*args, **kwds)
        if expanded:
            zipped = zip(self._objs, expanded)
            iterable = (obj(*a, **k) for (obj, (a, k)) in zipped)
        else:
            iterable = (obj(*args, **kwds) for obj in self._objs)

        group = self.__class__(iterable)
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
            self.assertEqual(group._keys, [])
            self.assertEqual(group._objs, [1, 2, 3])

        def test_init_mapping(self):
            data = {'a': 1, 'b': 2, 'c': 3}
            group = ProxyGroup({'a': 1, 'b': 2, 'c': 3})
            self.assertEqual(group._keys, list(data.keys()))
            self.assertEqual(group._objs, list(data.values()))

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
            self.assertEqual(set(group), set([('a', 1), ('b', 2), ('c', 3)]))

        def test_repr(self):
            group = ProxyGroup([1, 2, 3])
            self.assertEqual(repr(group), 'ProxyGroup([1, 2, 3])')

            group = ProxyGroup({'a': 1})
            self.assertEqual(repr(group), "ProxyGroup({'a': 1})")

        def test_getattr(self):
            class ExampleClass(object):
                attr = 123

            group = ProxyGroup([ExampleClass(), ExampleClass()])
            group = group.attr
            self.assertIsInstance(group, ProxyGroup)
            self.assertEqual(group._objs, [123, 123])

        def test_expand_arguments(self):
            argsgroup = ProxyGroup([2, 4])

            kwdsgroup = ProxyGroup([2, 4])
            kwdsgroup._keys = ['foo', 'bar']

            # Nothing to expand.
            result = argsgroup._expand_args(1, 2)
            self.assertIsNone(result, msg='if no args to expand, returns None')

            result = kwdsgroup._expand_args(1, x=2)
            self.assertIsNone(result, msg='if no args or kwds to expand, return None')

            result = argsgroup._expand_args(ProxyGroup([1, 2, 3]))
            self.assertIsNone(result, msg='if args length is different, return None')

            result = argsgroup._expand_args(kwdsgroup)
            self.assertIsNone(result, msg='if expects args but only get kwds, return None')

            result = kwdsgroup._expand_args(argsgroup)
            self.assertIsNone(result, msg='if expects kwds but only get args, return None')

            result = kwdsgroup._expand_args(ProxyGroup({'qux': 5, 'quux': 6}))
            self.assertIsNone(result, msg='if kwds do not match, return None')

            # Argsgroup expansion.
            result = argsgroup._expand_args(ProxyGroup([5, 6]))
            expected = [
                ((5,), {}),
                ((6,), {}),
            ]
            self.assertEqual(result, expected)

            result = argsgroup._expand_args(1, ProxyGroup([5, 6]))
            expected = [
                ((1, 5), {}),
                ((1, 6), {}),
            ]
            self.assertEqual(result, expected)

            result = argsgroup._expand_args(x=ProxyGroup([5, 6]), y=ProxyGroup([7, 9]))
            expected = [
                (tuple(), {'x': 5, 'y': 7}),
                (tuple(), {'x': 6, 'y': 9}),
            ]
            self.assertEqual(result, expected)

            # Kwdsgroup expansion.
            kwdgrp2 = ProxyGroup([5, 6])
            kwdgrp2._keys = ['foo', 'bar']

            result = kwdsgroup._expand_args(kwdgrp2)
            expected = [
                ((5,), {}),
                ((6,), {}),
            ]
            self.assertEqual(result, expected)

            kwdgrp_reverse = ProxyGroup([6, 5])
            kwdgrp_reverse._keys = ['bar', 'foo']
            result = kwdsgroup._expand_args(kwdgrp_reverse)
            expected = [
                ((5,), {}),
                ((6,), {}),
            ]
            self.assertEqual(result, expected)

            result = kwdsgroup._expand_args(1, kwdgrp2)
            expected = [
                ((1, 5), {}),
                ((1, 6), {}),
            ]
            self.assertEqual(result, expected)

            # Arguments and keywords (all cases).
            result = kwdsgroup._expand_args('a', ProxyGroup({'foo': 'b', 'bar': 'c'}),
                                            x=1, y=ProxyGroup({'bar': 4, 'foo': 2}))
            expected = [
                (('a', 'b'), {'x': 1, 'y': 2}),
                (('a', 'c'), {'x': 1, 'y': 4}),
            ]
            self.assertEqual(result, expected)

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
            result = group[:2]  # <- __getitem__()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, ['ab', 'xy'])

        def test_proxygroup_argument_handling(self):
            # Unwrapping ProxyGroup args with __add__().
            group_of_ints1 = ProxyGroup([50, 60])
            group_of_ints2 = ProxyGroup([5, 10])
            group = group_of_ints1 + group_of_ints2
            self.assertEqual(group._objs, [55, 70])

            # Unwrapping ProxyGroup args with __getitem__().
            group_of_indexes = ProxyGroup([0, 1])
            group_of_strings = ProxyGroup(['abc', 'abc'])
            group = group_of_strings[group_of_indexes]
            self.assertEqual(group._objs, ['a', 'b'])

    class TestProxyGroupBaseMethods(unittest.TestCase):
        def test__eq__(self):
            group1 = ProxyGroup(['foo', 'bar'])
            group2 = ProxyGroup(['foo', 'bar'])

            result = group1.__eq__(group2)
            self.assertIsInstance(result, ProxyGroup,
                                  msg='comparison runs on ProxyGroup contents')

            result = super(ProxyGroup, group1).__eq__(group2)
            self.assertIs(
                result, True, msg='comparison runs on ProxyGroup itself')


    unittest.main()
