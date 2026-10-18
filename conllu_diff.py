import conllu
from collections import Counter


def count_conllu_corrections(predicted_file, corrected_file):
    with (
        open(predicted_file, "r", encoding="utf-8") as f_pred,
        open(corrected_file, "r", encoding="utf-8") as f_corr,
    ):
        pred_sentences = list(conllu.parse_incr(f_pred))
        corr_sentences = list(conllu.parse_incr(f_corr))

    changes = Counter()
    total_tokens = 0
    fields_to_check = [
        "form",
        "lemma",
        "upos",
        "xpos",
        "feats",
        "head",
        "deprel",
        "misc",
        "deps",
    ]

    for pred_sent, corr_sent in zip(pred_sentences, corr_sentences):
        for pred_token, corr_token in zip(pred_sent, corr_sent):
            if not isinstance(pred_token["id"], int):
                continue

            total_tokens += 1

            for field in fields_to_check:
                if pred_token[field] != corr_token[field]:
                    if field == "feats":
                        # conllu parses empty feats as None, so default to empty dictionaries
                        pred_feats = pred_token["feats"] or {}
                        corr_feats = corr_token["feats"] or {}

                        # Get a unique set of all feature keys present in either token
                        all_keys = set(pred_feats.keys()).union(set(corr_feats.keys()))

                        if all_keys:
                            # Count how many individual features have mismatched values
                            diff_count = sum(
                                1
                                for k in all_keys
                                if pred_feats.get(k) != corr_feats.get(k)
                            )
                            # Add the fractional change (e.g., 1 diff / 4 total keys = 0.25)
                            changes[field] += diff_count / len(all_keys)
                        else:
                            # Fallback if one was None and the other was an empty dictionary {}
                            changes[field] += 1
                    else:
                        changes[field] += 1

    total_edits = sum(changes.values())

    print(f"Total tokens compared: {total_tokens}")
    # Use :g to format floats cleanly (prints 103 instead of 103.0, but 103.25 instead of 103)
    print(f"Total overall edits:   {total_edits:g}")
    print("-" * 30)
    print("Corrections by field:")

    for field, count in changes.most_common():
        if count > 0:
            print(f"{field.upper().ljust(10)}: {count:g} corrections")

    return changes


def main():
    predicted_file = (
        "annotated-samples-4/stavros.bompolas/el_cypriot-ud-dev-4th-cycle.conllu"
    )
    corrected_file = "annotated-samples-4/validated/el_cypriot-ud-dev-4th-cycle.conllu"

    print(f"Comparing '{predicted_file}' against '{corrected_file}'...\n")

    count_conllu_corrections(predicted_file, corrected_file)


if __name__ == "__main__":
    main()
