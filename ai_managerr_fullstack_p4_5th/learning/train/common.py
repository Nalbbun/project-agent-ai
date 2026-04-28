from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from datasets import load_dataset
from peft import LoraConfig


@dataclass
class TrainConfig:
    model_name: str
    train_jsonl: str
    valid_jsonl: str
    output_dir: str
    max_seq_length: int = 4096
    learning_rate: float = 2e-4
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    num_train_epochs: int = 2
    bf16: bool = True
    gradient_checkpointing: bool = True


def build_lora_config() -> LoraConfig:
    return LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )


def load_jsonl_dataset(train_path: str, valid_path: str):
    return load_dataset("json", data_files={"train": train_path, "validation": valid_path})


def to_messages(sample: Dict[str, Any]) -> Dict[str, Any]:
    role = sample["role"]
    user_payload = sample["input"]
    assistant_payload = sample["output"]
    return {
        "messages": [
            {"role": "system", "content": f"You are the {role} agent. Return structured JSON only."},
            {"role": "user", "content": str(user_payload)},
            {"role": "assistant", "content": str(assistant_payload)},
        ]
    }
