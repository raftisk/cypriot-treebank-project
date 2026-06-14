import argparse
import conllu
import pandas as pd

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

            #TODO:handle case where one variant only is empty
            
            # original Cypriot greek token added as misc field (10th column) 
            misc = cg_token

            sentence_text += cg_token + " "

            token = {
                'id': token_id,
                'form': smg_token,
                'lemma': "_",
                'upos': "_",
                'xpos': "_",
                'feats': "_",
                'head': "_",
                'deprel': "_",
                'deps': "_",
                'misc': misc
            }

            sentence_tokens.append(token)
            token_id += 1

        if sentence_tokens:
            sentence = conllu.TokenList(sentence_tokens, metadata={"sent_id": str(sent_id), "text": sentence_text.strip()})
            sentences.append(sentence)
            sent_id += 1
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence in sentences:
            f.write(sentence.serialize())
            f.write('\n\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Excel file to CoNLL-U format.")
    parser.add_argument("--input_file", help="Path to the input Excel file.")
    parser.add_argument("--output_file", help="Path to the output CoNLL-U file.")

    args = parser.parse_args()

    convert_excel_to_conllu(args.input_file, args.output_file)







        
