"""Convert a YuE Studio training checkpoint into the bundled ComfyUI adapter format."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from safetensors.torch import save_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    source = Path(args.checkpoint)
    destination = Path(args.destination)
    saved = torch.load(source, map_location="cpu", weights_only=False)
    values = saved.get("lora", [])
    rank = int(saved.get("rank", 0))
    if not rank or len(values) % 14:
        raise RuntimeError("This is not a compatible YuE Studio LoRA checkpoint.")
    targets = (("self_attn", ("q_proj", "k_proj", "v_proj", "o_proj")), ("mlp", ("gate_proj", "up_proj", "down_proj")))
    state, index = {}, 0
    for layer in range(len(values) // 14):
        for group, names in targets:
            for name in names:
                # ComfyUI's generic Load LoRA maps YuE2 weights through the
                # BaseModel state-dict namespace, which starts at diffusion_model.
                prefix = f"diffusion_model.model.layers.{layer}.{group}.{name}"
                state[prefix + ".lora_A.weight"] = values[index].contiguous()
                state[prefix + ".lora_B.weight"] = values[index + 1].contiguous()
                index += 2
    destination.mkdir(parents=True, exist_ok=True)
    save_file(state, str(destination / "adapter_model.safetensors"))
    (destination / "adapter_config.json").write_text(json.dumps({"peft_type": "LORA", "r": rank, "lora_alpha": rank, "target_modules": [key.rsplit(".lora_", 1)[0] for key in state if key.endswith(".lora_A.weight")]}, indent=2), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
