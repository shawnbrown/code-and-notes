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


class MatcherBase(abc.ABC):
    """Base class for objects that implement rich predicate matching."""
    @abc.abstractmethod
    def __repr__(self):
        return super(MatcherBase, self).__repr__()


class MatcherObject(MatcherBase):
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


class MatcherTuple(MatcherBase, tuple):
    """Wrapper to mark tuples that contain one or more MatcherObject
    instances.
    """
    pass


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
        return None

    return function, repr_string


def _get_matcher_or_original(value):
    parts = _get_predicate_parts(value)
    if parts:
        return MatcherObject(*parts)
    return value


def get_matcher(obj):
    """Return an object suitable for comparing to other objects
    using the "==" operator.

    If the original object is already suitable for this purpose,
    it will be returned unchanged. If special comparison handling
    is implemented, a PredicateObject will be returned instead.
    """
    if isinstance(obj, tuple):
        predicate = tuple(_get_matcher_or_original(x) for x in obj)
        for x in predicate:
            if isinstance(x, MatcherBase):
                return MatcherTuple(predicate)  # <- Wrapper.
        return obj  # <- Orignal reference.

    return _get_matcher_or_original(obj)


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
            def always_false(x):  # <- Helper function.
                return False

            function, _ = _get_predicate_parts(always_false)
            self.assertTrue(function(always_false))

        def test_identity_with_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')

            function, _ = _get_predicate_parts(fails_internally)
            self.assertTrue(function(fails_internally))


    class TestEllipsisWildcardParts(unittest.TestCase):
        def test_repr_string(self):
            _, repr_string = _get_predicate_parts(Ellipsis)
            self.assertEqual(repr_string, '...')

        def test_function(self):
            function, _ = _get_predicate_parts(Ellipsis)
            self.assertTrue(function(1))
            self.assertTrue(function(object()))
            self.assertTrue(function(None))


    class TestTruthyParts(unittest.TestCase):
        def setUp(self):
            function, repr_string = _get_predicate_parts(True)
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
            self.assertIsNone(_get_predicate_parts(1))


    class TestFalsyParts(unittest.TestCase):
        def setUp(self):
            function, repr_string = _get_predicate_parts(False)
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
            self.assertIsNone(_get_predicate_parts(0))


    class TestRegexParts(unittest.TestCase):
        def setUp(self):
            regex = re.compile('(Ch|H)ann?ukk?ah?')
            function, repr_string = _get_predicate_parts(regex)
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
            with self.assertRaises(TypeError):
                self.assertFalse(self.function(123))  # Regex fails with TypeError.

        def test_identity(self):
            self.assertTrue(self.function(self.regex))


    class TestSetParts(unittest.TestCase):
        def test_repr_string(self):
            myset = set(['a'])
            _, repr_string = _get_predicate_parts(myset)
            self.assertEqual(repr_string, repr(myset))

        def test_function(self):
            function, _ = _get_predicate_parts(set(['abc', 'def']))
            self.assertTrue(function('abc'))
            self.assertFalse(function('xyz'))

        def test_whole_set_equality(self):
            function, _ = _get_predicate_parts(set(['abc', 'def']))
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


    unittest.main()
