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
    state = {}

    def add(prefix: str, down: torch.Tensor, up: torch.Tensor) -> None:
        state[prefix + ".lora_A.weight"] = down.contiguous()
        state[prefix + ".lora_B.weight"] = up.contiguous()

    def add_fused(prefix: str, pairs: list[tuple[torch.Tensor, torch.Tensor]]) -> None:
        """Pack independent LoRAs into ComfyUI's fused projection layout."""
        down = torch.cat([item[0] for item in pairs], dim=0)
        up = torch.zeros(sum(item[1].shape[0] for item in pairs), down.shape[0], dtype=pairs[0][1].dtype)
        rows = columns = 0
        for item_down, item_up in pairs:
            next_rows, next_columns = rows + item_up.shape[0], columns + item_down.shape[0]
            up[rows:next_rows, columns:next_columns] = item_up
            rows, columns = next_rows, next_columns
        add(prefix, down, up)

    # YuE Studio trains the upstream, split semantic projections. ComfyUI stores
    # the same text encoder as packed QKV and gate/up matrices.
    for layer in range(len(values) // 14):
        offset = layer * 14
        q, k, v, o = [(values[offset + index], values[offset + index + 1]) for index in (0, 2, 4, 6)]
        gate, up, down = [(values[offset + index], values[offset + index + 1]) for index in (8, 10, 12)]
        prefix = f"text_encoders.model.layers.{layer}"
        add_fused(prefix + ".self_attn.qkv_proj", [q, k, v])
        add(prefix + ".self_attn.o_proj", *o)
        add_fused(prefix + ".mlp.gate_up_proj", [gate, up])
        add(prefix + ".mlp.down_proj", *down)
    destination.mkdir(parents=True, exist_ok=True)
    save_file(state, str(destination / "adapter_model.safetensors"))
    (destination / "adapter_config.json").write_text(json.dumps({"peft_type": "LORA", "r": rank, "lora_alpha": rank, "target_modules": [key.rsplit(".lora_", 1)[0] for key in state if key.endswith(".lora_A.weight")]}, indent=2), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
