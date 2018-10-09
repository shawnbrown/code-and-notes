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


def _check_type(type_, value):
    """Return true if *value* is an instance of the specified type
    or if *value* is the specified type.
    """
    return value is type_ or isinstance(value, type_)


def _check_callable(func, value):
    """Return true if func(value) returns is true or if *func* is
    *value*.
    """
    return value is func or func(value)


def _check_wildcard(value):
    """Always returns true."""
    return True


def _check_truthy(value):
    """Return true if *value* is truthy."""
    return bool(value)


def _check_falsy(value):
    """Return true if *value* is falsy."""
    return not bool(value)


def _check_regex(regex, value):
    """Return true if *value* matches regex."""
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


def _check_set(set_, value):
    """Return true if *value* is a member of the given set or if
    the *value* is equal to the given set."""
    return value in set_ or value == set_


def _get_matcher_parts(obj):
    """Return a 2-tuple containing a handler function (to check for
    matches) and a string (to use for displaying a user-readable
    value). Return None if *obj* can be matched with the "==" operator
    and requires no other special handling.
    """
    if isinstance(obj, type):
        pred_handler = lambda x: _check_type(obj, x)
        repr_string = getattr(obj, '__name__', repr(obj))
    elif callable(obj):
        pred_handler = lambda x: _check_callable(obj, x)
        repr_string = getattr(obj, '__name__', repr(obj))
    elif obj is Ellipsis:
        pred_handler = _check_wildcard  # <- Matches everything.
        repr_string = '...'
    elif obj is True:
        pred_handler = _check_truthy
        repr_string = 'True'
    elif obj is False:
        pred_handler = _check_falsy
        repr_string = 'False'
    elif isinstance(obj, regex_types):
        pred_handler = lambda x: _check_regex(obj, x)
        repr_string = 're.compile({0!r})'.format(obj.pattern)
    elif isinstance(obj, set):
        pred_handler = lambda x: _check_set(obj, x)
        repr_string = repr(obj)
    else:
        return None

    return pred_handler, repr_string


def _get_matcher_or_original(obj):
    parts = _get_matcher_parts(obj)
    if parts:
        return MatcherObject(*parts)
    return obj


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
        if isinstance(obj, Predicate):
            self.obj = obj.obj
            self._pred_handler = obj._pred_handler
            self._repr_string = obj._repr_string
            self._inverted = obj._inverted
        else:
            self.obj = obj
            matcher = get_matcher(obj)
            try:
                self._pred_handler = matcher.__eq__
            except AttributeError:
                self._pred_handler = lambda other: matcher == other
                # Above: In Python 2, some built-in objects
                # do not have an explicit __eq__() method.
            self._repr_string = repr(matcher)
            self._inverted = False

    def __call__(self, other):
        result = self._pred_handler(other)
        if self._inverted:
            return not result
        return result

    def __invert__(self):
        new_pred = self.__class__(self)
        new_pred._inverted = not self._inverted
        return new_pred

    def __repr__(self):
        cls_name = self.__class__.__name__
        inverted = '~' if self._inverted else ''
        return '{0}{1}({2})'.format(inverted, cls_name, self._repr_string)

    def __str__(self):
        inverted = 'not ' if self._inverted else ''
        return '{0}{1}'.format(inverted, self._repr_string)
