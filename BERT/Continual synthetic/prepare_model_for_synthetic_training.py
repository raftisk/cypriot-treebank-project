# file: prepare_model_for_synthetic_training.py
# Adds extra tokens extracted from our training dataset, initializing them using the mean
# Trains a new tokenizer on our data, with a size larger than the default one, and appends the
# top original tokens of the new tokenizer to the default one
# (not used since we had it ready from the default scenario)

import torch
import json
import os
from transformers import AutoTokenizer, AutoModelForMaskedLM

# script options
base_model_name = "jhu-clsp/mmbert-base"
corpus_file = "embeddings_data_all.txt"
output_dir = "./cypriot-base-model"
num_new_tokens_to_add = 1000

# Load the base model
print("Loading base model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(base_model_name)
model = AutoModelForMaskedLM.from_pretrained(base_model_name)
base_vocab = set(tokenizer.get_vocab().keys())

def get_training_corpus():
    with open(corpus_file, "r", encoding="utf-8") as f:
        batch = []
        for line in f:
            batch.append(line.strip())
            if len(batch) == 50000:
                yield batch
                batch = []
        if batch:
            yield batch

# Train tokenizer from scratch on Cypriot data
print("Training Cypriot tokenizer...")
temp_tokenizer = tokenizer.train_new_from_iterator(get_training_corpus(), vocab_size=265000)    # make it a bit larger than the original tokenizer

temp_vocab = temp_tokenizer.get_vocab()
sorted_temp_vocab = sorted(temp_vocab.items(), key=lambda x: x[1])

new_cypriot_tokens = []
for token, _ in sorted_temp_vocab:
    # Ensure it's new and contains at least one letter
    if token not in base_vocab and any(c.isalpha() for c in token):
        new_cypriot_tokens.append(token)
    if len(new_cypriot_tokens) >= num_new_tokens_to_add: 
        break

print(f"Extracted {len(new_cypriot_tokens)} Cypriot tokens. Injecting into model...")

# Initializing new tokens to the mean
print("Applying Mean Token Initialization...")
old_embeddings = model.get_input_embeddings().weight.data.clone()
clean_base_tokenizer = AutoTokenizer.from_pretrained(base_model_name)

tokenizer.add_tokens(new_cypriot_tokens)
model.resize_token_embeddings(len(tokenizer))
new_embeddings = model.get_input_embeddings().weight.data

for token in new_cypriot_tokens:
    new_id = tokenizer.convert_tokens_to_ids(token)
    
    clean_token_str = token.replace('▁', ' ').strip()
    subword_ids = clean_base_tokenizer.encode(clean_token_str, add_special_tokens=False)
    
    if subword_ids:
        subword_embeds = old_embeddings[subword_ids]
        new_embeddings[new_id] = torch.mean(subword_embeds, dim=0)

tokenizer.save_pretrained(output_dir)
model.save_pretrained(output_dir)

# Explicitly setting metadata to avoid issues later
print("Applying Version-Safe Metadata Patches...")
# Patch Config
with open(os.path.join(output_dir, "config.json"), "r+") as f:
    cfg = json.load(f)
    cfg["model_type"] = "modernbert"
    if "transformers_version" in cfg: del cfg["transformers_version"]
    f.seek(0); json.dump(cfg, f, indent=2); f.truncate()

# Patch Tokenizer Config
with open(os.path.join(output_dir, "tokenizer_config.json"), "r+") as f:
    t_cfg = json.load(f)
    t_cfg["tokenizer_class"] = "PreTrainedTokenizerFast"
    t_cfg["add_prefix_space"] = True
    t_cfg["clean_up_tokenization_spaces"] = True
    if "transformers_version" in t_cfg: del t_cfg["transformers_version"]
    f.seek(0); json.dump(t_cfg, f, indent=2); f.truncate()

print(f"Model saved to {output_dir}")