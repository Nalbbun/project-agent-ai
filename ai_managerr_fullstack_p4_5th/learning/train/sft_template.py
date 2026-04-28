from __future__ import annotations

import argparse

from peft import get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer

from common import TrainConfig, build_lora_config, load_jsonl_dataset, to_messages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", required=True)
    parser.add_argument("--train_jsonl", required=True)
    parser.add_argument("--valid_jsonl", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    cfg = TrainConfig(
        model_name=args.model_name,
        train_jsonl=args.train_jsonl,
        valid_jsonl=args.valid_jsonl,
        output_dir=args.output_dir,
    )

    ds = load_jsonl_dataset(cfg.train_jsonl, cfg.valid_jsonl)
    ds = ds.map(to_messages, remove_columns=ds["train"].column_names)

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_name,
        torch_dtype="auto",
        trust_remote_code=True,
    )
    model = get_peft_model(model, build_lora_config())

    training_args = TrainingArguments(
        output_dir=cfg.output_dir,
        learning_rate=cfg.learning_rate,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        num_train_epochs=cfg.num_train_epochs,
        bf16=cfg.bf16,
        logging_steps=10,
        save_steps=200,
        eval_steps=200,
        evaluation_strategy="steps",
        gradient_checkpointing=cfg.gradient_checkpointing,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)


if __name__ == "__main__":
    main()
