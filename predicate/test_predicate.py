#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import re

from predicate import _type_predicate
from predicate import _callable_predicate
from predicate import _wildcard_predicate
from predicate import _truthy_predicate
from predicate import _falsy_predicate
from predicate import _regex_predicate
from predicate import _set_predicate
from predicate import _get_matcher_parts
from predicate import get_matcher
from predicate import MatcherBase
from predicate import MatcherObject
from predicate import MatcherTuple
from predicate import Predicate


class TestTypePredicate(unittest.TestCase):
    def test_isinstance(self):
        function = lambda x: _type_predicate(int, x)
        self.assertTrue(function(0))
        self.assertTrue(function(1))
        self.assertFalse(function(0.0))
        self.assertFalse(function(1.0))

    def test_is_type(self):
        self.assertTrue(_type_predicate(int, int))


class TestCallablePredicate(unittest.TestCase):
    def test_function(self):
        def divisible3or5(x):  # <- Helper function.
            return (x % 3 == 0) or (x % 5 == 0)

        function = lambda x: _callable_predicate(divisible3or5, x)
        self.assertFalse(function(1))
        self.assertFalse(function(2))
        self.assertTrue(function(3))
        self.assertFalse(function(4))
        self.assertTrue(function(5))
        self.assertTrue(function(6))

    def test_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')

        function = lambda x: _callable_predicate(fails_internally, x)
        with self.assertRaises(TypeError):
            self.assertFalse(function('abc'))

    def test_identity(self):
        def always_false(x):  # <- Helper function.
            return False

        function = lambda x: _callable_predicate(always_false, x)
        self.assertTrue(function(always_false))

    def test_identity_with_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')

        function = lambda x: _callable_predicate(fails_internally, x)
        self.assertTrue(function(fails_internally))


class TestEllipsisWildcardParts(unittest.TestCase):
    def test_always_true(self):
        self.assertTrue(_wildcard_predicate(1))
        self.assertTrue(_wildcard_predicate(object()))
        self.assertTrue(_wildcard_predicate(None))


class TestTruthyParts(unittest.TestCase):
    def test_matches(self):
        self.assertTrue(_truthy_predicate('x'))
        self.assertTrue(_truthy_predicate(1.0))
        self.assertTrue(_truthy_predicate([1]))
        self.assertTrue(_truthy_predicate(range(1)))

    def test_nonmatches(self):
        self.assertFalse(_truthy_predicate(''))
        self.assertFalse(_truthy_predicate(0.0))
        self.assertFalse(_truthy_predicate([]))
        self.assertFalse(_truthy_predicate(range(0)))


class TestFalsyParts(unittest.TestCase):
    def test_matches(self):
        self.assertTrue(_falsy_predicate(''))
        self.assertTrue(_falsy_predicate(0.0))
        self.assertTrue(_falsy_predicate([]))
        self.assertTrue(_falsy_predicate(range(0)))

    def test_nonmatches(self):
        self.assertFalse(_falsy_predicate('x'))
        self.assertFalse(_falsy_predicate(1.0))
        self.assertFalse(_falsy_predicate([1]))
        self.assertFalse(_falsy_predicate(range(1)))


class TestRegexParts(unittest.TestCase):
    def test_function(self):
        regex = re.compile('(Ch|H)ann?ukk?ah?')
        function = lambda x: _regex_predicate(regex, x)

        self.assertTrue(function('Happy Hanukkah'))
        self.assertTrue(function('Happy Chanukah'))
        self.assertFalse(function('Merry Christmas'))

    def test_error(self):
        regex = re.compile('abc')
        with self.assertRaisesRegex(TypeError, "got int: 123"):
            self.assertFalse(_regex_predicate(regex, 123))  # Regex fails with TypeError.

        with self.assertRaisesRegex(TypeError, "got tuple: \('a', 'b'\)"):
            self.assertFalse(_regex_predicate(regex, ('a', 'b')))

    def test_identity(self):
        regex = re.compile('abc')
        self.assertTrue(_regex_predicate(regex, regex))


class TestSetParts(unittest.TestCase):
    def test_function(self):
        function = lambda x: _set_predicate(set(['abc', 'def']), x)
        self.assertTrue(function('abc'))
        self.assertFalse(function('xyz'))

    def test_whole_set_equality(self):
        function = lambda x: _set_predicate(set(['abc', 'def']), x)
        self.assertTrue(function(set(['abc', 'def'])))


class TestGetMatcherParts(unittest.TestCase):
    def test_type(self):
        pred_function, repr_string = _get_matcher_parts(int)
        self.assertTrue(pred_function(1))
        self.assertFalse(pred_function(1.0))
        self.assertEqual(repr_string, 'int')

    def test_callable(self):
        def userfunc(x):
            return x == 1
        pred_function, repr_string = _get_matcher_parts(userfunc)
        self.assertTrue(pred_function(1))
        self.assertFalse(pred_function(2))
        self.assertEqual(repr_string, 'userfunc')

        userlambda = lambda x: x == 1
        pred_function, repr_string = _get_matcher_parts(userlambda)
        self.assertTrue(pred_function(1))
        self.assertFalse(pred_function(2))
        self.assertEqual(repr_string, '<lambda>')

    def test_ellipsis_wildcard(self):
        pred_function, repr_string = _get_matcher_parts(Ellipsis)
        self.assertIs(pred_function, _wildcard_predicate)
        self.assertEqual(repr_string, '...')

    def test_truthy(self):
        pred_function, repr_string = _get_matcher_parts(True)
        self.assertIs(pred_function, _truthy_predicate)
        self.assertEqual(repr_string, 'True')

    def test_falsy(self):
        pred_function, repr_string = _get_matcher_parts(False)
        self.assertIs(pred_function, _falsy_predicate)
        self.assertEqual(repr_string, 'False')

    def test_regex(self):
        regex = re.compile('ab[cd]')

        pred_function, repr_string = _get_matcher_parts(regex)
        self.assertTrue(pred_function('abc'))
        self.assertFalse(pred_function('abe'))
        self.assertEqual(repr_string, "re.compile('ab[cd]')")

    def test_set(self):
        myset = set(['a'])
        pred_function, repr_string = _get_matcher_parts(myset)
        self.assertTrue(pred_function('a'))
        self.assertFalse(pred_function('b'))
        self.assertEqual(repr_string, repr(myset))

    def test_no_special_handling(self):
        self.assertIsNone(_get_matcher_parts(1))
        self.assertIsNone(_get_matcher_parts(0))


class TestMatcherInheritance(unittest.TestCase):
    def test_inheritance(self):
        self.assertTrue(issubclass(MatcherTuple, MatcherBase))
        self.assertTrue(issubclass(MatcherObject, MatcherBase))


class TestGetMatcher(unittest.TestCase):
    def assertIsInstance(self, obj, cls, msg=None):  # New in Python 3.2.
        if not isinstance(obj, cls):
            standardMsg = '%s is not an instance of %r' % (safe_repr(obj), cls)
            self.fail(self._formatMessage(msg, standardMsg))

    def test_single_value(self):
        # Check for MatcherObject wrapping.
        def isodd(x):  # <- Helper function.
            return x % 2 == 1
        matcher = get_matcher(isodd)
        self.assertIsInstance(matcher, MatcherObject)

        # When original is adequate, it should be returned unchanged.
        original = object()
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

    def test_tuple_of_values(self):
        # Check for MatcherTuple wrapping.
        def isodd(x):  # <- Helper function.
            return x % 2 == 1
        matcher = get_matcher((1, isodd))
        self.assertIsInstance(matcher, MatcherTuple)

        # When tuple contains no MatcherObject objects,
        # the original should be returned unchanged.
        original = ('abc', 123)
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

    def test_integration(self):
        """A small integration test that checks a tuple containing all
        of the different special handling cases.
        """
        def mycallable(x):  # <- Helper function.
            return x == '_'

        myregex = re.compile('_')

        myset = set(['_'])

        matcher = get_matcher(
            (mycallable,  myregex, myset, '_', Ellipsis)
        )

        self.assertTrue(matcher == ('_', '_', '_', '_', '_'))   # <- Passes all conditions.
        self.assertFalse(matcher == ('X', '_', '_', '_', '_'))  # <- Callable returns False.
        self.assertFalse(matcher == ('_', 'X', '_', '_', '_'))  # <- Regex has no match.
        self.assertFalse(matcher == ('_', '_', 'X', '_', '_'))  # <- Not in set.
        self.assertFalse(matcher == ('_', '_', '_', 'X', '_'))  # <- Does not equal string.
        self.assertTrue(matcher == ('_', '_', '_', '_', 'X'))   # <- Passes all conditions (wildcard).

        expected = "(mycallable, re.compile('_'), {0!r}, '_', ...)".format(myset)
        self.assertEqual(repr(matcher), expected)


class TestPredicate(unittest.TestCase):
    def test_predicate_function(self):
        pred = Predicate('abc')
        self.assertTrue(pred('abc'))
        self.assertFalse(pred('def'))

        pred = Predicate(('abc', int))
        self.assertTrue(pred(('abc', 1)))
        self.assertFalse(pred(('abc', 1.0)))

    def test_inverted_logic(self):
        pred = ~Predicate('abc')
        self.assertFalse(pred('abc'))
        self.assertTrue(pred('def'))

    def test_repr(self):
        pred = Predicate('abc')
        self.assertEqual(repr(pred), "Predicate('abc')")

        pred = ~Predicate('abc')
        self.assertEqual(repr(pred), "~Predicate('abc')")


if __name__ == '__main__':
    unittest.main()
