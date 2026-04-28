from __future__ import annotations

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge a PEFT LoRA adapter into a base model.")
    parser.add_argument("--base-model", required=True, help="Local path or HF id of the base model")
    parser.add_argument("--adapter", required=True, help="Local path to the LoRA adapter")
    parser.add_argument("--output-dir", required=True, help="Directory to write merged HF model")
    parser.add_argument("--dtype", default="float16", choices=["auto", "float16", "bfloat16", "float32"])
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def resolve_dtype(name: str):
    if name == "auto":
        return "auto"
    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }[name]


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dtype = resolve_dtype(args.dtype)
    model_kwargs = {"trust_remote_code": args.trust_remote_code}
    tok_kwargs = {"trust_remote_code": args.trust_remote_code}
    if dtype != "auto":
        model_kwargs["torch_dtype"] = dtype

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, **tok_kwargs)
    base_model = AutoModelForCausalLM.from_pretrained(args.base_model, **model_kwargs)
    peft_model = PeftModel.from_pretrained(base_model, args.adapter)
    merged_model = peft_model.merge_and_unload()

    merged_model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    print(f"[OK] merged model saved to: {output_dir}")


if __name__ == "__main__":
    main()
