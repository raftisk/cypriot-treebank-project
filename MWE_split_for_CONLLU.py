import os

MWE_MAP = {
    "έννεν’": ["εν", "εν'"],
    "έννεν'": ["εν", "εν'"],
    "τούντην": ["τούτην", "την"],
    "τούντο": ["τούτον", "το"],
    "ποτούντα": ["που", "τούτα", "τα"],
    "εννάν’": ["εννά", "εν'"],
    "εννάν'": ["εννά", "εν'"],
    "σάννα": ["σαν", "να"],
    "πὀννά": ["που", "εννά"]}

def process_conllu(input_filepath, output_filepath):
    with open(input_filepath, 'r', encoding='utf-8') as f:
        blocks = f.read().strip().split('\n\n')
    out_blocks = []
    for block in blocks:
        lines = block.split('\n')
        meta_lines = [l for l in lines if l.startswith('#')]
        data_lines = [l for l in lines if not l.startswith('#') and l.strip()]
        offset = 0
        old_to_new_id = {"0": "0", "_": "_"}
        temp_data = []

        # First pass: Identify MWEs, inject splits, and calculate ID shifts
        for row in data_lines:
            cols = row.split('\t')
            if len(cols) < 10 or '-' in cols[0] or '.' in cols[0]:   # Skip lines that are already MWE ranges (e.g., "1-2") or empty nodes (e.g., "1.1")
                temp_data.append(row)
                continue
            old_id = cols[0]
            form = cols[1]
            lower_form = form.lower()
            if lower_form in MWE_MAP:
                splits = MWE_MAP[lower_form]
                split_count = len(splits)
                start_new_id = int(old_id) + offset
                end_new_id = start_new_id + split_count - 1

                # Create the MWE range line
                mwe_line = f"{start_new_id}-{end_new_id}\t{form}\t_\t_\t_\t_\t_\t_\t_\t_"
                temp_data.append(mwe_line)

                # Create the individual split lines
                for i, split_form in enumerate(splits):
                    # Maintain capitalization if the original MWE was capitalized
                    if i == 0 and form[0].isupper():
                        split_form = split_form.capitalize()

                    token_id = start_new_id + i

                    # For the first split token, retain the original POS/HEAD/DEPREL data.
                    # For the subsequent split tokens, blank them out for manual treebanking later.
                    if i == 0:
                        new_cols = [str(token_id), split_form, "_", "_", "_", "_", cols[6], cols[7], "_", "_"]
                    else:
                        new_cols = [str(token_id), split_form, "_", "_", "_", "_", "_", "_", "_", "_"]

                    temp_data.append('\t'.join(new_cols))

                # Map the old ID to the ID of the FIRST split token for dependency consistency
                old_to_new_id[old_id] = str(start_new_id)

                offset += (split_count - 1)
            else:
                # Normal token: Just shift its ID by the current offset
                new_id = int(old_id) + offset
                cols[0] = str(new_id)
                old_to_new_id[old_id] = str(new_id)
                temp_data.append('\t'.join(cols))

        # Second pass: Update HEAD mappings with the newly calculated IDs
        final_data = []
        for row in temp_data:
            cols = row.split('\t')
            # Only update dependencies on standard token lines (not MWE intervals or empty nodes)
            if len(cols) == 10 and '-' not in cols[0] and '.' not in cols[0]:
                old_head = cols[6]
                if old_head in old_to_new_id:
                    cols[6] = old_to_new_id[old_head]
            final_data.append('\t'.join(cols))

        # Reconstruct the block
        out_blocks.append('\n'.join(meta_lines + final_data))

    # Write the modified data to the output file
    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(out_blocks) + '\n\n')

    print(f"File processed successfully. Output saved to {output_filepath}")


if __name__ == "__main__":
    input_file = "el_cypriot-ud-test.conllu"
    output_file = "el_cypriot-ud-test-MWE.conllu"
    if os.path.exists(input_file):
        process_conllu(input_file, output_file)
    else:
        print(f"Error: {input_file} not found in the directory.")