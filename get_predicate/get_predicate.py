#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Predicate objects are used to check that values satisfy a certain
criteria. The specific behavior of a predicate depends on its type:

    +----------------------+------------------------------------------+
    | Predicate type       | Checks that                              |
    +======================+==========================================+
    | set                  | value is a member of the set             |
    +----------------------+------------------------------------------+
    | function             | calling ``function(value)`` returns True |
    +----------------------+------------------------------------------+
    | type                 | value is an instance of the type         |
    +----------------------+------------------------------------------+
    | re.compile(pattern)  | value matches the regular expression     |
    +----------------------+------------------------------------------+
    | str or non-container | value equals predicate                   |
    +----------------------+------------------------------------------+
    | tuple of             | tuple of values satisfies corresponding  |
    | predicates           | tuple of predicates                      |
    +----------------------+------------------------------------------+
    | True                 | value is truthy (truth value is True)    |
    +----------------------+------------------------------------------+
    | False                | value is falsy (truth value is False)    |
    +----------------------+------------------------------------------+
    | "``...``" (an        | (used as a wildcard, matches any value)  |
    | ellipsis)            |                                          |
    +----------------------+------------------------------------------+


Some Examples:

    +---------------------------+----------------+---------+
    | Example Predicate         | Example Value  | Matches |
    +===========================+================+=========+
    | .. code-block:: python    | ``'A'``        | Yes     |
    |                           +----------------+---------+
    |     {'A', 'B'}            | ``'C'``        | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``4``          | Yes     |
    |                           +----------------+---------+
    |     def iseven(x):        | ``9``          | No      |
    |         return x % 2 == 0 |                |         |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``1.0``        | Yes     |
    |                           +----------------+---------+
    |     float                 | ``1``          | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'bake'``     | Yes     |
    |                           +----------------+---------+
    |     re.compile('[bc]ake') | ``'cake'``     | Yes     |
    |                           +----------------+---------+
    |                           | ``'fake'``     | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'foo'``      | Yes     |
    |                           +----------------+---------+
    |     'foo'                 | ``'bar'``      | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'x'``        | Yes     |
    |                           +----------------+---------+
    |     True                  | ``''``         | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``''``         | Yes     |
    |                           +----------------+---------+
    |     False                 | ``'x'``        | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``('A', 'X')`` | Yes     |
    |                           +----------------+---------+
    |     ('A', ...)            | ``('A', 'Y')`` | Yes     |
    |                           +----------------+---------+
    | Uses ellipsis wildcard.   | ``('B', 'X')`` | No      |
    +---------------------------+----------------+---------+

"""

import abc
import re

try:
    abc.ABC  # New in version 3.4.
except AttributeError:
    _ABC = abc.ABCMeta('ABC', (object,), {})  # <- Using Python 2 and 3
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
    """Wrapper to call *function* when evaluating the '==' operator."""
    def __init__(self, function, repr_string):
        self._func = function
        self._repr = repr_string

    def __eq__(self, other):
        return self._func(other)

    def __ne__(self, other):  # <- For Python 2.x compatibility.
        return not self.__eq__(other)

    def __repr__(self):
        return self._repr

# Special predicate functions.
_wildcard = lambda x: True
_is_truthy = lambda x: bool(x)
_is_falsy = lambda x: not bool(x)


def _get_predicate_parts(value):
    """Return a 2-tuple containing a function (to use as a predicate)
    and string (to use as a repr value). Return None if *value* can be
    matched with the "==" operator and requires no other special
    handling.
    """
    if isinstance(value, type):
        function = lambda x: (x is value) or isinstance(x, value)
        repr_string = getattr(value, '__name__', repr(value))
    elif callable(value):
        function = lambda x: (x is value) or value(x)
        repr_string = getattr(value, '__name__', repr(value))
    else:
        return None

    return function, repr_string


def _get_matcher(value):
    """Return an object suitable for comparing to other values
    using the "==" operator.

    When special comparison handling is required, returns a
    PredicateMatcher instance. When no special comparison is
    needed, returns the original object unchanged.
    """
    if isinstance(value, type):
        function = lambda x: (x is value) or isinstance(x, value)
        repr_string = getattr(value, '__name__', repr(value))
    elif callable(value):
        function = lambda x: (x is value) or value(x)
        repr_string = getattr(value, '__name__', repr(value))
    elif value is Ellipsis:
        function = _wildcard  # <- Matches everything.
        repr_string = '...'
    elif value is True:
        function = _is_truthy
        repr_string = 'True'
    elif value is False:
        function = _is_falsy
        repr_string = 'False'
    elif isinstance(value, regex_types):
        function = lambda x: (x is value) or (value.search(x) is not None)
        repr_string = 're.compile({0!r})'.format(value.pattern)
    elif isinstance(value, set):
        function = lambda x: (x in value) or (x == value)
        repr_string = repr(value)
    else:
        return value  # <- EXIT!
    return PredicateMatcher(function, repr_string)


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


    class TestTypeParts(unittest.TestCase):
        def test_repr_string(self):
            _, repr_string = _get_predicate_parts(int)
            self.assertEqual(repr_string, 'int')

        def test_function(self):
            function, _ = _get_predicate_parts(int)
            self.assertTrue(function(0))
            self.assertTrue(function(1))
            self.assertFalse(function(0.0))
            self.assertFalse(function(1.0))


    class TestCallableParts(unittest.TestCase):
        def test_repr_string(self):
            def userfunc(x):
                return True
            _, repr_string = _get_predicate_parts(userfunc)
            self.assertEqual(repr_string, 'userfunc')

            userlambda = lambda x: True
            _, repr_string = _get_predicate_parts(userlambda)
            self.assertEqual(repr_string, '<lambda>')

        def test_function(self):
            def divisible3or5(x):  # <- Helper function.
                return (x % 3 == 0) or (x % 5 == 0)
            function, _ = _get_predicate_parts(divisible3or5)

            self.assertFalse(function(1))
            self.assertFalse(function(2))
            self.assertTrue(function(3))
            self.assertFalse(function(4))
            self.assertTrue(function(5))
            self.assertTrue(function(6))

        def test_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            function, _ = _get_predicate_parts(fails_internally)

            with self.assertRaises(TypeError):
                self.assertFalse(function('abc'))

        def test_identity(self):
            def always_false(x):
                return False
            function, _ = _get_predicate_parts(always_false)

            self.assertTrue(function(always_false))

        def test_identity_with_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            function, _ = _get_predicate_parts(fails_internally)

            self.assertTrue(function(fails_internally))


    class TestInheritance(unittest.TestCase):
        def test_inheritance(self):
            self.assertTrue(issubclass(PredicateTuple, PredicateObject))
            self.assertTrue(issubclass(PredicateMatcher, PredicateObject))

    class TestTypeMatcher(unittest.TestCase):
        def test_isinstance(self):
            matcher = _get_matcher(int)

            self.assertTrue(matcher == 0)
            self.assertTrue(matcher == 1)
            self.assertFalse(matcher == 0.0)
            self.assertFalse(matcher == 1.0)

    class TestCallableMatcher(unittest.TestCase):
        def test_equality(self):
            def divisible3or5(x):  # <- Helper function.
                return (x % 3 == 0) or (x % 5 == 0)
            matcher = _get_matcher(divisible3or5)

            self.assertFalse(matcher == 1)
            self.assertFalse(matcher == 2)
            self.assertTrue(matcher == 3)
            self.assertFalse(matcher == 4)
            self.assertTrue(matcher == 5)
            self.assertTrue(matcher == 6)

        def test_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            matcher = _get_matcher(fails_internally)

            with self.assertRaises(TypeError):
                self.assertFalse(matcher == 'abc')

        def test_identity(self):
            def always_false(x):
                return False
            matcher = _get_matcher(always_false)

            self.assertTrue(matcher ==always_false)

        def test_identity_with_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            matcher = _get_matcher(fails_internally)

            self.assertTrue(matcher == fails_internally)

        def test_repr(self):
            def userfunc(x):
                return True
            matcher = _get_matcher(userfunc)
            self.assertEqual(repr(matcher), 'userfunc')

            userlambda = lambda x: True
            matcher = _get_matcher(userlambda)
            self.assertEqual(repr(matcher), '<lambda>')


    class TestRegexMatcher(unittest.TestCase):
        def test_equality(self):
            matcher = _get_matcher(re.compile('(Ch|H)ann?ukk?ah?'))

            self.assertTrue(matcher == 'Happy Hanukkah')
            self.assertTrue(matcher == 'Happy Chanukah')
            self.assertFalse(matcher == 'Merry Christmas')

        def test_error(self):
            matcher = _get_matcher(re.compile('abc'))

            with self.assertRaises(TypeError):
                self.assertFalse(matcher == 123)  # Regex fails with TypeError.

        def test_identity(self):
            regex = re.compile('abc')
            matcher = _get_matcher(regex)

            self.assertTrue(matcher == regex)

        def test_repr(self):
            matcher = _get_matcher(re.compile('abc'))

            self.assertEqual(repr(matcher), "re.compile('abc')")


    class TestSetMatcher(unittest.TestCase):
        def test_equality(self):
            matcher = _get_matcher(set(['a', 'e', 'i', 'o', 'u']))

            self.assertTrue(matcher == 'a')
            self.assertFalse(matcher == 'x')

        def test_whole_set_equality(self):
            matcher = _get_matcher(set(['a', 'b', 'c']))

            self.assertTrue(matcher == set(['a', 'b', 'c']))

        def test_repr(self):
            matcher = _get_matcher(set(['a']))

            self.assertEqual(repr(matcher), repr(set(['a'])))


    class TestEllipsisWildcardMatcher(unittest.TestCase):
        def test_equality(self):
            matcher = _get_matcher(Ellipsis)

            self.assertTrue(matcher == 1)
            self.assertTrue(matcher == object())
            self.assertTrue(matcher == None)

        def test_repr(self):
            matcher = _get_matcher(Ellipsis)

            self.assertEqual(repr(matcher), '...')


    class TestTruthyMatcher(unittest.TestCase):
        def test_equality(self):
            matcher = _get_matcher(True)

            self.assertTrue(matcher == 'x')
            self.assertTrue(matcher == 1.0)
            self.assertTrue(matcher == [1])
            self.assertTrue(matcher == range(1))

            self.assertFalse(matcher == '')
            self.assertFalse(matcher == 0.0)
            self.assertFalse(matcher == [])
            self.assertFalse(matcher == range(0))

        def test_number_one(self):
            matcher = _get_matcher(1)  # <- Should not match True

            self.assertTrue(matcher == 1.0)
            self.assertFalse(matcher == 'x')

        def test_repr(self):
            matcher = _get_matcher(True)

            self.assertEqual(repr(matcher), 'True')


    class TestFalsyMatcher(unittest.TestCase):
        def test_equality(self):
            matcher = _get_matcher(False)

            self.assertFalse(matcher == 'x')
            self.assertFalse(matcher == 1.0)
            self.assertFalse(matcher == [1])
            self.assertFalse(matcher == range(1))

            self.assertTrue(matcher == '')
            self.assertTrue(matcher == 0.0)
            self.assertTrue(matcher == [])
            self.assertTrue(matcher == range(0))

        def test_number_zero(self):
            matcher = _get_matcher(0)  # <- Should not match False

            self.assertTrue(matcher == 0.0)
            self.assertFalse(matcher == '')

        def test_repr(self):
            matcher = _get_matcher(False)

            self.assertEqual(repr(matcher), 'False')


    class TestGetPredicate(unittest.TestCase):
        def assertIsInstance(self, obj, cls, msg=None):  # New in Python 3.2.
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (safe_repr(obj), cls)
                self.fail(self._formatMessage(msg, standardMsg))

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
