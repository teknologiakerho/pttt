import operator
import functools
import itertools
from datetime import datetime, timedelta

class TimetableError(Exception):
    pass

@functools.total_ordering
class Label:
    
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "<%s>" % self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

class LabeledTime(Label):

    def add_delta(self, delta):
        raise TimetableError("Can't add delta to label")

    def set_base(self, dt):
        raise TimetableError("Can't set base of label")

    def stringify(self, **kwargs):
        return self.name

@functools.total_ordering
class OffsetTime:

    def __init__(self, td):
        self.td = td

    def __repr__(self):
        return repr(self.td)

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

    def __repr__(self):
        return repr(self.dt)

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

class Timetable:

    def __init__(self):
        self.labels = {}
        self.events = []
        self._sorted = True

    def __str__(self):
        return stringify_timetable(self)

    def label(self, name):
        ret = self.labels.get(name)

        if ret is None:
            ret = Label(name)
            self.labels[name] = ret

        return ret

    def rename(self, oldlabel, newlabel):
        if newlabel in self.labels:
            raise KeyError(newlabel)

        label = self.labels.pop(oldlabel, None)

        if label is None:
            return

        label.name = newlabel
        self.labels[newlabel] = label
        self._sorted = False

    def add(self, time, rest):
        self.events.append([time, *map(self.label, rest)])
        self._sorted = False

    def add_delta(self, td):
        for e in self.events:
            e[0] = e[0].add_delta(td)

    def set_base(self, dt):
        for e in self.events:
            e[0] = e[0].set_base(dt)

    def sort(self):
        if not self._sorted:
            self.events.sort(key=operator.itemgetter(0))
            self._sorted = True

def parse_time(src, datefmt):
    #if datefmt == "+L":
    #    return LabelTime(src)

    if datefmt == "+M":
        return OffsetTime(timedelta(minutes=int(src)))
    
    return AbsoluteTime(datetime.strptime(src, datefmt))

def parse_timetable(src, datefmt="+L"):
    ret = Timetable()

    for line in src.splitlines():
        cols = line.split("\t")
        time, rest = cols[0], cols[1:]

        try:
            time = parse_time(time, datefmt)
        except ValueError as e:
            raise TimetableError(e) from e

        ret.add(time, rest)

    return ret

def stringify_timetable(timetable, datefmt="%d.%m.%Y %H:%M"):
    ret = []

    for e in timetable.events:
        ret.append("\t".join((
            e[0].stringify(datefmt=datefmt),
            *map(operator.attrgetter("name"), e[1:]))
        ))

    return "\n".join(ret)

def fit_slots(timetable, slots):
    slots = sorted(slots, key=operator.itemgetter(0))
    timetable.sort()

    evs = iter(itertools.groupby(timetable.events, key=operator.itemgetter(0)))

    for start, end, td in slots:
        time = start

        while time < end:
            try:
                _, es = next(evs)
            except StopIteration:
                return

            for e in es:
                e[0] = time

            time = time.add_delta(td)

    raise TimetableError("All data not fitted (at %s)" % str(e))

def combine_timetables(timetable1, timetable2):
    timetable1.labels.update(timetable2.labels)
    timetable1.events.extend(timetable2.events)
    timetable1._sorted = False
    return timetable1
