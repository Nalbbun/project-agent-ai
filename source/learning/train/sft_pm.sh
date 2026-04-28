python sft_template.py \
  --model_name LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct \
  --train_jsonl ../data_examples/pm.train.jsonl \
  --valid_jsonl ../data_examples/pm.valid.jsonl \
  --output_dir ../artifacts/pm-lora
