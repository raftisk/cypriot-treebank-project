#!/bin/bash

# Training script for Cypriot BERT on 8x H100 GPUs
# Run with: bash continual_train.sh
# Download the fine-tuning script from huggingface first:
# wget https://raw.githubusercontent.com/huggingface/transformers/main/examples/pytorch/language-modeling/run_mlm.py

# Reasoning:
# Batch size needs to be this small to fit on the GPUs because of the large vocabulary size
# We want a larger effective batch size due to the size of our data and the desire for more stable continual
# pre-training, so we use gradient_accumulation_steps = 8 for an effective batch size of 2048
# Huge dataset so one epoch is enough, small val split for the same reason
# Larger lr than fine-tuning script because we're less afraid of catastrophic forgetting
# Using warmup and weight decay largely for our new tokens
# Everything else is industry-standard

torchrun --nproc_per_node=8 run_mlm.py \
    --model_name_or_path ./cypriot-base-model \
    --train_file synthetic_cypriot_data.txt \
    --validation_split_percentage 1 \
    --per_device_train_batch_size 32 \
    --gradient_accumulation_steps 8 \
    --per_device_eval_batch_size 16 \
    --do_train \
    --do_eval \
    --gradient_checkpointing False \
    --output_dir ./cypriot-synthetic-checkpoint \
    --eval_strategy "steps" \
    --eval_steps 2500 \
    --save_strategy "steps" \
    --save_steps 2500 \
    --save_total_limit 2 \
    --load_best_model_at_end True \
    --metric_for_best_model "loss" \
    --optim "adamw_torch_fused" \
    --learning_rate 2e-4 \
    --lr_scheduler_type "cosine" \
    --warmup_ratio 0.05 \
    --adam_beta2 0.98 \
    --num_train_epochs 1 \
    --weight_decay 0.01 \
    --max_seq_length 512 \
    --bf16 \
    --tf32 True \
    --torch_compile True \
    --dataloader_num_workers 16 \
    --preprocessing_num_workers 64 \
    --ddp_timeout 86400 \
    --overwrite_output_dir