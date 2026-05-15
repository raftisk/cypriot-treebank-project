# file: cypriotify.py
# Runs Armostis' normalization tool programmatically

import sys
import multiprocessing as mp
from ProcessCyGr import ProcessCyGr

# Global variable for the worker processes
tool = None

def init_worker():
    """Initializes the ProcessCyGr tool once per CPU core to save memory"""
    global tool
    tool = ProcessCyGr(data_path='./', rule_path='./', rule_files=['1-smooth.xlsx', '2-corrections.xlsx', '3-restore.xlsx'])

def process_chunk(line):
    """Worker function that processes a single line"""
    clean_line = line.strip()
    if not clean_line:
        return ""
    
    # Send the line through the normalization logic
    processed = tool.process_single_line(clean_line)
    return processed

if __name__ == '__main__':
    # Force Python to handle Greek characters safely in the stream
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    
    # Fire up a worker for every CPU core
    cores = mp.cpu_count()
    
    # imap processes the stream in chunks without loading everything into RAM
    with mp.Pool(processes=cores, initializer=init_worker) as pool:
        for processed_line in pool.imap(process_chunk, sys.stdin, chunksize=5000):
            if processed_line:
                sys.stdout.write(processed_line + '\n')