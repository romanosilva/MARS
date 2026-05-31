"""Lightweight keyword/topic extraction (no external NLP dependency)."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

_STOPWORDS = set("""
a an and the of to in on at for is are was were be been being it its this that
these those i you he she we they me my your his her our their them us am do does
did have has had will would can could should may might must shall not no yes ok
okay so if then than too very just but or as up out about with from by we'll i'll
you'll get got go going gone here there what when where who why how which whom
hi hello hey thanks thank please sure yeah yep nope lol ok. https http www com
""".split())

_WORD = re.compile(r"[A-Za-z][A-Za-z'+-]{2,}")


def tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def keywords(texts: Iterable[str], top: int = 12) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for t in texts:
        for w in tokens(t):
            if w in _STOPWORDS or w.isdigit():
                continue
            counter[w] += 1
    return counter.most_common(top)
