"""YuE Studio LoRA Loader for ComfyUI.

Copy this folder into ComfyUI/custom_nodes, then restart ComfyUI.
"""
import json
from pathlib import Path


class YuEStudioLoRALoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"lora_path": ("STRING", {"default": ""}), "scale": ("FLOAT", {"default": 1.0, "min": -4.0, "max": 4.0, "step": 0.05})}}

    RETURN_TYPES = ("YUE_LORA",)
    FUNCTION = "load_lora"
    CATEGORY = "YuE Studio"

    def load_lora(self, lora_path, scale=1.0):
        from safetensors.torch import load_file
        root = Path(lora_path).expanduser()
        weights = root / "adapter_model.safetensors" if root.is_dir() else root
        config = weights.parent / "adapter_config.json"
        state = load_file(str(weights))
        pairs = {}
        for key, value in state.items():
            if key.endswith(".lora_A.weight"):
                pairs.setdefault(key[:-14], {})["A"] = value
            elif key.endswith(".lora_B.weight"):
                pairs.setdefault(key[:-14], {})["B"] = value
        cfg = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
        rank = int(cfg.get("r") or 1)
        alpha = float(cfg.get("lora_alpha") or rank)
        return ({"path": str(root), "scale": float(scale), "scaling": alpha / rank, "deltas": {name: (v["A"], v["B"]) for name, v in pairs.items() if "A" in v and "B" in v}},)


NODE_CLASS_MAPPINGS = {"YuEStudioLoRALoader": YuEStudioLoRALoader}
NODE_DISPLAY_NAME_MAPPINGS = {"YuEStudioLoRALoader": "YuE Studio LoRA Loader"}
