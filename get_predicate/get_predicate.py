#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re


regex_types = type(re.compile(''))

try:
    callable  # Removed from 3.0 and 3.1, added back in 3.2.
except NameError:
    def callable(obj):
        parent_types = type(obj).__mro__
        return any('__call__' in typ.__dict__ for typ in parent_types)


class EqualityAdapter(object):
    """Wrapper to call *func* when evaluating the '==' operator."""
    def __init__(self, func, name):
        self._func = func
        self._name = name

    def __eq__(self, other):
        return self._func(other)

    def __repr__(self):
        return self._name


class get_predicate(object):
    """Return a predicate function made from the given *obj*."""
    def __new__(cls, obj):
        if isinstance(obj, tuple):
            equality_object =  tuple(cls._adapt(x) for x in obj)
        else:
            equality_object = cls._adapt(obj)

        def predicate(x):
            return equality_object == x
        predicate.__name__ = repr(equality_object)

        return predicate

    @staticmethod
    def _adapt(value):
        """Return an adapter object whose behavior is triggered by
        the '==' operator.
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
        return EqualityAdapter(func, name)


if __name__ == '__main__':
    import unittest


    class TestAdaptedCallable(unittest.TestCase):
        def test_equality(self):
            def divisible3or5(x):  # <- Helper function.
                return (x % 3 == 0) or (x % 5 == 0)
            adapted = get_predicate._adapt(divisible3or5)

            self.assertFalse(adapted == 1)
            self.assertFalse(adapted == 2)
            self.assertTrue(adapted == 3)
            self.assertFalse(adapted == 4)
            self.assertTrue(adapted == 5)
            self.assertTrue(adapted == 6)

        def test_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            adapted = get_predicate._adapt(fails_internally)

            with self.assertRaises(TypeError):
                self.assertFalse(adapted == 'abc')

        def test_identity(self):
            def always_false(x):
                return False
            adapted = get_predicate._adapt(always_false)

            self.assertTrue(adapted ==always_false)

        def test_identity_with_error(self):
            def fails_internally(x):  # <- Helper function.
                raise TypeError('raising an error')
            adapted = get_predicate._adapt(fails_internally)

            self.assertTrue(adapted == fails_internally)

        def test_repr(self):
            def userfunc(x):
                return True
            adapted = get_predicate._adapt(userfunc)
            self.assertEqual(repr(adapted), 'userfunc')

            userlambda = lambda x: True
            adapted = get_predicate._adapt(userlambda)
            self.assertEqual(repr(adapted), '<lambda>')


    class TestAdaptedRegex(unittest.TestCase):
        def test_equality(self):
            adapted = get_predicate._adapt(re.compile('(Ch|H)ann?ukk?ah?'))

            self.assertTrue(adapted == 'Happy Hanukkah')
            self.assertTrue(adapted == 'Happy Chanukah')
            self.assertFalse(adapted == 'Merry Christmas')

        def test_error(self):
            adapted = get_predicate._adapt(re.compile('abc'))

            with self.assertRaises(TypeError):
                self.assertFalse(adapted == 123)  # Regex fails with TypeError.

        def test_identity(self):
            regex = re.compile('abc')
            adapted = get_predicate._adapt(regex)

            self.assertTrue(adapted == regex)

        def test_repr(self):
            adapted = get_predicate._adapt(re.compile('abc'))

            self.assertEqual(repr(adapted), "re.compile('abc')")


    class TestAdaptedSet(unittest.TestCase):
        def test_equality(self):
            adapted = get_predicate._adapt(set(['a', 'e', 'i', 'o', 'u']))

            self.assertTrue(adapted == 'a')
            self.assertFalse(adapted == 'x')

        def test_whole_set_equality(self):
            adapted = get_predicate._adapt(set(['a', 'b', 'c']))

            self.assertTrue(adapted == set(['a', 'b', 'c']))

        def test_repr(self):
            adapted = get_predicate._adapt(set(['a']))

            self.assertEqual(repr(adapted), repr(set(['a'])))


    class TestAdaptedEllipsisWildcard(unittest.TestCase):
        def test_equality(self):
            adapted = get_predicate._adapt(Ellipsis)

            self.assertTrue(adapted == 1)
            self.assertTrue(adapted == object())
            self.assertTrue(adapted == None)

        def test_repr(self):
            adapted = get_predicate._adapt(Ellipsis)

            self.assertEqual(repr(adapted), '...')


    class TestGetPredicate(unittest.TestCase):
        def test_single_object(self):
            predicate = get_predicate(1)

            self.assertTrue(predicate(1))
            self.assertFalse(predicate(2))
            self.assertEqual(predicate.__name__, '1')

        def test_tuple_of_objects(self):
            predicate = get_predicate(('A', 1))

            self.assertTrue(predicate(('A', 1)))
            self.assertFalse(predicate(('A', 2)))
            self.assertFalse(predicate(('B', 1)))
            self.assertEqual(predicate.__name__, "('A', 1)")

        def test_tuple_of_all_adapter_options(self):
            def mycallable(x):  # <- Helper function.
                return x == '_'

            myregex = re.compile('_')

            myset = set(['_'])

            predicate = get_predicate(
                (mycallable,  myregex, myset, '_', Ellipsis)
            )

            self.assertTrue(predicate(('_', '_', '_', '_', '_')))   # <- Passes all conditions.
            self.assertFalse(predicate(('X', '_', '_', '_', '_')))  # <- Callable returns False.
            self.assertFalse(predicate(('_', 'X', '_', '_', '_')))  # <- Regex has no match.
            self.assertFalse(predicate(('_', '_', 'X', '_', '_')))  # <- Not in set.
            self.assertFalse(predicate(('_', '_', '_', 'X', '_')))  # <- Does not equal string.
            self.assertTrue(predicate(('_', '_', '_', '_', 'X')))   # <- Passes all conditions (wildcard).

            expected = "(mycallable, re.compile('_'), {0!r}, '_', ...)".format(myset)
            self.assertEqual(predicate.__name__, expected)


    unittest.main()
