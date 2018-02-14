#!/usr/bin/env python
# -*- coding: utf-8 -*-
import abc
import re


try:
    string_types = basestring
except NameError:
    string_types = str

regex_types = type(re.compile(''))

try:
    callable = callable  # Removed from 3.0 and 3.1, added back in 3.2.
except NameError:
    def callable(obj):
        parent_types = type(obj).__mro__
        return any('__call__' in typ.__dict__ for typ in parent_types)

try:
    abc.ABC  # New in version 3.4.
except AttributeError:
    abc.ABC = abc.ABCMeta('ABC', (object,), {})  # <- Using Python 2 and 3
                                                 #    compatible syntax.


class EqualityBase(abc.ABC):
    def __init__(self, obj):
        self.obj = obj

    @abc.abstractmethod
    def __eq__(self, other):
        return super(PredicateOperator, self).__eq__(other)

    @abc.abstractmethod
    def __repr__(self):
        return super(PredicateOperator, self).__repr__()


class EqualityCallable(EqualityBase):
    def __eq__(self, other):
        try:
            return (self.obj is other) or self.obj(other)
        except Exception:
            return False

    def __repr__(self):
        return getattr(self.obj, '__name__', repr(self.obj))


class EqualityRegex(EqualityBase):
    def __eq__(self, other):
        try:
            return self.obj.search(other) is not None
        except TypeError:
            return self.obj is other

    def __repr__(self):
        return 're.compile({0!r})'.format(self.obj.pattern)


class EqualityContains(EqualityBase):
    def __eq__(self, other):
        return (other in self.obj) or (other is self.obj)

    def __repr__(self):
        return repr(self.obj)


class EqualityWildcard(EqualityBase):
    def __init__(self):
        self.obj = Ellipsis

    def __eq__(self, other):
        return True

    def __repr__(self):
        return '...'


class Predicate(object):
    def __init__(self, obj):
        if isinstance(obj, tuple):
            self.__wrapped__ = tuple(self._get_single_equality(x) for x in obj)
        else:
            self.__wrapped__ = self._get_single_equality(obj)

    def __call__(self, other):
        return self.__wrapped__ == other

    def __eq__(self, other):
        return self.__wrapped__ == other

    def __repr__(self):
        return '{0}({1!r})'.format(self.__class__.__name__, self.__wrapped__)

    @staticmethod
    def _get_single_equality(obj):
        if obj is Ellipsis:
            return EqualityWildcard()

        if callable(obj):
            return EqualityCallable(obj)

        if isinstance(obj, regex_types):
            return EqualityRegex(obj)

        if isinstance(obj, set):
            return EqualityContains(obj)

        return obj


if __name__ == '__main__':
    import unittest

    class TestEqualityCallable(unittest.TestCase):
        def test_comparison(self):

            def divisible3or5(x):  # <- Helper function.
                return (x % 3 == 0) or (x % 5 == 0)

            eq_obj = EqualityCallable(divisible3or5)

            self.assertFalse(eq_obj == 1)
            self.assertFalse(eq_obj == 2)
            self.assertTrue(eq_obj == 3)
            self.assertFalse(eq_obj == 4)
            self.assertTrue(eq_obj == 5)
            self.assertTrue(eq_obj == 6)

        def test_callable_error(self):

            def fails_internally(x):  # <- Helper function.
                raise Exception('raising an error')

            eq_obj = EqualityCallable(fails_internally)

            self.assertFalse(eq_obj == 'abc')

        def test_identity_comparison(self):

            def always_false(x):
                return False

            eq_obj = EqualityCallable(always_false)

            self.assertTrue(eq_obj == always_false)

        def test_repr(self):

            def userfunc(x):
                return True

            eq_obj = EqualityCallable(userfunc)
            self.assertEqual(repr(eq_obj), 'userfunc')

            userlambda = lambda x: True
            eq_obj = EqualityCallable(userlambda)
            self.assertEqual(repr(eq_obj), '<lambda>')


    class TestEqualityRegex(unittest.TestCase):
        def test_regex_search(self):
            equality_obj = EqualityRegex(re.compile('(Ch|H)ann?ukk?ah?'))

            self.assertTrue(equality_obj == 'Happy Hanukkah')
            self.assertTrue(equality_obj == 'Happy Chanukah')
            self.assertFalse(equality_obj == 'Merry Christmas')

        def test_regex_error(self):
            equality_obj = EqualityRegex(re.compile('abc'))

            self.assertFalse(equality_obj == 123)  # Regex fails with TypeError.

        def test_identity_comparison(self):
            regex = re.compile('abc')
            equality_obj = EqualityRegex(regex)

            self.assertTrue(equality_obj == regex)

        def test_repr(self):
            equality_obj = EqualityRegex(re.compile('abc'))

            self.assertEqual(repr(equality_obj), "re.compile('abc')")


    class TestEqualityContains(unittest.TestCase):
        def test_contains(self):
            equality_obj = EqualityContains(set(['a', 'e', 'i', 'o', 'u']))

            self.assertTrue(equality_obj == 'a')
            self.assertFalse(equality_obj == 'x')

        def test_identity_comparison(self):
            myset = set(['a', 'b', 'c'])
            equality_obj = EqualityContains(myset)

            self.assertTrue(equality_obj == myset)

        def test_repr(self):
            equality_obj = EqualityContains(set(['a']))

            self.assertEqual(repr(equality_obj), repr(set(['a'])))


    class TestEqualityWildcard(unittest.TestCase):
        def test_wildcard(self):
            equality_obj = EqualityWildcard()

            self.assertTrue(equality_obj == 1)
            self.assertTrue(equality_obj == object())
            self.assertTrue(equality_obj == None)

        def test_repr(self):
            equality_obj = EqualityWildcard()

            self.assertEqual(repr(equality_obj), '...')


    class TestPredicate(unittest.TestCase):
        def test_single_object(self):
            func = Predicate(1)

            self.assertTrue(func(1))
            self.assertFalse(func(2))

            self.assertTrue(func == 1)
            self.assertFalse(func == 2)

        def test_tuple(self):
            composite_object = Predicate(('A', ...))
            self.assertTrue(composite_object == ('A', 1))
            self.assertTrue(composite_object == ('A', 2))
            self.assertFalse(composite_object == ('B', 1))

            def divisible3or5(x):  # <- Helper function.
                return (x % 3 == 0) or (x % 5 == 0)
            composite_object = Predicate((..., divisible3or5))
            self.assertTrue(composite_object == ('A', 3))
            self.assertFalse(composite_object == ('B', 4))
            self.assertTrue(composite_object == ('C', 5))


    unittest.main()
