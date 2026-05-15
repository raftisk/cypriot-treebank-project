#!/bin/bash

# Training script for Cypriot BERT on 8x H100 GPUs
# Run with: bash train_cypriot_bert.sh
# Download the fine-tuning script from huggingface first:
# wget https://raw.githubusercontent.com/huggingface/transformers/main/examples/pytorch/language-modeling/run_mlm.py

# Reasoning:
# Batch size particularly small to increase the steps because we need to train the newly-added Cypriot tokens from scratch
# Number of epochs similarly slightly above the industry standard for fine-tuning on small datasets for the same reason
# Using warmup and weight decay for the same reason
# Everything else is industry-standard

torchrun --nproc_per_node=8 run_mlm.py \
    --model_name_or_path ./cypriot-synthetic-checkpoint \
    --train_file embeddings_data_all.txt \
    --validation_split_percentage 5 \
    --per_device_train_batch_size 16 \
    --per_device_eval_batch_size 16 \
    --do_train \
    --do_eval \
    --output_dir ./cypriot-synthetic-finetuned \
    --eval_strategy "steps" \
    --eval_steps 50 \
    --save_strategy "steps" \
    --save_steps 50 \
    --load_best_model_at_end True \
    --metric_for_best_model "loss" \
    --optim "adamw_torch_fused" \
    --learning_rate 3e-5 \
    --num_train_epochs 5 \
    --warmup_ratio 0.1 \
    --weight_decay 0.01 \
    --max_seq_length 512 \
    --bf16 \
    --tf32 True \
    --torch_compile True \
    --dataloader_num_workers 16 \
    --overwrite_output_dir True