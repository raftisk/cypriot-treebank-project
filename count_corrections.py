"""Count the corrections annotators made to a model-parsed CoNLL-U file.

Both files hold the same sentences, matched on sent_id, and tokens are matched
on their position in the sentence. Every annotation cell that differs between
the two files counts as one correction, except FEATS, where every feature that
was added, removed or given a new value counts as one. Sentences whose token
count changed (re-tokenized by the annotator) are skipped and listed at the end.
"""

import argparse
from collections import Counter
from pathlib import Path

import conllu

COLUMNS = ["form", "lemma", "upos", "xpos", "feats", "head", "deprel", "deps", "misc"]


def read_sentences(path):
    """Return a dict mapping each sent_id to its word tokens.

    Multiword ranges ("17-18") and empty nodes ("8.1") are left out, because
    they carry no annotation of their own. conllu gives both a tuple id.
    """
    sentences = conllu.parse(Path(path).read_text(encoding="utf-8"))
    return {
        sentence.metadata["sent_id"]: [token for token in sentence if isinstance(token["id"], int)]
        for sentence in sentences
    }


def count_feature_changes(original_feats, validated_feats):
    """Return how many features were added, removed or given a new value."""
    feature_names = original_feats.keys() | validated_feats.keys()
    return sum(original_feats.get(name) != validated_feats.get(name) for name in feature_names)


def count_corrections(original_tokens, validated_tokens):
    """Return a Counter of corrections per column for one sentence."""
    counts = Counter()
    for original_token, validated_token in zip(original_tokens, validated_tokens):
        for column in COLUMNS:
            original_cell = original_token[column]
            validated_cell = validated_token[column]
            if column == "feats":
                # conllu gives None for an empty cell ("_").
                counts[column] += count_feature_changes(original_cell or {}, validated_cell or {})
            elif original_cell != validated_cell:
                counts[column] += 1
    return counts


def print_report(counts, sentence_count, token_count, skipped):
    print(f"Compared {sentence_count} sentences, {token_count} tokens.\n")
    print(f"{'COLUMN':<8} {'HITS':>6} {'PER 100 TOKENS':>16}")
    for column in [*COLUMNS, "total"]:
        hits = counts.total() if column == "total" else counts[column]
        print(f"{column.upper():<8} {hits:>6} {100 * hits / token_count:>16.1f}")

    if skipped:
        print(f"\nSkipped sentences ({len(skipped)}):")
        for reason in skipped:
            print(f"  {reason}")


def main():
    parser = argparse.ArgumentParser(
        description="Count corrections between a model-parsed and a validated CoNLL-U file."
    )
    parser.add_argument("--original", required=True, help="CoNLL-U file as parsed by the model")
    parser.add_argument("--validated", required=True, help="The same sentences after manual correction")
    args = parser.parse_args()

    original = read_sentences(args.original)
    validated = read_sentences(args.validated)

    counts = Counter()
    sentence_count = 0
    token_count = 0
    skipped = [f"{sent_id}: missing from original file" for sent_id in validated.keys() - original.keys()]
    for sent_id, original_tokens in original.items():
        validated_tokens = validated.get(sent_id)
        if validated_tokens is None:
            skipped.append(f"{sent_id}: missing from validated file")
            continue
        if len(original_tokens) != len(validated_tokens):
            skipped.append(f"{sent_id}: token count changed ({len(original_tokens)} -> {len(validated_tokens)})")
            continue
        counts += count_corrections(original_tokens, validated_tokens)
        sentence_count += 1
        token_count += len(original_tokens)

    if token_count == 0:
        raise SystemExit("No sentences could be compared. Check that both files share sent_ids.")
    print_report(counts, sentence_count, token_count, skipped)


if __name__ == "__main__":
    main()
