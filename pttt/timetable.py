import operator
import functools
import itertools
from datetime import datetime, timedelta

class TimetableError(Exception):
    pass

class Label:
    
    def __init__(self, key, name=None):
        self.key = key
        self.name = name if name is not None else key

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s<%s>" % (self.name, self.key)

class LabelSet(dict):

    def __setitem__(self, key, val):
        if key in self:
            raise TimetableError("Duplicate label: %s" % key)
        super().__setitem__(key, val)

    def __missing__(self, key):
        ret = Label(key)
        self[key] = ret
        return ret

class relative_time:

    @staticmethod
    def __add__(other):
        if other is absolute_time:
            return absolute_time
        return relative_time

    @staticmethod
    def __sub__(other):
        if other is absolute_time:
            raise TypeError("Can't sub absolute time from relative")
        return relative_time

    @staticmethod
    def __str__():
        return "relative"

    @staticmethod
    def tostring(ts, unit=timedelta(minutes=1)):
        return "%d" % (ts / unit)

relative_time = relative_time()

class absolute_time:

    @staticmethod
    def __add__(other):
        if other is absolute_time:
            raise TypeError("Can't add absolute times")
        return absolute_time

    @staticmethod
    def __sub__(other):
        if other is absolute_time:
            return relative_time
        return absolute_time

    @staticmethod
    def __str__():
        return "absolute"

    @staticmethod
    def tostring(ts, dateformat="%d.%m.%Y %H:%M"):
        return ts.strftime(dateformat)

absolute_time = absolute_time()

_time_fmts = (relative_time, absolute_time)

def gettimefmt(fmt):
    if isinstance(fmt, str):
        if fmt == "relative":
            return relative_time
        if fmt == "absolute":
            return absolute_time

    if isinstance(fmt, timedelta):
        return relative_time

    if isinstance(fmt, datetime):
        return absolute_time

    if fmt in _time_fmts:
        return fmt

    raise TimetableError("No such format '%s'" % fmt)

class Event:

    def __init__(self, time, data):
        self.time = time
        self.data = data

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Event(self.time, self.data[key])
        return self.data[key]

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return "%s %s" % (str(self.time), str(self.data))

class Timetable:

    def __init__(self, time_fmt=None, events=None, labels=None, sorted=False):
        if time_fmt is None:
            if not events:
                raise ValueError("No time_fmt and no events, can't infer format")
            time_fmt = events[0].time

        self._time_fmt = gettimefmt(time_fmt)
        self._events = events if events is not None else []
        self._labels = labels
        self._sorted = sorted

    def __getitem__(self, key):
        if isinstance(key, tuple):
            rows, cols = key
            return Timetable(
                    time_fmt=self._time_fmt,
                    events=[e[cols] for e in self._events[rows]],
                    sorted=self._sorted
            )

        if isinstance(key, slice):
            return Timetable(
                    time_fmt=self._time_fmt,
                    events=self._events[key],
                    sorted=self._sorted
            )

        return self._events[key]

    def __add__(self, other):
        if type(other) in (timedelta, datetime):
            return Timetable(
                    time_fmt=self._time_fmt + gettimefmt(other),
                    events=[Event(e.time + other, e.data) for e in self._events],
                    labels=self._labels,
                    sorted=self._sorted
            )

        if isinstance(other, Timetable):
            if self._time_fmt is not other._time_fmt:
                raise TypeError("Can't add differing time formats")
            return Timetable(
                    time_fmt=self._time_fmt,
                    events=self._events + other.events,
                    sorted=False
            )

        raise TypeError(other)

    def __sub__(self, other):
        if type(other) in (timedelta, datetime):
            return Timetable(
                    time_fmt=self._time_fmt - gettimefmt(other),
                    events=[Event(e.time - other, e.data) for e in self._events],
                    labels=self._labels,
                    sorted=self._sorted
            )

        raise TypeError(other)

    def __str__(self):
        return self.tostring()

    def __iter__(self):
        yield from self._events

    def __len__(self):
        return len(self._events)

    def __bool__(self):
        return bool(self._events)

    @property
    def labels(self):
        if self._labels is None:
            self._labels = self._get_label_set()

        return self._labels

    @property
    def time_format(self):
        return str(self._time_fmt)

    def sort(self):
        if not self._sorted:
            self._events.sort(key=operator.attrgetter("time"))
            self._sorted = True

    def tostring(self, **kwargs):
        ret = []

        for e in self:
            ret.append("\t".join((
                self._time_fmt.tostring(e.time, **kwargs),
                *map(operator.attrgetter("name"), e.data))
            ))

        return "\n".join(ret)

    def _get_label_set(self):
        ret = LabelSet()

        for e in self:
            for x in e.data:
                if x.key not in ret:
                    ret[x.key] = x

        return ret

def parse_time(src, datefmt):
    if datefmt == "+M":
        return OffsetTime(timedelta(minutes=int(src)))
    
    return AbsoluteTime(datetime.strptime(src, datefmt))

def infer_timefmt(time, relative_fmt="+M", absolute_fmt="%d.%m.%Y %H:%M"):
    try:
        int(time)
    except ValueError:
        pass
    else:
        return relative_fmt

    try:
        datetime.strptime(time, absolute_fmt)
    except ValueError:
        pass
    else:
        return absolute_fmt

    raise ValueError("%s is not of either format (%s, %s)" % (time, relative_fmt, absolute_fmt))

_timedelta_keywords = {
        "S": "seconds",
        "M": "minutes",
        "H": "hours"
}

def get_time_parser(time_fmt):
    if time_fmt[0] == "+":
        kw = _timedelta_keywords[time_fmt[1]]
        return lambda s: timedelta(**{kw: int(s)})

    return lambda s: datetime.strptime(s, time_fmt)

def parse_timetable(src, time_fmt=None):
    lines = (l.split("\t") for l in src.splitlines())
    td = ((l[0], l[1:]) for l in lines)

    events = []

    if time_fmt is None:
        try:
            time, data = next(td)
        except StopIteration:
            # Tyhjä data ja ei aikatauluformaattia annettu joten ei väliä mitä laitetaan
            return Timetable(relative_time)

        parser = get_time_parser(infer_timefmt(time))
        events.append((parser(time), data))
    else:
        parser = get_time_parser(time_fmt)

    for time, data in td:
        events.append((parser(time), data))

    return create_timetable(
            events,
            time_fmt="relative" if time_fmt[0] == "+" else "absolute",
            sorted=False
    )

def create_timetable(events, **kwargs):
    labels = LabelSet()
    return Timetable(
        events=[Event(time, [labels[d] for d in data]) for time,data in events],
        labels=labels,
        **kwargs
    )

def fit_slots(timetable, slots):
    slots = sorted(slots, key=operator.itemgetter(0))
    timetable.sort()

    evs = iter(itertools.groupby(timetable, key=operator.attrgetter("time")))

    for start, end, td in slots:
        time = start

        while time < end:
            try:
                _, es = next(evs)
            except StopIteration:
                return

            for e in es:
                e.time = time

            time += td

    raise TimetableError("All data not fitted (at %s)" % str(e))
