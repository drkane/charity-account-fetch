import re

class HighlightNumbers(object):
    def __init__(self, start=1):
        self.count = start - 1

    def __call__(self, match):
        self.count += 1
        return '<span class="bg-yellow" id="match-{}">{}</span>'.format(
            self.count,
            match.group(1)
        )

def add_highlights(s, q):
    if not q:
        return (s, 0)
    qs = q.split()
    h = HighlightNumbers()
    s = re.sub(
        r'({})'.format("|".join(qs)),
        h,
        s,
        flags=re.IGNORECASE
    )
    return (s, h.count)
