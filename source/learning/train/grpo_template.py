from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import GRPOConfig, GRPOTrainer


# NOTE:
# reward_func must return a list[float] aligned to completions.
# 아래 템플릿은 역할별 wrapper에서 실제 reward 함수로 교체해서 사용합니다.
def reward_func(prompts, completions, **kwargs):
    scores = []
    for completion in completions:
        content = completion[0]["content"] if isinstance(completion, list) else str(completion)
        scores.append(0.0 if not content else 0.5)
    return scores


def format_example(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt": [
            {"role": "system", "content": f"You are the {sample['role']} agent. Return structured JSON only."},
            {"role": "user", "content": str(sample["input"])}
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", required=True)
    parser.add_argument("--train_jsonl", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    ds = load_dataset("json", data_files={"train": args.train_jsonl})["train"].map(format_example)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype="auto", trust_remote_code=True)

    config = GRPOConfig(
        output_dir=args.output_dir,
        learning_rate=5e-6,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        num_generations=4,
        max_completion_length=1024,
        logging_steps=10,
        save_steps=100,
        bf16=True,
        report_to="none",
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=reward_func,
        args=config,
        train_dataset=ds,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main()
