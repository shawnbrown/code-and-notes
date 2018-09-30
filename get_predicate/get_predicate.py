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


def _type_predicate(type_, value):
    """Predicate function that returns True if value is of specified
    type.
    """
    return value is type_ or isinstance(value, type_)


def _callable_predicate(func, value):
    """Predicate function that returns True if func(value) is true."""
    return value is func or func(value)


def _wildcard_predicate(value):
    """Predicate function that always returns True."""
    return True


def _truthy_predicate(value):
    """Predicate function that returns True if value is truthy."""
    return bool(value)


def _falsy_predicate(value):
    """Predicate function that returns True if value is falsy."""
    return not bool(value)


def _regex_predicate(regex, value):
    """Predicate function that returns True if value matches regex."""
    try:
        return regex.search(value) is not None
    except TypeError:
        if value is regex:
            return True  # <- EXIT!

        value_repr = repr(value)
        if len(value_repr) > 45:
            value_repr = value_repr[:42] + '...'
        msg = 'expected string or bytes-like object, got {0}: {1}'
        exc = TypeError(msg.format(value.__class__.__name__, value_repr))
        exc.__cause__ = None
        raise exc


def _set_predicate(set_, value):
    """Predicate function that returns True if func(value) is true."""
    return value in set_ or value == set_


def _get_matcher_parts(value):
    """Return a 2-tuple containing a function (to use as a predicate)
    and string (to use for displaying a user-readable value). Return
    None if *value* can be matched with the "==" operator and requires
    no other special handling.
    """
    if isinstance(value, type):
        pred_function = lambda x: _type_predicate(value, x)
        repr_string = getattr(value, '__name__', repr(value))
    elif callable(value):
        pred_function = lambda x: _callable_predicate(value, x)
        repr_string = getattr(value, '__name__', repr(value))
    elif value is Ellipsis:
        pred_function = _wildcard_predicate  # <- Matches everything.
        repr_string = '...'
    elif value is True:
        pred_function = _truthy_predicate
        repr_string = 'True'
    elif value is False:
        pred_function = _falsy_predicate
        repr_string = 'False'
    elif isinstance(value, regex_types):
        pred_function = lambda x: _regex_predicate(value, x)
        repr_string = 're.compile({0!r})'.format(value.pattern)
    elif isinstance(value, set):
        pred_function = lambda x: _set_predicate(value, x)
        repr_string = repr(value)
    else:
        return None

    return pred_function, repr_string


def _get_matcher_or_original(value):
    parts = _get_matcher_parts(value)
    if parts:
        return MatcherObject(*parts)
    return value


def get_matcher(obj):
    """Return an object suitable for comparing against other objects
    using the "==" operator.

    If special comparison handling is implemented, a MatcherObject or
    MatcherTuple will be returned. If the object is already suitable
    for this purpose, the original object will be returned unchanged.
    """
    if isinstance(obj, tuple):
        matcher = tuple(_get_matcher_or_original(x) for x in obj)
        for x in matcher:
            if isinstance(x, MatcherBase):
                return MatcherTuple(matcher)  # <- Wrapper.
        return obj  # <- Orignal reference.

    return _get_matcher_or_original(obj)


class Predicate(object):
    """Returns a callable object that can be used as a functional
    predicate.
    """
    def __init__(self, obj):
        matcher = get_matcher(obj)
        self._pred_function = matcher.__eq__
        self._repr_string = repr(matcher)
        self._inverted = False

    def __call__(self, other):
        result = self._pred_function(other)
        if self._inverted:
            return not result
        return result

    def __invert__(self):
        new_pred = self.__class__.__new__(self.__class__)
        new_pred._pred_function = self._pred_function
        new_pred._repr_string = self._repr_string
        new_pred._inverted = not self._inverted
        return new_pred

    def __repr__(self):
        cls_name = self.__class__.__name__
        inverted = '~' if self._inverted else ''
        return '{0}{1}({2})'.format(inverted, cls_name, self._repr_string)


if __name__ == '__main__':
    import unittest


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


    unittest.main()
