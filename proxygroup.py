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

    def _expand_args(self, *args, **kwds):
        arg_values = chain(args, kwds.values())
        if not any(isinstance(x, ProxyGroup) for x in arg_values):
            return None

        len_objs = len(self._objs)

        is_expandable = \
            lambda x: isinstance(x, ProxyGroup) and len(x._objs) == len_objs

        if args:
            def expand_arg(arg):
                if is_expandable(arg):
                    return arg._objs
                return [arg] * len_objs

            expanded_args = [expand_arg(arg) for arg in args]
            zipped_args = list(zip(*expanded_args))
        else:
            zipped_args = [tuple()] * len_objs

        if kwds:
            def expand_kwd(key, value):
                if is_expandable(value):
                    return key, value._objs
                return key, [value] * len_objs

            expanded_kwds = dict(expand_kwd(k, v) for k, v in kwds.items())
            expanded_values = list(zip(*expanded_kwds.values()))
            zipped_kwds = [dict(zip(kwds.keys(), x)) for x in expanded_values]
        else:
            zipped_kwds = [{}] * len_objs

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
            self.assertEqual(group._keys, None)
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
            group = ProxyGroup([5, 10])

            # Arguments.
            result = group._expand_args(1, 2)
            self.assertIsNone(result, msg='if no args to expand, returns None')

            result = group._expand_args(ProxyGroup([2, 4]))
            expected = [
                ((2,), {}),
                ((4,), {}),
            ]
            self.assertEqual(result, expected)

            result = group._expand_args(1, ProxyGroup([2, 4]))
            expected = [
                ((1, 2), {}),
                ((1, 4), {}),
            ]
            self.assertEqual(result, expected)

            # Keywords.
            result = group._expand_args(foo=1, bar=2)
            self.assertIsNone(result, msg='if no args or kwds to expand, returns None')

            result = group._expand_args(foo=ProxyGroup([2, 4]))
            expected = [
                (tuple(), {'foo': 2}),
                (tuple(), {'foo': 4}),
            ]
            self.assertEqual(result, expected)

            result = group._expand_args(foo=1, bar=ProxyGroup([2, 4]))
            expected = [
                (tuple(), {'foo': 1, 'bar': 2}),
                (tuple(), {'foo': 1, 'bar': 4}),
            ]
            self.assertEqual(result, expected)

            # Arguments and keywords (all cases).
            result = group._expand_args('x', ProxyGroup(['y', 'z']),
                                        foo=1, bar=ProxyGroup([2, 4]))
            expected = [
                (('x', 'y'), {'foo': 1, 'bar': 2}),
                (('x', 'z'), {'foo': 1, 'bar': 4}),
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
