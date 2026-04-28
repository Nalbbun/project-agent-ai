python sft_template.py \
  --model_name Qwen/Qwen2.5-3B-Instruct \
  --train_jsonl ../data_examples/qa.train.jsonl \
  --valid_jsonl ../data_examples/qa.valid.jsonl \
  --output_dir ../artifacts/qa-lora
