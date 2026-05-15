# file: post_continual_cleanup.py
# Explicitly setting metadata to avoid issues later, saving checkpoint separately

import json
import os
import shutil

source_dir = "./cypriot-synthetic-checkpoint"
fortified_dir = "./cypriot-synthetic-base"

print(f"Creating copy at '{fortified_dir}'...")

# 1. Safely clone the directory
if os.path.exists(fortified_dir):
    print(f"Error: Target directory '{fortified_dir}' already exists.")
    print("Please remove or rename it first to avoid mixing files.")
    exit(1)

shutil.copytree(source_dir, fortified_dir)
print("Copy successful. Hardening metadata in the new folder...")

# 2. Clean the Model Config
config_path = os.path.join(fortified_dir, "config.json")
with open(config_path, "r+") as f:
    cfg = json.load(f)
    cfg["model_type"] = "modernbert"
    if "transformers_version" in cfg: 
        del cfg["transformers_version"]
    f.seek(0)
    json.dump(cfg, f, indent=2)
    f.truncate()

# 3. Clean the Tokenizer Config
t_config_path = os.path.join(fortified_dir, "tokenizer_config.json")
with open(t_config_path, "r+") as f:
    t_cfg = json.load(f)
    t_cfg["tokenizer_class"] = "PreTrainedTokenizerFast"
    t_cfg["add_prefix_space"] = True
    t_cfg["clean_up_tokenization_spaces"] = True
    if "transformers_version" in t_cfg: 
        del t_cfg["transformers_version"]
    f.seek(0)
    json.dump(t_cfg, f, indent=2)
    f.truncate()

print("Copy ready for use")