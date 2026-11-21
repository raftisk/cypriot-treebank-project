#!/usr/bin/env python3
"""Rule-based conversion of Standard Greek CoNLL-U towards Cypriot Greek.

Usage:  python cypriotize.py in.conllu -o out.conllu [--diff [conllu]] [--only kai,den]
Add rules at the bottom (RULES SECTION): a rule is a function of one Sentence, decorated with @rule.
"""
import argparse, difflib, re, sys
from collections import Counter
from datetime import datetime

R = re.compile  # shorthand for regex filters:  form=R(r'^κ')
UPOS = set('ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X'.split())


# ───────────────────────────── data model ─────────────────────────────
def parse_kv(s):  # 'A=b|C=d' -> {'A': 'b', 'C': 'd'}
    return {} if s == '_' else {k: (v if sep else None) for k, sep, v in (p.partition('=') for p in s.split('|'))}

def fmt_kv(d, sort=False):
    items = sorted(d.items(), key=lambda kv: kv[0].lower()) if sort else d.items()
    return '|'.join(k if v is None else f'{k}={v}' for k, v in items) or '_'

def test(val, m):
    """Does one value satisfy one filter?  m can be: callable | compiled regex | set/list/tuple | plain value."""
    if callable(m): return bool(m(val))
    if isinstance(m, re.Pattern): return val is not None and bool(m.search(val))
    if isinstance(m, (set, frozenset, list, tuple)): return val in m
    return val == m


class Tok:
    """A word. Fields: form lemma upos xpos feats(dict) deprel deps misc(dict) head(Tok or None for root).
    Derived (read-only): id prev next children depth mwt."""
    def __init__(self, sent, row):
        self.sent = sent
        _, self.form, self.lemma, self.upos, self.xpos, feats, self.head, self.deprel, self.deps, misc = row
        self.feats, self.misc = parse_kv(feats), parse_kv(misc)   # self.head is still a string id; Sentence resolves it

    id = property(lambda s: s.sent.toks.index(s) + 1)
    prev = property(lambda s: s.sent.toks[s.id - 2] if s.id > 1 else None)
    next = property(lambda s: s.sent.toks[s.id] if s.id < len(s.sent.toks) else None)
    children = property(lambda s: [t for t in s.sent.toks if t.head is s])
    mwt = property(lambda s: next((m for m in s.sent.mwts if s in m.toks), None))

    @property
    def depth(self):  # root = 0
        d, t = 0, self
        while t.head is not None and d < 1000: t, d = t.head, d + 1
        return d

    def matches(self, not_=None, where=None, **crit):
        """Filter. Keys: any attribute (form, lemma, upos, xpos, deprel, deps, id, depth, mwt) or
        feats={..}/misc={..} (value None = key absent), head/prev/next={nested filter} (None = no such token),
        children={nested filter} (any child), not_={filter to exclude}, where=lambda tok: bool."""
        for key, m in crit.items():
            if key in ('head', 'prev', 'next'):
                t = getattr(self, key)
                ok = (t is None) if m is None else (t is not None and t.matches(**m))
            elif key == 'children': ok = any(c.matches(**m) for c in self.children)
            elif key in ('feats', 'misc'): ok = all(test(getattr(self, key).get(k), v) for k, v in m.items())
            elif key == 'mwt': ok = (self.mwt is not None) == m
            else: ok = test(getattr(self, key), m)
            if not ok: return False
        if not_ is not None and self.matches(**not_): return False
        return where(self) if where else True

    def __repr__(self): return f'{self.id}:{self.form}'


class Mwt:
    """Multiword token line (e.g. 10-11 στην). Holds references to its word Toks, so it survives reordering."""
    def __init__(self, toks, form, misc=None): self.toks, self.form, self.misc = toks, form, misc or {}


class Sentence:
    def __init__(self, meta_lines, rows):
        self.meta = {}
        for l in meta_lines:
            k, sep, v = l[1:].strip().partition(' = ')
            self.meta[k] = v if sep else None
        self.toks, self.mwts, byid = [], [], {}
        for r in rows:
            if '.' in r[0]: raise ValueError('empty nodes (e.g. 5.1) are not supported')
            if '-' not in r[0]: byid[r[0]] = Tok(self, r); self.toks.append(byid[r[0]])
        for t in self.toks: t.head = byid.get(t.head)             # '0' -> None (root)
        for r in rows:
            if '-' in r[0]:
                a, b = map(int, r[0].split('-'))
                self.mwts.append(Mwt([byid[str(i)] for i in range(a, b + 1)], r[1], parse_kv(r[9])))
        self.before = str(self)

    def find(self, **crit): return [t for t in self.toks if t.matches(**crit)]

    def move(self, tok, after=None, before=None):
        """Move tok right after / before another token. Heads are object references, so ids fix themselves."""
        self.toks.remove(tok)
        self.toks.insert(self.toks.index(after) + 1 if after else self.toks.index(before), tok)

    def make_mwt(self, toks, form, **misc):
        """Glue adjacent words into one multiword token with surface form `form`."""
        self.mwts.append(Mwt(list(toks), form, misc))

    def text(self):
        """Rebuild '# text' from the tokens (MWT surface forms replace their parts; honours SpaceAfter=No)."""
        starts, inside = {m.toks[0]: m for m in self.mwts}, {t for m in self.mwts for t in m.toks}
        out = ''
        for t in self.toks:
            if t in inside and t not in starts: continue
            u = starts.get(t, t)
            out += u.form + ('' if u.misc.get('SpaceAfter') == 'No' else ' ')
        return out.strip()

    def __str__(self):
        starts = {m.toks[0]: m for m in self.mwts}
        lines = ['# ' + k + ('' if v is None else f' = {v}') for k, v in self.meta.items()]
        for t in self.toks:
            if t in starts:
                m = starts[t]
                lines.append('\t'.join([f'{m.toks[0].id}-{m.toks[-1].id}', m.form, *['_'] * 7, fmt_kv(m.misc)]))
            lines.append('\t'.join([str(t.id), t.form, t.lemma, t.upos, t.xpos, fmt_kv(t.feats, True),
                                    str(t.head.id if t.head else 0), t.deprel, t.deps, fmt_kv(t.misc)]))
        return '\n'.join(lines) + '\n'


def read(path):
    sents, meta, rows = [], [], []
    for line in open(path, encoding='utf8').read().split('\n') + ['']:
        if line.startswith('#'): meta.append(line)
        elif line.strip(): rows.append(line.split('\t'))
        elif meta or rows: sents.append(Sentence(meta, rows)); meta, rows = [], []
    return sents

def write(sents, path):
    with open(path, 'w', encoding='utf8') as f: f.write('\n'.join(str(s) for s in sents) + '\n')


# ───────────────────────────── validation ─────────────────────────────
def validate(s):
    """Returns a list of problems (strings starting with 'WARN' are soft: e.g. non-projectivity)."""
    errs = []
    if len([t for t in s.toks if t.head is None]) != 1: errs.append('sentence must have exactly one root')
    for t in s.toks:
        if t.head is not None and t.head not in s.toks: return errs + [f'{t}: head is not in the sentence']
        if (t.head is None) != (t.deprel == 'root'): errs.append(f'{t}: head 0 and deprel root must go together')
        if t.upos not in UPOS: errs.append(f'{t}: unknown UPOS {t.upos}')
        x, seen = t, set()                                       # walk up; ending on a revisited token = cycle
        while x and x not in seen: seen.add(x); x = x.head
        if x: errs.append(f'{t}: dependency cycle')
    for m in s.mwts:
        ids = [t.id for t in m.toks]
        if ids != list(range(ids[0], ids[0] + len(ids))): errs.append(f'MWT {m.form}: words are not contiguous')
    if any(n > 1 for n in Counter(t for m in s.mwts for t in m.toks).values()): errs.append('overlapping MWTs')
    arcs = [(min(t.id, t.head.id), max(t.id, t.head.id), t) for t in s.toks if t.head]
    errs += [f'WARN non-projective: {t} x {u}' for a, b, t in arcs for c, d, u in arcs if a < c < b < d]
    return errs


# ───────────────────────────── helpers for rules ─────────────────────────────
RULES = []
def rule(f): RULES.append(f); return f          # rules run in the order they are defined, on every sentence

def keep_case(old, new): return new[0].upper() + new[1:] if old[:1].isupper() else new

def lex(s, old_lemma, new, **crit):
    """Replace every token whose lemma is `old_lemma` by `new` (sets form AND lemma, keeps capitalisation)."""
    for t in s.find(lemma=old_lemma, **crit): t.form, t.lemma = keep_case(t.form, new), new


# ───────────────────────────── RULES SECTION ─────────────────────────────
@rule
def kai(s): lex(s, 'και', 'τζ̆αι')                     # note: τζ̆ = τζ + U+0306 (as in the treebank)

@rule
def den(s): lex(s, 'δεν', 'εν', upos='PART')

@rule
def tha(s): lex(s, 'θα', 'εννά')

FRONT = r'(?:[εέιίηήυύ]|[αεου][ιί])'                   # front vowels: ε ι η υ αι ει οι υι (accented or not)
KAPPA = R(rf'(?<![γκσΓΚΣ])[κΚ](?={FRONT})')            # κ before a front vowel; not in γκ, κκ, σκ  (ASSUMPTION: edit me)

@rule
def palatal_k(s):
    for t in s.find(not_=dict(upos='PROPN'), mwt=False):   # names untouched; words inside MWTs untouched (exceptions live here)
        sub = lambda x: KAPPA.sub(lambda m: keep_case(m.group(), 'τζ̆'), x)
        t.form, t.lemma = sub(t.form), sub(t.lemma)


# ── clitics go after the verb:  μου το είπε → είπε το μου ──────────────────
CLITIC = dict(upos='PRON', feats={'PronType': 'Prs', 'Poss': None},           # personal, not possessive
              form=R(r'(?i)^(μου|σου|του|της|μας|σας|τους|με|σε|τον|την|τη|το|τα|τις|τες)$'),
              deprel={'obj', 'iobj', 'obl'}, mwt=False)
REVERSE_CLUSTER = True            # μου το είπε → είπε το μου (True) or είπε μου το (False)
KEEP_BEFORE_IF_VERB_HAS_CHILD = [                      # EDIT ME: contexts where the clitic stays before the verb
    dict(upos='SCONJ', lemma='να'),                    #   να μου πεις
    dict(lemma={'θα', 'εννά'}),                        #   εννά μου πει
    # dict(feats={'Polarity': 'Neg'}),                 #   negation: uncomment to keep  εν μου το είπε
]

@rule
def clitics_after_verb(s):
    for verb in s.find(upos={'VERB', 'AUX'}):
        if any(verb.matches(children=c) for c in KEEP_BEFORE_IF_VERB_HAS_CHILD): continue
        cluster, t = [], verb.prev                    # the clitics sitting directly before their verb
        while t and t.head is verb and t.matches(**CLITIC): cluster.insert(0, t); t = t.prev
        if not cluster: continue
        sentence_initial = cluster[0].prev is None
        anchor = verb
        for c in (reversed(cluster) if REVERSE_CLUSTER else cluster):
            s.move(c, after=anchor); anchor = c
        if sentence_initial:                          # Μου το είπε → Είπε το μου
            for c in cluster: c.form = c.form.lower()
            verb.form = verb.form[:1].upper() + verb.form[1:]


# ── template: glue words into an MWT (disabled).  εν + εν’ → έννεν’ as in the treebank ──
# @rule
# def neg_copula_mwt(s):
#     for a in s.find(feats={'Polarity': 'Neg'}, mwt=False, next=dict(upos='AUX', mwt=False)):
#         s.make_mwt([a, a.next], 'έννεν’')


# ───────────────────────────── command line ─────────────────────────────
def convert(s, rules):
    """Apply rules in order; returns the names of the rules that changed the sentence."""
    fired = []
    for r in rules:
        snapshot = str(s)
        r(s)
        if str(s) != snapshot: fired.append(r.__name__)
    if fired:
        new = s.text()
        if new != s.meta.get('text'): s.meta['text_orig'], s.meta['text'] = s.meta.get('text'), new
        s.meta['rules'] = ', '.join(fired)
    return fired

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input')
    ap.add_argument('-o', '--output', help='write the converted CoNLL-U here')
    ap.add_argument('--diff', nargs='?', const='text', choices=['text', 'conllu'],
                    help='print before/after of every changed sentence (text, or full conllu diff)')
    ap.add_argument('--only', help='comma-separated rule names to run (default: all)')
    args = ap.parse_args()

    rules = [r for r in RULES if not args.only or r.__name__ in args.only.split(',')]
    sents, changed, bad = read(args.input), 0, 0
    for s in sents:
        fired = convert(s, rules)
        changed += bool(fired)
        if fired and args.diff:
            print(f"[{s.meta.get('sent_id')}] {s.meta['rules']}")
            print(f"- {s.meta.get('text_orig', s.meta.get('text'))}\n+ {s.meta.get('text')}")
            if args.diff == 'conllu':
                diffs = '\n'.join(difflib.unified_diff(s.before.splitlines(), str(s).splitlines(), lineterm='', n=0))
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"[{timestamp}]\n{diffs}\n"
                with open('differences.txt', 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            print()
        problems = validate(s)
        bad += bool(problems)
        for p in problems: print(f"[{s.meta.get('sent_id')}] {p}", file=sys.stderr)
    if args.output: write(sents, args.output)
    print(f'{len(sents)} sentences, {changed} changed, {bad} with validation problems', file=sys.stderr)

if __name__ == '__main__':
    main()
