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

@functools.total_ordering
class OffsetTime:

    def __init__(self, td):
        self.td = td

    def __str__(self):
        return self.stringify()

    def __eq__(self, other):
        return self.td == other.td

    def __lt__(self, other):
        return self.td < other.td

    def add_delta(self, delta):
        return OffsetTime(self.td + delta)

    def set_base(self, dt):
        return AbsoluteTime(dt + self.td)

    def stringify(self, **kwargs):
        return "%d" % (self.td / timedelta(minutes=1))

@functools.total_ordering
class AbsoluteTime:

    def __init__(self, dt):
        self.dt = dt

    def __str__(self):
        return self.stringify()

    def __int__(self):
        return int(self.dt.timestamp())

    def __eq__(self, other):
        return self.dt == other.dt

    def __lt__(self, other):
        return self.dt < other.dt

    def add_delta(self, delta):
        return AbsoluteTime(self.dt + delta)

    def set_base(self, dt):
        raise TimetableError("Can't set base of absolute time")

    def stringify(self, datefmt="%d.%m.%Y %H:%M", **kwargs):
        return self.dt.strftime(datefmt)

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

    def __init__(self, events=None, labels=None, sorted=True):
        self._events = events if events is not None else []
        self._labels = labels
        self._sorted = sorted

    def __str__(self):
        return stringify_timetable(self)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            rows, cols = key
            return Timetable(events=[e[cols] for e in self._events[rows]])

        if isinstance(key, slice):
            return Timetable(events=self._events[key])

        return self._events[key]

    def __add__(self, other):
        if isinstance(other, datetime):
            return Timetable(
                    events=[Event(e.time.set_base(other), e.data) for e in self._events],
                    labels=self._labels
            )

        if isinstance(other, timedelta):
            return Timetable(
                    events=[Event(e.time.add_delta(other), e.data) for e in self._events],
                    labels=self._labels
            )

        if isinstance(other, Timetable):
            return Timetable(self._events + other.events, sorted=False)

        return Timetable(self._events + other, sorted=False)

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

    def _get_label_set(self):
        ret = LabelSet()

        for e in self:
            for x in e.data:
                if x.key not in ret:
                    ret[x.key] = x

        return ret

    def sort(self):
        if not self._sorted:
            self._events.sort(key=operator.attrgetter("time"))
            self._sorted = True

def parse_time(src, datefmt):
    #if datefmt == "+L":
    #    return LabelTime(src)

    if datefmt == "+M":
        return OffsetTime(timedelta(minutes=int(src)))
    
    return AbsoluteTime(datetime.strptime(src, datefmt))

def parse_timetable(src, datefmt="+L"):
    events = []

    for line in src.splitlines():
        cols = line.split("\t")
        time, data = cols[0], cols[1:]

        try:
            time = parse_time(time, datefmt)
        except ValueError as e:
            raise TimetableError(e) from e

        events.append((time, data))

    return create_timetable(events, sorted=False)

def stringify_timetable(timetable, datefmt="%d.%m.%Y %H:%M"):
    ret = []

    for e in timetable:
        ret.append("\t".join((
            e.time.stringify(datefmt=datefmt),
            *map(operator.attrgetter("name"), e.data))
        ))

    return "\n".join(ret)

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

            time = time.add_delta(td)

    raise TimetableError("All data not fitted (at %s)" % str(e))
