python sft_template.py \
  --model_name Qwen/Qwen2.5-Coder-1.5B-Instruct \
  --train_jsonl ../data_examples/dev-fe.train.jsonl \
  --valid_jsonl ../data_examples/dev-fe.valid.jsonl \
  --output_dir ../artifacts/dev-fe-lora
