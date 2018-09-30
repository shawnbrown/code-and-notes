#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import re

from predicate import _get_matcher_parts
from predicate import get_matcher
from predicate import MatcherBase
from predicate import MatcherObject
from predicate import MatcherTuple
from predicate import Predicate


class TestTypeParts(unittest.TestCase):
    def test_repr_string(self):
        _, repr_string = _get_matcher_parts(int)
        self.assertEqual(repr_string, 'int')

    def test_function(self):
        function, _ = _get_matcher_parts(int)
        self.assertTrue(function(0))
        self.assertTrue(function(1))
        self.assertFalse(function(0.0))
        self.assertFalse(function(1.0))


class TestCallableParts(unittest.TestCase):
    def test_repr_string(self):
        def userfunc(x):
            return True
        _, repr_string = _get_matcher_parts(userfunc)
        self.assertEqual(repr_string, 'userfunc')

        userlambda = lambda x: True
        _, repr_string = _get_matcher_parts(userlambda)
        self.assertEqual(repr_string, '<lambda>')

    def test_function(self):
        def divisible3or5(x):  # <- Helper function.
            return (x % 3 == 0) or (x % 5 == 0)

        function, _ = _get_matcher_parts(divisible3or5)
        self.assertFalse(function(1))
        self.assertFalse(function(2))
        self.assertTrue(function(3))
        self.assertFalse(function(4))
        self.assertTrue(function(5))
        self.assertTrue(function(6))

    def test_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')

        function, _ = _get_matcher_parts(fails_internally)
        with self.assertRaises(TypeError):
            self.assertFalse(function('abc'))

    def test_identity(self):
        def always_false(x):  # <- Helper function.
            return False

        function, _ = _get_matcher_parts(always_false)
        self.assertTrue(function(always_false))

    def test_identity_with_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')

        function, _ = _get_matcher_parts(fails_internally)
        self.assertTrue(function(fails_internally))


class TestEllipsisWildcardParts(unittest.TestCase):
    def test_repr_string(self):
        _, repr_string = _get_matcher_parts(Ellipsis)
        self.assertEqual(repr_string, '...')

    def test_function(self):
        function, _ = _get_matcher_parts(Ellipsis)
        self.assertTrue(function(1))
        self.assertTrue(function(object()))
        self.assertTrue(function(None))


class TestTruthyParts(unittest.TestCase):
    def setUp(self):
        function, repr_string = _get_matcher_parts(True)
        self.function = function
        self.repr_string = repr_string

    def test_repr_string(self):
        self.assertEqual(self.repr_string, 'True')

    def test_matches(self):
        self.assertTrue(self.function('x'))
        self.assertTrue(self.function(1.0))
        self.assertTrue(self.function([1]))
        self.assertTrue(self.function(range(1)))

    def test_nonmatches(self):
        self.assertFalse(self.function(''))
        self.assertFalse(self.function(0.0))
        self.assertFalse(self.function([]))
        self.assertFalse(self.function(range(0)))

    def test_number_one(self):
        self.assertIsNone(_get_matcher_parts(1))


class TestFalsyParts(unittest.TestCase):
    def setUp(self):
        function, repr_string = _get_matcher_parts(False)
        self.function = function
        self.repr_string = repr_string

    def test_repr_string(self):
        self.assertEqual(self.repr_string, 'False')

    def test_matches(self):
        self.assertTrue(self.function(''))
        self.assertTrue(self.function(0.0))
        self.assertTrue(self.function([]))
        self.assertTrue(self.function(range(0)))

    def test_nonmatches(self):
        self.assertFalse(self.function('x'))
        self.assertFalse(self.function(1.0))
        self.assertFalse(self.function([1]))
        self.assertFalse(self.function(range(1)))

    def test_number_zero(self):
        self.assertIsNone(_get_matcher_parts(0))


class TestRegexParts(unittest.TestCase):
    def setUp(self):
        regex = re.compile('(Ch|H)ann?ukk?ah?')
        function, repr_string = _get_matcher_parts(regex)
        self.regex = regex
        self.function = function
        self.repr_string = repr_string

    def test_repr_string(self):
        self.assertEqual(self.repr_string, "re.compile('(Ch|H)ann?ukk?ah?')")

    def test_function(self):
        self.assertTrue(self.function('Happy Hanukkah'))
        self.assertTrue(self.function('Happy Chanukah'))
        self.assertFalse(self.function('Merry Christmas'))

    def test_error(self):
        with self.assertRaisesRegex(TypeError, "got int: 123"):
            self.assertFalse(self.function(123))  # Regex fails with TypeError.

        with self.assertRaisesRegex(TypeError, "got tuple: \('a', 'b'\)"):
            self.assertFalse(self.function(('a', 'b')))

    def test_identity(self):
        self.assertTrue(self.function(self.regex))


class TestSetParts(unittest.TestCase):
    def test_repr_string(self):
        myset = set(['a'])
        _, repr_string = _get_matcher_parts(myset)
        self.assertEqual(repr_string, repr(myset))

    def test_function(self):
        function, _ = _get_matcher_parts(set(['abc', 'def']))
        self.assertTrue(function('abc'))
        self.assertFalse(function('xyz'))

    def test_whole_set_equality(self):
        function, _ = _get_matcher_parts(set(['abc', 'def']))
        self.assertTrue(function(set(['abc', 'def'])))


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

        matcher = get_matcher(Ellipsis)
        self.assertIsInstance(matcher, MatcherObject)

        matcher = get_matcher(re.compile('abc'))
        self.assertIsInstance(matcher, MatcherObject)

        matcher = get_matcher(set([1, 2, 3]))
        self.assertIsInstance(matcher, MatcherObject)

        # When original is adequate, it should be returned unchanged.
        original = 123
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

        original = 'abc'
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

        original = ['abc', 123]
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

        original = object()
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

    def test_tuple_of_values(self):
        # Check for MatcherTuple wrapping.
        def isodd(x):  # <- Helper function.
            return x % 2 == 1
        matcher = get_matcher((1, isodd))
        self.assertIsInstance(matcher, MatcherTuple)

        matcher = get_matcher((1, Ellipsis))
        self.assertIsInstance(matcher, MatcherTuple)

        matcher = get_matcher((1, re.compile('abc')))
        self.assertIsInstance(matcher, MatcherTuple)

        matcher = get_matcher((1, set([1, 2, 3])))
        self.assertIsInstance(matcher, MatcherTuple)

        # When tuple contains no MatcherObject objects,
        # the original should be returned unchanged.
        original = ('abc', 123)
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

    def test_integration(self):
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
