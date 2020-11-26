#!/usr/bin/env python3
"""
=====================
pretty_timedelta_repr
=====================

Takes a timedelta instance and returns a more human-readable repr
than is available from timedelta's built-in repr.

Copyright 2020 Shawn Brown. All rights reserved.
License: http://www.apache.org/licenses/LICENSE-2.0
"""


def pretty_timedelta_repr(delta, extras=None):
    """Supports more human-readable reprs for timedelta objects.

    Negative values are presented naturally:

        >>> pretty_timedelta_repr(datetime.timedelta(microseconds=-1))
        'datetime.timedelta(microseconds=-1)'

    Compare this with timedelta's default repr:

        >>> repr(datetime.timedelta(microseconds=-1))
        'datetime.timedelta(days=-1, seconds=86399, microseconds=999999)'

    Using the optional *extras* argument, you can specify a string of
    comma-separated units to use when constructing the repr. Possible
    values are 'weeks', 'hours', 'minutes', and 'milliseconds'.
    Required units ('days', 'seconds', and 'microseconds') will be
    included as necessary.

    Below, we specify extra units ("hours" and "minutes") to produce
    a more intuitive repr:

        >>> delta = datetime.timedelta(seconds=29156)
        >>> pretty_timedelta_repr(delta, extras='hours,minutes')
        'datetime.timedelta(hours=8, minutes=5, seconds=56)'
    """
    # Note: timedeltas are normalized so that negative values
    # always have a negative 'days' attribute. For example:
    #
    #    >>> datetime.timedelta(microseconds=-1)
    #    datetime.timedelta(days=-1, seconds=86399, microseconds=999999)
    if delta.days < 0:
        isnegative = True
        delta = -delta  # Flip sign get rid of negative value normalization.
    else:
        isnegative = False

    if extras:
        extras = set(x.strip() for x in extras.split(','))
    else:
        extras = set()

    days = delta.days
    seconds = delta.seconds
    microseconds = delta.microseconds

    if 'weeks' in extras:
        weeks, days = divmod(days, 7)
    else:
        weeks = 0

    if 'hours' in extras:
        hours, seconds = divmod(seconds, 3600)
    else:
        hours = 0

    if 'minutes' in extras:
        minutes, seconds = divmod(seconds, 60)
    else:
        minutes = 0

    if 'milliseconds' in extras:
        milliseconds, microseconds = divmod(microseconds, 1000)
    else:
        milliseconds = 0

    if isnegative:
        weeks = -weeks
        days = -days
        hours = -hours
        minutes = -minutes
        seconds = -seconds
        milliseconds = -milliseconds
        microseconds = -microseconds

    args = []
    if weeks:
        args.append('weeks=%d' % weeks)
    if days:
        args.append('days=%d' % days)
    if hours:
        args.append('hours=%d' % hours)
    if minutes:
        args.append('minutes=%d' % minutes)
    if seconds:
        args.append('seconds=%d' % seconds)
    if milliseconds:
        args.append('milliseconds=%d' % milliseconds)
    if microseconds:
        args.append('microseconds=%d' % microseconds)
    if not args:
        args.append('0')
    return '%s.%s(%s)' % (delta.__class__.__module__,
                          delta.__class__.__qualname__,
                          ', '.join(args))


if __name__ == '__main__':
    from datetime import timedelta
    import unittest


    class TestPrettyTimedeltaRepr(unittest.TestCase):
        def test_no_change(self):
            """When the units align to timedelta's internal
            normalization, the pretty repr will be the same
            as the built-in repr for positve timedeltas.
            """
            delta = timedelta(days=6, seconds=27, microseconds=100)
            self.assertEqual(pretty_timedelta_repr(delta), repr(delta))

        def test_default_behavior(self):
            """When there are no *extras*, positive deltas should have
            the same repr as timedelta's native repr.
            """
            delta = timedelta(days=11, seconds=49600)

            actual = pretty_timedelta_repr(delta, extras=None)  # <- No extras!
            expected = 'datetime.timedelta(days=11, seconds=49600)'
            self.assertEqual(actual, expected)

        def test_extras_weeks(self):
            """Test breaking out units into 'weeks'."""
            delta = timedelta(days=11, seconds=49600)

            actual = pretty_timedelta_repr(delta, extras='weeks')
            expected = 'datetime.timedelta(weeks=1, days=4, seconds=49600)'
            self.assertEqual(actual, expected)

        def test_extras_hours_minutes(self):
            """The *extras* argument defauls to 'hours,minutes'."""
            delta = timedelta(days=11, seconds=49600)

            actual = pretty_timedelta_repr(delta, extras='hours,minutes')
            expected = 'datetime.timedelta(days=11, hours=13, minutes=46, seconds=40)'
            self.assertEqual(actual, expected)

        def test_negative_delta_default_behavior(self):
            delta = timedelta(days=-9, seconds=-49600)

            actual = pretty_timedelta_repr(delta)
            expected = 'datetime.timedelta(days=-9, seconds=-49600)'
            self.assertEqual(actual, expected)

        def test_negative_delta_extras_hours_minutes(self):
            """The builtin repr for timedelta is awful for readability,
            the pretty repr is more natural to read.
            """
            delta = timedelta(microseconds=-1)

            actual = pretty_timedelta_repr(delta, extras='hours,minutes')
            expected = 'datetime.timedelta(microseconds=-1)'
            self.assertEqual(actual, expected)

            delta = timedelta(days=-9, seconds=-49600)

            actual = pretty_timedelta_repr(delta, extras='hours,minutes')
            expected = 'datetime.timedelta(days=-9, hours=-13, minutes=-46, seconds=-40)'
            self.assertEqual(actual, expected)

        def test_negative_delta_custom_extras(self):
            """Test breaking out units into 'weeks'."""
            delta = timedelta(days=-9, seconds=-49600)

            actual = pretty_timedelta_repr(delta, extras='weeks')
            expected = 'datetime.timedelta(weeks=-1, days=-2, seconds=-49600)'
            self.assertEqual(actual, expected)


    unittest.main()
