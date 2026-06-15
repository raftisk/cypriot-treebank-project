import conllu
import argparse


def swap_columns_and_update_text(input_file_path, output_file_path):
    with open(input_file_path, "r", encoding="utf-8") as f:
        data = f.read()

    sentences = conllu.parse(data)

    for sentence in sentences:
        new_words = []

        # Track which IDs are part of an MWT split so we can skip them
        ids_to_skip = set()
        for token in sentence:
            if isinstance(token["id"], tuple):
                start_id = int(token["id"][0])
                end_id = int(token["id"][2])
                ids_to_skip.update(range(start_id, end_id + 1))

            # CoNLL-U columns are 0-indexed in python-conllu:
            # Column 2 (FORM) is token['form']
            # Column 10 (MISC) is token['misc']

            old_form = token["form"]
            old_misc = token["misc"]

            # 1. Extract the text after "CypriotGreek="
            # Check if old_misc is a dictionary and contains our target key
            if isinstance(old_misc, dict) and "CypriotGreek" in old_misc:
                extracted_word = old_misc["CypriotGreek"]
            elif isinstance(old_misc, str) and "CypriotGreek=" in old_misc:
                # Fallback string split just in case it didn't parse as a dict
                extracted_word = old_misc.split("CypriotGreek=")[1].split("|")[0]
            else:
                # Fallback if the key isn't found
                extracted_word = str(old_misc) if old_misc not in (None, "_") else ""

            token["form"] = extracted_word if extracted_word else "_"
            token["misc"] = {"SMGTranslit": old_form}

            try:
                current_id = int(token["id"])
            except TypeError, ValueError:
                current_id = token["id"]

            if current_id in ids_to_skip:
                continue
            else:
                new_words.append(extracted_word)

        sentence.metadata["text"] = " ".join(new_words).strip()

    with open(output_file_path, "w", encoding="utf-8") as f:
        f.writelines([sentence.serialize() for sentence in sentences])


def main():
    parser = argparse.ArgumentParser(
        description="Swap the 2nd (FORM) and 10th (MISC) columns in a CoNLL-U file and update text metadata."
    )

    parser.add_argument(
        "--input_file", required=True, help="Path to the input CoNLL-U file"
    )
    parser.add_argument(
        "--output_file",
        required=True,
        help="Path where the modified CoNLL-U file will be saved",
    )

    args = parser.parse_args()
    swap_columns_and_update_text(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
