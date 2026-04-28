python sft_template.py \
  --model_name Qwen/Qwen2.5-3B-Instruct \
  --train_jsonl ../data_examples/architect.train.jsonl \
  --valid_jsonl ../data_examples/architect.valid.jsonl \
  --output_dir ../artifacts/architect-lora
