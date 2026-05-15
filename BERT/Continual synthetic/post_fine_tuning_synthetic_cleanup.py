# file: post_fine_tuning_synthetic_cleanup.py
# Explicitly setting metadata to avoid issues later

import json
import os

final_dir = "./cypriot-synthetic-finetuned"
print("Hardening final model metadata...")

# Clean the Model Config
config_path = os.path.join(final_dir, "config.json")
with open(config_path, "r+") as f:
    cfg = json.load(f)
    cfg["model_type"] = "modernbert"
    if "transformers_version" in cfg: del cfg["transformers_version"]
    f.seek(0); json.dump(cfg, f, indent=2); f.truncate()

# Clean the Tokenizer Config
t_config_path = os.path.join(final_dir, "tokenizer_config.json")
with open(t_config_path, "r+") as f:
    t_cfg = json.load(f)
    t_cfg["tokenizer_class"] = "PreTrainedTokenizerFast"
    t_cfg["add_prefix_space"] = True
    t_cfg["clean_up_tokenization_spaces"] = True
    if "transformers_version" in t_cfg: del t_cfg["transformers_version"]
    f.seek(0); json.dump(t_cfg, f, indent=2); f.truncate()

print("Final model ready for use")