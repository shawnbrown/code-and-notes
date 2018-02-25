#!/usr/bin/env python
# -*- coding: utf-8 -*-
import abc
import re

try:
    abc.ABC  # New in version 3.4.
except NameError:
    _ABC = ABCMeta('ABC', (object,), {})  # <- Using Python 2 and 3
                                          #    compatible syntax.
    abc.ABC = _ABC

regex_types = type(re.compile(''))

try:
    callable  # Removed from 3.0 and 3.1, added back in 3.2.
except NameError:
    def callable(obj):
        parent_types = type(obj).__mro__
        return any('__call__' in typ.__dict__ for typ in parent_types)


class PredicateObject(abc.ABC):
    """Base class for objects that implement rich predicate matching."""
    @abc.abstractmethod
    def __repr__(self):
        return super(PredicateObject, self).__repr__()


class PredicateTuple(PredicateObject, tuple):
    """Wrapper to mark tuples that contain one or more PredicateMatcher
    instances.
    """
    pass


class PredicateMatcher(PredicateObject):
    """Wrapper to call *func* when evaluating the '==' operator."""
    def __init__(self, func, name):
        self._func = func
        self._name = name

    def __eq__(self, other):
        return self._func(other)

    def __repr__(self):
        return self._name


def _get_matcher(value):
    """Return an object suitable for comparing to other values
    using the "==" operator.

    When special comparison handling is required, returns a
    PredicateMatcher instance. When no special comparison is
    needed, returns the original object unchanged.
    """
    if callable(value):
        func = lambda x: (x is value) or value(x)
        name = getattr(value, '__name__', repr(value))
    elif value is Ellipsis:
        func = lambda x: True  # <- Wildcard (matches everything).
        name = '...'
    elif isinstance(value, regex_types):
        func = lambda x: (x is value) or (value.search(x) is not None)
        name = 're.compile({0!r})'.format(value.pattern)
    elif isinstance(value, set):
        func = lambda x: (x in value) or (x == value)
        name = repr(value)
    else:
        return value  # <- EXIT!
    return PredicateMatcher(func, name)


def get_predicate(obj):
    """Return a predicate object suitable for comparing to other
    objects using the "==" operator.

    If the original object is already suitable for this purpose,
    it will be returned unchanged. If special comparison handling
    is implemented, a PredicateObject will be returned instead.
    """
    if isinstance(obj, tuple):
        predicate = tuple(_get_matcher(x) for x in obj)
        for x in predicate:
            if isinstance(x, PredicateObject):
                return PredicateTuple(predicate)  # <- Wrapper.
        return obj  # <- Orignal reference.

    return _get_matcher(obj)


if __name__ == '__main__':
    import unittest


    class TestAdaptedCallable(unittest.TestCase):
        def test_equality(self):
            def divisible3or5(x):  # <- Helper function.
                return (x % 3 == 0) or (x % 5 == 0)
            adapted = _get_matcher(divisible3or5)

            self.assertFalse(adapted == 1)
            self.assertFalse(adapted == 2)
            self.assertTrue(adapted == 3)
            self.assertFalse(adapted == 4)
            self.assertTrue(adapted == 5)
            self.assertTrue(adapted == 6)

        def test_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            adapted = _get_matcher(fails_internally)

            with self.assertRaises(TypeError):
                self.assertFalse(adapted == 'abc')

        def test_identity(self):
            def always_false(x):
                return False
            adapted = _get_matcher(always_false)

            self.assertTrue(adapted ==always_false)

        def test_identity_with_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            adapted = _get_matcher(fails_internally)

            self.assertTrue(adapted == fails_internally)

        def test_repr(self):
            def userfunc(x):
                return True
            adapted = _get_matcher(userfunc)
            self.assertEqual(repr(adapted), 'userfunc')

            userlambda = lambda x: True
            adapted = _get_matcher(userlambda)
            self.assertEqual(repr(adapted), '<lambda>')


    class TestAdaptedRegex(unittest.TestCase):
        def test_equality(self):
            adapted = _get_matcher(re.compile('(Ch|H)ann?ukk?ah?'))

            self.assertTrue(adapted == 'Happy Hanukkah')
            self.assertTrue(adapted == 'Happy Chanukah')
            self.assertFalse(adapted == 'Merry Christmas')

        def test_error(self):
            adapted = _get_matcher(re.compile('abc'))

            with self.assertRaises(TypeError):
                self.assertFalse(adapted == 123)  # Regex fails with TypeError.

        def test_identity(self):
            regex = re.compile('abc')
            adapted = _get_matcher(regex)

            self.assertTrue(adapted == regex)

        def test_repr(self):
            adapted = _get_matcher(re.compile('abc'))

            self.assertEqual(repr(adapted), "re.compile('abc')")


    class TestAdaptedSet(unittest.TestCase):
        def test_equality(self):
            adapted = _get_matcher(set(['a', 'e', 'i', 'o', 'u']))

            self.assertTrue(adapted == 'a')
            self.assertFalse(adapted == 'x')

        def test_whole_set_equality(self):
            adapted = _get_matcher(set(['a', 'b', 'c']))

            self.assertTrue(adapted == set(['a', 'b', 'c']))

        def test_repr(self):
            adapted = _get_matcher(set(['a']))

            self.assertEqual(repr(adapted), repr(set(['a'])))


    class TestAdaptedEllipsisWildcard(unittest.TestCase):
        def test_equality(self):
            adapted = _get_matcher(Ellipsis)

            self.assertTrue(adapted == 1)
            self.assertTrue(adapted == object())
            self.assertTrue(adapted == None)

        def test_repr(self):
            adapted = _get_matcher(Ellipsis)

            self.assertEqual(repr(adapted), '...')


    class TestGetPredicateObject(unittest.TestCase):
        def test_single_value(self):
            # Check for PredicateMatcher wrapping.
            def isodd(x):  # <- Helper function.
                return x % 2 == 1
            predicate = get_predicate(isodd)
            self.assertIsInstance(predicate, PredicateMatcher)

            predicate = get_predicate(Ellipsis)
            self.assertIsInstance(predicate, PredicateMatcher)

            predicate = get_predicate(re.compile('abc'))
            self.assertIsInstance(predicate, PredicateMatcher)

            predicate = get_predicate(set([1, 2, 3]))
            self.assertIsInstance(predicate, PredicateMatcher)

            # When original is adequate, it should be returned unchanged.
            original = 123
            predicate = get_predicate(original)
            self.assertIs(predicate, original)

            original = 'abc'
            predicate = get_predicate(original)
            self.assertIs(predicate, original)

            original = ['abc', 123]
            predicate = get_predicate(original)
            self.assertIs(predicate, original)

            original = object()
            predicate = get_predicate(original)
            self.assertIs(predicate, original)

        def test_tuple_of_values(self):
            # Check for PredicateTuple wrapping.
            def isodd(x):  # <- Helper function.
                return x % 2 == 1
            predicate = get_predicate((1, isodd))
            self.assertIsInstance(predicate, PredicateTuple)

            predicate = get_predicate((1, Ellipsis))
            self.assertIsInstance(predicate, PredicateTuple)

            predicate = get_predicate((1, re.compile('abc')))
            self.assertIsInstance(predicate, PredicateTuple)

            predicate = get_predicate((1, set([1, 2, 3])))
            self.assertIsInstance(predicate, PredicateTuple)

            # When tuple contains no PredicateMatcher objects,
            # the original should be returned unchanged.
            original = ('abc', 123)
            predicate = get_predicate(original)
            self.assertIs(predicate, original)

        def test_integration(self):
            def mycallable(x):  # <- Helper function.
                return x == '_'

            myregex = re.compile('_')

            myset = set(['_'])

            predicate = get_predicate(
                (mycallable,  myregex, myset, '_', Ellipsis)
            )

            self.assertTrue(predicate == ('_', '_', '_', '_', '_'))   # <- Passes all conditions.
            self.assertFalse(predicate == ('X', '_', '_', '_', '_'))  # <- Callable returns False.
            self.assertFalse(predicate == ('_', 'X', '_', '_', '_'))  # <- Regex has no match.
            self.assertFalse(predicate == ('_', '_', 'X', '_', '_'))  # <- Not in set.
            self.assertFalse(predicate == ('_', '_', '_', 'X', '_'))  # <- Does not equal string.
            self.assertTrue(predicate == ('_', '_', '_', '_', 'X'))   # <- Passes all conditions (wildcard).

            expected = "(mycallable, re.compile('_'), {0!r}, '_', ...)".format(myset)
            self.assertEqual(repr(predicate), expected)


    unittest.main()
