# file: stream_greek.py
# Streams the Greek subset of FineWeb2

from datasets import load_dataset
import sys

# Force UTF-8 so the terminal doesn't crash on Greek characters
sys.stdout.reconfigure(encoding='utf-8')

# Stream only the Greek subset from FineWeb2
dataset = load_dataset("HuggingFaceFW/fineweb-2", "ell_Grek", split="train", streaming=True)

for row in dataset:
    # Clean out newlines so every document is a single line
    clean_text = row["text"].replace("\n", " ").strip()
    
    # Write directly to standard output (intended to be piped into cypriotify.py)
    sys.stdout.write(clean_text + "\n")