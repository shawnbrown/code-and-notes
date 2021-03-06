# -*- coding: utf-8 -*-
try:
    from abc import ABC  # New in version 3.4.
except ImportError:
    # Define ABC using Python 2 and 3 compatible syntax.
    from abc import ABCMeta as _ABCMeta
    ABC = _ABCMeta('ABC', (object,), {})

try:
    from collections.abc import ItemsView
    from collections.abc import Iterable
    from collections.abc import Mapping
except ImportError:
    from collections import ItemsView
    from collections import Iterable
    from collections import Mapping


class IterItems(ABC):
    """An iterator that returns item-pairs appropriate for constructing
    a dictionary or other mapping. The given *items_or_mapping* should
    be an iterable of key/value pairs or a mapping.

    .. warning::

        :class:`IterItems` does no type checking or verification of
        the iterable's contents. When iterated over, it should yield
        only those values necessary for constructing a :py:class:`dict`
        or other mapping and no more---no duplicate or unhashable keys.
    """
    def __init__(self, items_or_mapping):
        """Initialize self."""
        if not isinstance(items_or_mapping, (Iterable, Mapping)):
            msg = 'expected iterable or mapping, got {0!r}'
            raise TypeError(msg.format(items_or_mapping.__class__.__name__))

        if isinstance(items_or_mapping, Mapping):
            if hasattr(items_or_mapping, 'iteritems'):
                items = items_or_mapping.iteritems()
            else:
                items = items_or_mapping.items()
        else:
            items = items_or_mapping
            while isinstance(items, IterItems) and hasattr(items, '__wrapped__'):
                items = items.__wrapped__

        self.__wrapped__ = iter(items)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{0}({1!r})'.format(cls_name, self.__wrapped__)

    # Set iteritems type as a class attribute.
    _iteritems_type = type(getattr(dict(), 'iteritems', dict().items)())

    @classmethod
    def __subclasshook__(cls, C):
        if cls is IterItems:
            if issubclass(C, (ItemsView, cls._iteritems_type, enumerate)):
                return True
        return NotImplemented


if __name__ == '__main__':
    import unittest

    try:
        unittest.TestCase.assertRaisesRegex
    except AttributeError:
        unittest.TestCase.assertRaisesRegex = \
            unittest.TestCase.assertRaisesRegexp


    class TestIterItems(unittest.TestCase):
        def test_type_error(self):
            regex = "expected iterable or mapping, got 'int'"
            with self.assertRaisesRegex(TypeError, regex):
                IterItems(123)

        def test_non_exhaustible(self):
            items_list = [('a', 1), ('b', 2)]  # <- Non-exhaustible input.

            items = IterItems(items_list)
            self.assertIs(iter(items), iter(items), msg='exhaustible output')
            self.assertEqual(list(items), items_list)
            self.assertEqual(list(items), [], msg='already exhausted')

        def test_exhaustible(self):
            items_iter = iter([('a', 1), ('b', 2)])  # <- Exhaustible iterator.

            items = IterItems(items_iter)
            self.assertIs(iter(items), iter(items))
            self.assertEqual(list(items), [('a', 1), ('b', 2)])
            self.assertEqual(list(items), [], msg='already exhausted')

        def test_dict(self):
            mapping = {'a': 1, 'b': 2}

            items = IterItems(mapping)
            self.assertEqual(set(items), set([('a', 1), ('b', 2)]))
            self.assertEqual(set(items), set(), msg='already exhausted')

        def test_dictitems(self):
            dic = {'a': 1}

            if hasattr(dic, 'iteritems'):  # <- Python 2
                dic_items = dic.iteritems()

                items = IterItems(dic_items)
                self.assertEqual(list(items), [('a', 1)])
                self.assertEqual(list(items), [], msg='already exhausted')

            dic_items = dic.items()

            items = IterItems(dic_items)
            self.assertEqual(list(items), [('a', 1)])
            self.assertEqual(list(items), [], msg='already exhausted')

        def test_empty_iterable(self):
            empty = iter([])

            items = IterItems(empty)
            self.assertEqual(list(items), [])

        def test_repr(self):
            items = IterItems([1, 2])

            repr_part = repr(iter([])).partition(' ')[0]
            repr_start = 'IterItems({0}'.format(repr_part)
            self.assertTrue(repr(items).startswith(repr_start))

            generator = (x for x in [1, 2])
            items = IterItems(generator)
            self.assertEqual(repr(items), 'IterItems({0!r})'.format(generator))

        def test_subclasshook(self):
            items = IterItems(iter([]))
            self.assertIsInstance(items, IterItems)

            try:
                items = dict([]).iteritems()  # <- For Python 2
            except AttributeError:
                items = dict([]).items()  # <- For Python 3
            self.assertIsInstance(items, IterItems)

            items = enumerate([])
            self.assertIsInstance(items, IterItems)

        def test_virtual_subclass(self):
            class OtherClass(object):
                pass

            oth_cls = OtherClass()

            IterItems.register(OtherClass)  # <- Register virtual subclass.
            self.assertIsInstance(oth_cls, IterItems)


    unittest.main()
