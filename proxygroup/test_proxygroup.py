#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest

try:
    import pandas
except ImportError:
    pandas = None

from proxygroup import ProxyGroup
from proxygroup import ProxyGroupBase


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


if __name__ == '__main__':
    unittest.main()
