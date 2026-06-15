import argparse
import conllu
import pandas as pd

from MWE_split_for_CONLLU import MWE_MAP


def split_parts(token):
    """Returns the word parts of a single surface token."""

    # check for known MWE
    parts = MWE_MAP.get(token.lower())
    if parts is not None:
        parts = list(parts)
        # Preserve capitalization of the original surface form
        if token[:1].isupper():
            parts[0] = parts[0].capitalize()
        return parts

    # catch whitespace-separated words 
    pieces = token.split()
    if len(pieces) > 1:
        return pieces
    return [token]


def _align_mwt(cg_str, smg_str):
    """Resolve aligned (cg_parts, smg_parts) for a token pair.

    Returns the parts plus a flag indicating whether this is a multiword
    token. Handles misalignment cases by warning and returning the unsplit forms.
    """
    cg_parts = split_parts(cg_str)
    cg_length = len(cg_parts)

    smg_parts = split_parts(smg_str)
    smg_length = len(smg_parts)

    if cg_length == 1 and smg_length == 1:
        return [cg_str], [smg_str], False

    if cg_length > 1 and smg_length > 1 and cg_length != smg_length:
        print(f"WARNING: conflicting MWT split counts for "
              f"CG={cg_str!r} ({cg_length}) / SMG={smg_str!r} ({smg_length}); left unsplit.")
        return [cg_str], [smg_str], False

    # If the SMG side splits but the CG side does not, warn and skip.
    if cg_length == 1:
        # special case: "εννά" is interpreted as "είναι να"
        if cg_str.lower() == 'εννά' and smg_str.lower() == 'είναι να':
            return ["εν’", "να"], ["είναι", "να"], True
        else: 
            print(f"WARNING: SMG splits but CG does not for "
                  f"CG={cg_str!r} / SMG={smg_str!r}; left unsplit.")
            return [cg_str], [smg_str], False

    # if SMG did not split, reuse the CG parts
    if smg_length == 1:
        smg_parts = list(cg_parts)
    return cg_parts, smg_parts, True


def make_token(token_id, form, cg_form):
    return {
        'id': token_id,
        'form': form,
        'lemma': "_",
        'upos': "_",
        'xpos': "_",
        'feats': "_",
        'head': "_",
        'deprel': "_",
        'deps': "_",
        'misc': f"CypriotGreek={cg_form}"
    }


def convert_excel_to_conllu(excel_file, output_file):

    df = pd.read_excel(excel_file, sheet_name=1)

    token_cols = [col for col in df.columns if col.startswith('token_')]
    sentences = []

    grouped_per_sentence = df.groupby('sentence_id')

    sent_id = 1
    for _, group in grouped_per_sentence:
        cg_row = group.iloc[0]
        smg_row = group.iloc[1]

        sentence_tokens = []
        sentence_text = ""
        token_id = 1

        for col in token_cols:
            cg_token = cg_row[col]
            smg_token = smg_row[col]
            
            #break if both tokens are NaN
            if pd.isna(cg_token) and pd.isna(smg_token):
                break

            #if SMG token is empty, use CG token directly
            if pd.isna(smg_token):
                smg_token = cg_token

            cg_str = str(cg_token).strip()
            smg_str = str(smg_token).strip()

            sentence_text += smg_str + " "

            cg_parts, smg_parts, is_mwt = _align_mwt(cg_str, smg_str)

            if not is_mwt:
                sentence_tokens.append(make_token(token_id, smg_str, cg_str))
                token_id += 1
                continue

            # Multiword token: emit a range row followed by one row per word
            n = len(cg_parts)
            start, end = token_id, token_id + n - 1
            sentence_tokens.append(make_token((start, '-', end), smg_str, cg_str))
            for i in range(n):
                sentence_tokens.append(make_token(start + i, smg_parts[i], cg_parts[i]))
            token_id = end + 1

        if sentence_tokens:
            sentence = conllu.TokenList(sentence_tokens, metadata={"sent_id": str(sent_id), "text": sentence_text.strip()})
            sentences.append(sentence)
            sent_id += 1
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence in sentences:
            f.write(sentence.serialize())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Excel file to CoNLL-U format.")
    parser.add_argument("--input_file", help="Path to the input Excel file.")
    parser.add_argument("--output_file", help="Path to the output CoNLL-U file.")

    args = parser.parse_args()

    convert_excel_to_conllu(args.input_file, args.output_file)







        
