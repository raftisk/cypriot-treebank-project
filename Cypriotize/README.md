# cypriotize.py: rule-based Standard Greek → Cypriot Greek on CoNLL-U

A single-file script (standard library only, Python ≥ 3.8). It reads a CoNLL-U file, applies your rules to
every sentence, rebuilds `# text`, validates the trees and writes a new CoNLL-U file. It does **not**
parse; feed it output from a UD parser (Stanza, UDPipe, …).

## Quick start

```bash
python cypriotize.py standard.conllu -o cypriot.conllu            # convert
python cypriotize.py el_gud-ud-test.conllu --diff                       # before/after text of changed sentences
python cypriotize.py standard.conllu --diff conllu                # ...plus a CoNLL-U diff
python cypriotize.py standard.conllu --only kai,clitics_after_verb -o out.conllu   # run chosen rules only
```

Example output of `--diff`:

```
[t2] den, clitics_after_verb
- Δεν μου αρέσει το κρασί .
+ Εν αρέσει μου το κρασί .
```

Changed sentences get two extra comments: `# text_orig` (the original text) and `# rules`
(which rules changed that sentence). Unchanged sentences are written exactly as read
(on your treebank, read → write with no rules is byte-identical). `sent_id` is never changed.

## How it works

Rules run **in the order they are defined**, each on every sentence, 100 % of the time. A rule is a
function of one `Sentence`, registered with `@rule`:

```python
@rule
def kai(s):
    for t in s.find(lemma='και'):          # 1. select tokens with a filter
        t.form, t.lemma = 'τζ̆αι', 'τζ̆αι'   # 2. edit them
```

Tokens (`Tok`) have editable fields `form lemma upos xpos feats deprel deps misc head`.
`feats` and `misc` are dicts; `head` is the head *token* (`None` = root). Because heads are object
references, **ids are never edited by hand**: they are recomputed on output. Reordering is just
`s.move(...)`, or any list operation on `s.toks`.

## Filters: `s.find(...)` and `tok.matches(...)`

Every keyword is an AND condition. A value can be:

| value | meaning | example |
|---|---|---|
| plain value | equals | `upos='PRON'` |
| `set` / `list` / `tuple` | is one of | `deprel={'obj', 'iobj'}` |
| `R(r'...')` (compiled regex) | `re.search` matches | `form=R(r'^κ')`, `form=R(r'(?i)^μου$')` |
| function | returns True | `depth=lambda d: d >= 3` |

| key | filters on |
|---|---|
| `form lemma upos xpos deprel deps` | the column of that name |
| `feats={'Case': 'Gen', 'Poss': None}` | features (same value types; `None` = feature absent) |
| `misc={...}` | same, for MISC |
| `id`, `depth` | position in sentence, depth in the tree (root = 0) |
| `mwt=True/False` | is the word part of a multiword token? |
| `head={...}` | nested filter on the parent. Nest for grandparents: `head=dict(head=dict(deprel='root'))`. `head=None` = is root |
| `prev={...}` / `next={...}` | nested filter on the neighbouring word (`None` = no neighbour) |
| `children={...}` | at least one child matches the nested filter |
| `not_={...}` | exclude tokens matching this filter |
| `where=lambda t: ...` | anything else (arbitrary Python test) |

```python
s.find(upos='PRON', feats={'Case': 'Gen', 'Poss': None}, head=dict(upos='VERB'), prev=dict(upos='AUX'))
s.find(deprel='obl', depth=lambda d: d >= 2, not_=dict(upos='PROPN'), mwt=False)
```

## Operations

| call | effect |
|---|---|
| `t.form = ...`, `t.feats['Case'] = ...`, `del t.feats['Poss']` | edit a token |
| `s.move(tok, after=other)` / `s.move(tok, before=other)` | reorder (heads and ids fix themselves) |
| `s.make_mwt([tok_a, tok_b], 'surface')` | create a multiword token line from adjacent words |
| `s.toks`, `s.mwts` | plain lists, so you can also insert/remove tokens or MWTs yourself |
| `lex(s, 'old_lemma', 'new', **filter)` | helper: set form+lemma of every token with that lemma, keeping capitalisation |
| `keep_case(old, new)` | helper: capitalise `new` if `old` starts with a capital |

Adding a rule = adding a function below the existing ones. Illustration of the syntax (not a vetted rule):

```python
@rule
def final_nu(s):
    for t in s.find(upos='NOUN', feats={'Case': 'Acc', 'Gender': 'Neut'}, form=R(r'[ιο]$'), mwt=False):
        t.form += 'ν'
```

## Rules included

| rule | what it does |
|---|---|
| `kai` | lemma `και` → `τζ̆αι` (form and lemma) |
| `den` | lemma `δεν` (PART) → `εν` |
| `tha` | lemma `θα` → `εννά` |
| `palatal_k` | `κ` before a front vowel (ε ι η υ αι ει οι υι) → `τζ̆`. Skips PROPN and words inside MWTs |
| `clitics_after_verb` | personal clitics before their verb move after it: `μου το είπε` → `είπε το μου` |

`τζ̆` is τζ + U+0306 (combining breve), the same characters as in your treebank.

### Editing the clitic rule

The settings sit just above the rule in the script:

* `CLITIC`: what counts as a clitic (a filter dict: PRON, personal, not possessive, listed weak forms, deprel obj/iobj/obl).
* `REVERSE_CLUSTER`: `True` gives `είπε το μου`, `False` gives `είπε μου το`.
* `KEEP_BEFORE_IF_VERB_HAS_CHILD`: contexts in which the clitic stays before the verb, written as
  child filters. Currently `να` and `θα`/`εννά`. **Negation is the commented-out line**: uncomment it to keep
  `εν μου το είπε`. Add any other context the same way.
* A sentence-initial cluster is handled (`Μου το είπε` → `Είπε το μου`).

### Multiword tokens

All existing MWT lines are kept and survive reordering. To exempt MWT words from a rule use `mwt=False`
in its filter (as `palatal_k` and the clitic rule do). To create MWTs, use `s.make_mwt`; a commented
template (`εν` + `εν’` → `έννεν’`) is in the script, just above the command-line section.

## Validation

Every output sentence is checked and problems are printed to stderr as `[sent_id] message`:
exactly one root, root ⇔ `deprel=root`, no cycles, known UPOS, MWT words contiguous and non-overlapping, plus
`WARN non-projective` for crossing arcs (a warning only; the parser's own output may contain some).
The last line is a summary: `N sentences, M changed, K with validation problems`.

## Limitations to know about

* Enhanced dependencies (column 9) are copied unchanged and their ids are **not** updated.
* The clitic rule only finds clitics directly before their own head verb. In `θα μου το έχει πει`
  the clitics belong to `πει` but sit before `έχει`, so they are left alone.
* If a rule changes a word *inside* an MWT, the MWT surface form is not updated (use `mwt=False` or update it yourself).
* The `palatal_k` exclusions (γκ, κκ, σκ, proper nouns) are my conservative assumptions, so please check them. It also
  covers `και`, so `kai` is technically redundant, but it is kept explicit and runs first.
* Empty nodes (`5.1`) are not supported and raise an error.
