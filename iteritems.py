# -*- coding: utf-8 -*-
try:
    from abc import ABC  # New in version 3.4.
except ImportError:
    # Define ABC using Python 2 and 3 compatible syntax.
    from abc import ABCMeta as _ABCMeta
    ABC = _ABCMeta('ABC', (object,), {})

try:
    from collections.abc import ItemsView
    from collections.abc import Iterator
    from collections.abc import Mapping
except ImportError:
    from collections import ItemsView
    from collections import Iterator
    from collections import Mapping


_iteritems_type = type(getattr(dict(), 'iteritems', dict().items)())


class IterItems(ABC):
    """A wrapper class to identify iterables that are appropriate for
    constructing a dictionary or other mapping.
    """
    def __init__(self, iterable):
        """Initialize self."""
        while isinstance(iterable, IterItems) \
                and hasattr(iterable, '__wrapped__'):
            iterable = iterable.__wrapped__

        self.__wrapped__ = iterable

    def __iter__(self):
        iterable = self.__wrapped__

        if not isinstance(iterable, Mapping):
            return iter(iterable)

        if hasattr(iterable, 'iteritems'):
            return iterable.iteritems()
        return iter(iterable.items())

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{0}({1!r})'.format(cls_name, self.__wrapped__)

    @classmethod
    def __subclasshook__(cls, C):
        if cls is IterItems:
            if issubclass(C, (ItemsView, _iteritems_type)):
                return True
        return NotImplemented


if __name__ == '__main__':
    import unittest


    class TestIterItems(unittest.TestCase):
        def test_non_exhaustible(self):
            items_list = [('a', 1), ('b', 2)]  # <- Non-exhaustible iterable.

            items = IterItems(items_list)
            self.assertIsNot(iter(items), iter(items))
            self.assertEqual(list(items), items_list)
            self.assertEqual(list(items), items_list, msg='not exhaustible')

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
            self.assertEqual(set(items), set([('a', 1), ('b', 2)]), msg='not exhaustible')

        def test_empty_iterable(self):
            items = IterItems(iter([]))
            self.assertEqual(list(items), [])

        def test_repr(self):
            items = IterItems([1, 2])
            self.assertEqual(repr(items), "IterItems([1, 2])")

            generator = (x for x in [1, 2])
            items = IterItems(generator)
            self.assertEqual(repr(items), 'IterItems({0!r})'.format(generator))

            items = IterItems({'a': 1})
            self.assertEqual(repr(items), "IterItems({'a': 1})")

        def test_subclasshook(self):
            items = IterItems(iter([]))
            self.assertIsInstance(items, IterItems)

            try:
                items = dict([]).iteritems()  # <- For Python 2
            except AttributeError:
                items = dict([]).items()  # <- For Python 3
            self.assertIsInstance(items, IterItems)


    class TestVerifiedItems(unittest.TestCase):
        @unittest.skip('verified_items() not implemented')
        def test_invalid_input(self):
            source = ['x', 1, 'y', 2]
            with self.assertRaises(TypeError):
                normalized = verified_items(source)

            source = [{'x': 1}, {'y': 2}]
            with self.assertRaises(TypeError):
                normalized = verified_items(source)


    unittest.main()
