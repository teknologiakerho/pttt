import collections

class VerifyError(Exception):
    pass

class MapEqError(VerifyError):

    def __init__(self, first, first_value, elem, elem_value):
        super().__init__("Non-matching properties %s (%s) and %s (%s)"\
                % tuple(map(str, (first, first_value, elem, elem_value))))
        self.first = first
        self.first_value = first_value
        self.elem = elem
        self.elem_value = elem_value

def map_eq(f, it):
    it = iter(it)

    try:
        first = next(it)
    except StopIteration:
        return

    fv = f(first)

    for i in it:
        iv = f(i)
        if iv != fv:
            raise MapEqError(first, fv, i, iv)

def verify_dimensions(timetable):
    try:
        map_eq(lambda r: len(r.data), timetable)
    except MapEqError as e:
        raise VerifyError("Unmatching dimensions: expected %d columns but got %d (row: %s)"\
                % (e.first_value, e.elem_value, str(e.elem)))

def verify_labels(timetable):
    for r in timetable:
        for l in r:
            if "\t" in l.name:
                raise VerifyError("Found tab character in label '%s' on row: %s" % (l.name, str(r)))

def verify_conflicts(timetable):
    simul = collections.defaultdict(set)

    for r in timetable:
        ts = str(r.time)
        s = simul[ts]
        for l in r:
            if l.key in s:
                raise VerifyError("Label %s conflict (row: %s)" % (repr(l), str(r)))
            s.add(l.key)

def verify_count(timetable, labels):
    counts = dict((l, 0) for l in labels)

    for r in timetable:
        for l in r:
            if l.key in counts:
                counts[l.key] += 1

    try:
        map_eq(lambda x: x[1], counts.items())
    except MapEqError as e:
        fl, fc = e.first
        el, ec = e.elem
        fl = timetable.labels[fl]
        el = timetable.labels[el]

        raise VerifyError("Label count mismatch: %s appears %d times and %s appears %d times"\
                % (repr(fl), fc, repr(el), ec))
