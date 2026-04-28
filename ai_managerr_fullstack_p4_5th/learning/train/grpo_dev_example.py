from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import GRPOConfig, GRPOTrainer

from rewards.dev import compute_dev_reward

SCHEMA_PATH = str(Path(__file__).resolve().parents[1] / "schemas" / "dev-be.schema.json")


def reward_func(prompts, completions, **kwargs):
    scores = []
    for completion in completions:
        content = completion[0]["content"] if isinstance(completion, list) else str(completion)
        result = compute_dev_reward(
            completion_text=content,
            schema_path=SCHEMA_PATH,
            build_cmd=["bash", "-lc", "true"],
            test_cmd=["bash", "-lc", "true"],
            lint_cmd=["bash", "-lc", "true"],
        )
        scores.append(float(result["reward"]))
    return scores


def format_example(sample):
    return {
        "prompt": [
            {"role": "system", "content": "You are the dev-be agent. Return structured JSON only."},
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
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype="auto", trust_remote_code=True)

    cfg = GRPOConfig(
        output_dir=args.output_dir,
        learning_rate=5e-6,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        num_generations=4,
        max_completion_length=1024,
        bf16=True,
        logging_steps=10,
        save_steps=100,
        report_to="none",
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=reward_func,
        args=cfg,
        train_dataset=ds,
    )
    trainer.train()
    trainer.save_model(args.output_dir)


if __name__ == "__main__":
    main()
