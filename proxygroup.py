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
    """A base class to provide magic methods that operate directly on
    the ProxyGroup itself---rather than on the objects it contains.

    These methods must be accessed using super()::

        >>> group1 = ProxyGroup(['foo', 'bar'])
        >>> group2 = ProxyGroup(['foo', 'bar'])
        >>> super(ProxyGroup, group1).__eq__(group2)
        True
    """
    def __eq__(self, other):
        return (isinstance(other, ProxyGroup)
                and self._objs == other._objs
                and self._keys == other._keys)

    def __ne__(self, other):
        return not super(ProxyGroup, self).__eq__(other)


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
            self._keys = tuple(iterable.keys())
            self._objs = tuple(iterable.values())
        else:
            self._keys = tuple()
            self._objs = tuple(iterable)

    def __iter__(self):
        if self._keys:
            return iter(zip(self._keys, self._objs))
        return iter(self._objs)

    def __repr__(self):
        cls_name = self.__class__.__name__

        if self._keys:
            zipped = zip(self._keys, self._objs)
            obj_reprs = ['{0!r}: {1!r}'.format(k, v) for k, v in zipped]
            indent_str = '    '
            begin, end = '{', '}'
        else:
            obj_reprs = [repr(x) for x in self._objs]
            indent_str = '  '
            begin, end = '[', ']'

        # Get length of _objs reprs and separator characters.
        separator_len = (len(obj_reprs) - 1) * len(', ')
        internal_repr_len = sum(len(x) for x in obj_reprs) + separator_len

        # Determine internal repr limit for single-line reprs.
        outer_repr_length = len(cls_name) + len('([])')
        max_repr_width = 79
        internal_repr_limit = max_repr_width - outer_repr_length

        # Build internal repr string.
        if internal_repr_len > internal_repr_limit:
            indent = '\n' + indent_str
            indented_objs = [indent.join(x.splitlines()) for x in obj_reprs]
            internal_repr = '\n  {0}\n'.format(',\n  '.join(indented_objs))
        else:
            internal_repr = ', '.join(obj_reprs)

        return '{0}({1}{2}{3})'.format(cls_name, begin, internal_repr, end)

    def __getattr__(self, name):
        group = self.__class__(getattr(obj, name) for obj in self._objs)
        group._keys = self._keys
        return group

    def _compatible_group(self, value):
        """Returns True if *value* is a ProxyGroup with compatible
        contents.
        """
        if not isinstance(value, ProxyGroup):
            return False
        if len(value._objs) != len(self._objs):
            return False
        if set(value._keys) != set(self._keys):
            return False
        return True

    def _normalize_value(self, value):
        """Return a tuple of objects equal the number of objects
        contained in the ProxyGroup.

        If *value* itself is a compatible ProxyGroup, its contents will
        be returned::

            >>> group = ProxyGroup([2, 4])
            >>> group._normalize_value(ProxyGroup([5, 6]))
            (5, 6)

        If *value* is not a compatible ProxyGroup, the iterable will
        contain multiple copies of the same *value*::

            >>> group = ProxyGroup([2, 4])
            >>> group._normalize_value(9)
            (9, 9)
        """
        if self._compatible_group(value):
            if value._keys:
                key_order = (self._keys.index(x) for x in value._keys)
                _, objs = zip(*sorted(zip(key_order, value._objs)))
                return objs
            return value._objs
        return (value,) * len(self._objs)  # <- Expand single value.

    def _expand_args_kwds(self, *args, **kwds):
        """Return an expanded list of *args* and *kwds* to use when
        calling objects contained in the ProxyGroup.

        When a compatible ProxyGroup is passed as an argument, its
        contents are unwrapped and paired with each record. When a
        non-compatible value is passed as an argument, it is duplicated
        for each record::

            >>> group = ProxyGroup([2, 4])
            >>> group._expand_args_kwds(ProxyGroup([5, 6]), 9, a=12)
            [((5, 9), {'a': 12}),
             ((6, 9), {'a': 12})]
        """
        objs_len = len(self._objs)

        normalized_args = (self._normalize_value(arg) for arg in args)
        zipped_args = tuple(zip(*normalized_args))
        if not zipped_args:
            zipped_args = ((),) * objs_len

        normalized_values = (self._normalize_value(v) for v in kwds.values())
        zipped_values = zip(*normalized_values)
        zipped_kwds = tuple(dict(zip(kwds.keys(), x)) for x in zipped_values)
        if not zipped_kwds:
            zipped_kwds = ({},) * objs_len

        return list(zip(zipped_args, zipped_kwds))

    def __call__(self, *args, **kwds):
        if any(self._compatible_group(x) for x in chain(args, kwds.values())):
            # Call each object using args and kwds from the expanded list.
            expanded_list = self._expand_args_kwds(*args, **kwds)
            zipped = zip(self._objs, expanded_list)
            iterable = (obj(*a, **k) for (obj, (a, k)) in zipped)
        else:
            # Call each object with the same args and kwds.
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

    try:
        import pandas
    except ImportError:
        pandas = None


    class TestProxyGroup(unittest.TestCase):
        def test_init_sequence(self):
            group = ProxyGroup([1, 2, 3])
            self.assertEqual(group._keys, ())
            self.assertEqual(group._objs, (1, 2, 3))

        def test_init_mapping(self):
            data = {'a': 1, 'b': 2, 'c': 3}
            group = ProxyGroup({'a': 1, 'b': 2, 'c': 3})
            self.assertEqual(group._keys, tuple(data.keys()))
            self.assertEqual(group._objs, tuple(data.values()))

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

            group = ProxyGroup([1, 2])
            group._keys = ['a', 'b']
            self.assertEqual(repr(group), "ProxyGroup({'a': 1, 'b': 2})")

            # Exactly up-to single-line limit.
            value = 'a' * 63
            group = ProxyGroup([value])
            self.assertEqual(len(repr(group)), 79)
            self.assertEqual(
                repr(group),
                "ProxyGroup(['{0}'])".format(value),
            )

            # Multi-line repr (one char over single-line limit)
            value = 'a' * 64
            group = ProxyGroup([value])
            self.assertEqual(len(repr(group)), 84)
            self.assertEqual(
                repr(group),
                "ProxyGroup([\n  '{0}'\n])".format(value),
            )

        def test_getattr(self):
            class ExampleClass(object):
                attr = 123

            group = ProxyGroup([ExampleClass(), ExampleClass()])
            group = group.attr
            self.assertIsInstance(group, ProxyGroup)
            self.assertEqual(group._objs, (123, 123))

        def test_compatible_group(self):
            # Test ProxyGroup of list items.
            group = ProxyGroup([2, 4])
            self.assertTrue(
                group._compatible_group(ProxyGroup([5, 6])),
                msg='is ProxyGroup and _objs length matches',
            )
            self.assertFalse(
                group._compatible_group(1),
                msg='non-ProxyGroup values are never compatible',
            )
            self.assertFalse(
                group._compatible_group(ProxyGroup([5, 6, 7])),
                msg='not compatible when _objs length does not match',
            )
            self.assertFalse(
                group._compatible_group(ProxyGroup({'foo': 5, 'bar': 6})),
                msg='not compatible if keys are given but original has no keys',
            )

            # Test ProxyGroup of dict items.
            group = ProxyGroup({'foo': 2, 'bar': 4})
            self.assertTrue(
                group._compatible_group(ProxyGroup({'foo': 5, 'bar': 6})),
                msg='is ProxyGroup and _keys match',
            )
            self.assertFalse(
                group._compatible_group(ProxyGroup({'qux': 5, 'quux': 6})),
                msg='not compatible if keys do not match',
            )

        def test_normalize_value(self):
            group = ProxyGroup([2, 4])

            result = group._normalize_value(5)
            self.assertEqual(
                result,
                (5, 5),
                msg='value is expanded to match number of _objs',
            )

            result = group._normalize_value(ProxyGroup([5, 6]))
            self.assertEqual(
                result,
                (5, 6),
                msg='compatible ProxyGroups are unwrapped rather than expanded',
            )

            other = ProxyGroup([5, 6, 7])
            result = group._normalize_value(other)
            self.assertIsInstance(
                result,
                tuple,
                msg='incompatible ProxyGroups are expanded like other values',
            )
            self.assertEqual(len(result), 2)
            equals_other = super(other.__class__, other).__eq__
            self.assertTrue(equals_other(result[0]))
            self.assertTrue(equals_other(result[1]))

            group = ProxyGroup([2, 4])
            group._keys = ['foo', 'bar']
            other = ProxyGroup([8, 6])
            other._keys = ['bar', 'foo']  # <- keys in different order
            result = group._normalize_value(other)
            self.assertEqual(
                result,
                (6, 8),  # <- reordered to match `group`
                msg='result order should match key names, not _obj position',
            )

        def test_expand_args_kwds(self):
            argsgroup = ProxyGroup([2, 4])

            kwdsgroup = ProxyGroup([2, 4])
            kwdsgroup._keys = ['foo', 'bar']

            # Unwrap ProxyGroup.
            result = argsgroup._expand_args_kwds(ProxyGroup([5, 6]))
            expected = [
                ((5,), {}),
                ((6,), {}),
            ]
            self.assertEqual(result, expected)

            # Expand int and unwrap ProxyGroup.
            result = argsgroup._expand_args_kwds(1, ProxyGroup([5, 6]))
            expected = [
                ((1, 5), {}),
                ((1, 6), {}),
            ]
            self.assertEqual(result, expected)

            # Unwrap two ProxyGroups.
            result = argsgroup._expand_args_kwds(x=ProxyGroup([5, 6]), y=ProxyGroup([7, 9]))
            expected = [
                ((), {'x': 5, 'y': 7}),
                ((), {'x': 6, 'y': 9}),
            ]
            self.assertEqual(result, expected)

            # Kwdsgroup expansion.
            kwdgrp2 = ProxyGroup([5, 6])
            kwdgrp2._keys = ['foo', 'bar']

            # Unwrap keyed ProxyGroup.
            result = kwdsgroup._expand_args_kwds(kwdgrp2)
            expected = [
                ((5,), {}),
                ((6,), {}),
            ]
            self.assertEqual(result, expected)

            # Unwrap keyed ProxyGroup with keys in different order.
            kwdgrp_reverse = ProxyGroup([6, 5])
            kwdgrp_reverse._keys = ['bar', 'foo']
            result = kwdsgroup._expand_args_kwds(kwdgrp_reverse)
            expected = [
                ((5,), {}),
                ((6,), {}),
            ]
            self.assertEqual(result, expected)

            # Expand int and unwrap keyed ProxyGroup.
            result = kwdsgroup._expand_args_kwds(1, kwdgrp2)
            expected = [
                ((1, 5), {}),
                ((1, 6), {}),
            ]
            self.assertEqual(result, expected)

            # Sanity-check/quick integration test (all combinations).
            result = kwdsgroup._expand_args_kwds('a', ProxyGroup({'foo': 'b', 'bar': 'c'}),
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
            self.assertEqual(result._objs, ('FOO', 'BAR'))

        def test__add__(self):
            group = ProxyGroup([1, 2])
            result = group + 100  # <- __add__()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, (101, 102))

        def test__radd__(self):
            group = ProxyGroup([1, 2])
            result = 100 + group  # <- __radd__()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, (101, 102))

        def test__getitem__(self):
            group = ProxyGroup(['abc', 'xyz'])
            result = group[:2]  # <- __getitem__()
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(result._objs, ('ab', 'xy'))

        def test_proxygroup_argument_handling(self):
            # Unwrapping ProxyGroup args with __add__().
            group_of_ints1 = ProxyGroup([50, 60])
            group_of_ints2 = ProxyGroup([5, 10])
            group = group_of_ints1 + group_of_ints2
            self.assertEqual(group._objs, (55, 70))

            # Unwrapping ProxyGroup args with __getitem__().
            group_of_indexes = ProxyGroup([0, 1])
            group_of_strings = ProxyGroup(['abc', 'abc'])
            group = group_of_strings[group_of_indexes]
            self.assertEqual(group._objs, ('a', 'b'))


    class TestProxyGroupBaseMethods(unittest.TestCase):
        def setUp(self):
            self.group1 = ProxyGroup(['foo', 'bar'])
            self.group2 = ProxyGroup(['foo', 'baz'])

        def test__eq__(self):
            # Comparing contents of ProxyGroup (default behavior).
            result = (self.group1 == self.group2)  # <- Call to __eq__().
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(tuple(result), (True, False))

            # Comparing ProxyGroup objects themselves.
            result = super(ProxyGroup, self.group1).__eq__(self.group1)
            self.assertIs(result, True)

            result = super(ProxyGroup, self.group1).__eq__(self.group2)
            self.assertIs(result, False)

        def test__ne__(self):
            # Comparing contents of ProxyGroup (default behavior).
            result = (self.group1 != self.group2)  # <- Call to __ne__().
            self.assertIsInstance(result, ProxyGroup)
            self.assertEqual(tuple(result), (False, True))

            # Comparing ProxyGroup objects themselves.
            result = super(ProxyGroup, self.group1).__ne__(self.group2)
            self.assertIs(result, True)

            result = super(ProxyGroup, self.group1).__ne__(self.group1)
            self.assertIs(result, False)


    @unittest.skipIf(not pandas, 'pandas not found')
    class TestPandasExample(unittest.TestCase):
        """Quick integration test using a ProxyGroup of DataFrames."""

        def setUp(self):
            data = pandas.DataFrame({
                'A': ('x', 'x', 'y', 'y', 'z', 'z'),
                'B': ('foo', 'foo', 'foo', 'bar', 'bar', 'bar'),
                'C': (20, 30, 10, 20, 10, 10),
            })
            self.group = ProxyGroup([data, data])

        def test_summed_values(self):
            result = self.group['C'].sum()
            self.assertEqual(tuple(result), (100, 100))

        def test_selected_grouped_summed_values(self):
            result = self.group[['A', 'C']].groupby('A').sum()

            expected = pandas.DataFrame(
                data={'C': (50, 30, 20)},
                index=pandas.Index(['x', 'y', 'z'], name='A'),
            )

            df1, df2 = result  # Unpack results.
            pandas.testing.assert_frame_equal(df1, expected)
            pandas.testing.assert_frame_equal(df2, expected)

        def test_selected_filtered_grouped_summed_values(self):
            result = self.group[['A', 'C']][self.group['B'] == 'foo'].groupby('A').sum()

            expected = pandas.DataFrame(
                data={'C': (50, 10)},
                index=pandas.Index(['x', 'y'], name='A'),
            )

            df1, df2 = result  # Unpack results.
            pandas.testing.assert_frame_equal(df1, expected)
            pandas.testing.assert_frame_equal(df2, expected)


    unittest.main()
