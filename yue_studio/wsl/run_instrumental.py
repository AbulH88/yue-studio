"""Prepare an isolated instrumental dataset and train the verified YuE2 AR LoRA.

This runner executes inside WSL and reads every machine/run-specific path from a
manifest written by YuE Studio. It never uses the historical shared training paths.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.signal import resample_poly
from torch.utils.checkpoint import checkpoint


def read_style(path: Path) -> str:
    caption = path.read_text(encoding="utf-8", errors="replace")
    caption = caption.split("===LYRICS===", 1)[0].replace("Global Metadata:", "").strip()
    return " ".join(caption.split())[:1500]


def stage(manifest: dict) -> Path:
    run_dir = Path(manifest["paths"]["run_dir"])
    source = run_dir / "source"
    source.mkdir(parents=True, exist_ok=True)
    print("STAGE staging", flush=True)
    for item in manifest["dataset"]["files"]:
        output = source / f"{item['name']}.flac"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", item["wsl_path"], "-ar", "48000", "-ac", "2", str(output)],
            check=True,
        )
        (source / f"{item['name']}.txt").write_text(item["caption"].strip() + "\n", encoding="utf-8")
        (source / f"{item['name']}.lyrics.txt").write_text("[instrumental]\n", encoding="utf-8")
        print(f"staged {item['original_name']} -> {output.name}", flush=True)
    return source


def prepare_features(manifest: dict, source: Path) -> None:
    import soundfile as sf
    from transformers import AutoFeatureExtractor, AutoModel
    from yue2.modeling_vae import YuE2VAE
    from yue2.protocol import SongRequest, token_prefixes
    from yue2.tokenization_yue2 import YuE2TextTokenizer

    print("STAGE preparing", flush=True)
    paths = manifest["paths"]
    run_dir = Path(paths["run_dir"])
    prep = run_dir / "prep"
    prep.mkdir(parents=True, exist_ok=True)
    device = "cuda"
    tokenizer = YuE2TextTokenizer(str(Path(paths["yue2_model"]) / "qwen.tiktoken"))
    processor = AutoFeatureExtractor.from_pretrained(paths["mert"], trust_remote_code=True, local_files_only=True)
    mert = AutoModel.from_pretrained(paths["mert"], trust_remote_code=True, local_files_only=True).to(device).eval()
    vae = YuE2VAE.from_pretrained(paths["vae"], decoder_only=False, device=device, local_files_only=True)

    def mert_l20(mono24: np.ndarray) -> np.ndarray:
        chunk_size = 24000 * 30
        chunks = [mono24[start:start + chunk_size] for start in range(0, len(mono24), chunk_size)]
        chunks = [chunk for chunk in chunks if len(chunk) >= 24000]
        full = [chunk for chunk in chunks if len(chunk) == chunk_size]
        tail = [chunk for chunk in chunks if len(chunk) < chunk_size]
        features = []
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            for group in ([full] if full else []) + [[chunk] for chunk in tail]:
                inputs = {key: value.to(device) for key, value in processor(group, sampling_rate=24000, return_tensors="pt").items()}
                features.append(mert(**inputs, output_hidden_states=True).hidden_states[20].reshape(-1, 1024))
        combined = torch.cat(features, 0).float()
        frames = int(round(len(mono24) / 24000 * 25))
        return F.interpolate(combined.T[None], size=frames, mode="linear", align_corners=False)[0].T.half().cpu().numpy()

    def latents(stereo48: np.ndarray) -> np.ndarray:
        output = []
        chunk_size = 48000 * 60
        with torch.inference_mode():
            for start in range(0, len(stereo48), chunk_size):
                segment = stereo48[start:start + chunk_size]
                if len(segment) < 1920:
                    break
                output.append(vae.encode(torch.tensor(segment.T[None]))[0].T.float().cpu())
        return torch.cat(output, 0).numpy()

    for audio in sorted(source.glob("*.flac")):
        name = audio.stem
        destination = prep / name
        destination.mkdir(parents=True, exist_ok=True)
        samples, sample_rate = sf.read(audio, dtype="float32")
        if samples.ndim == 1:
            samples = np.stack([samples, samples], axis=1)
        divisor = math.gcd(sample_rate, 48000)
        stereo48 = resample_poly(samples, 48000 // divisor, sample_rate // divisor, axis=0).astype(np.float32) if sample_rate != 48000 else samples
        divisor = math.gcd(sample_rate, 24000)
        mono24 = resample_poly(samples.mean(1), 24000 // divisor, sample_rate // divisor).astype(np.float32)
        mert_features = mert_l20(mono24)
        vae_latents = latents(stereo48)
        count = min(len(mert_features), len(vae_latents))
        np.save(destination / "mert.npy", mert_features[:count])
        np.save(destination / "lat.npy", vae_latents[:count].astype(np.float32))
        style = read_style(source / f"{name}.txt")
        prefix = token_prefixes(SongRequest(style=style, lyrics="[instrumental]", cot="off", seed=1, id="real"), tokenizer)
        np.save(destination / "prefix.npy", np.array(prefix, dtype=np.int64))
        print(f"prepared {name}: {count} frames ({count / 25 / 60:.1f} min)", flush=True)


class TokenizerHead(nn.Module):
    def __init__(self, input_size: int = 1024):
        super().__init__()
        width, window, layers, heads, vocab = 512, 512, 8, 8, 32768
        self.inp = nn.Linear(input_size, width)
        self.pos = nn.Parameter(torch.zeros(1, window, width))
        layer = nn.TransformerEncoderLayer(width, heads, 4 * width, dropout=0.1, batch_first=True, norm_first=True, activation="gelu")
        self.enc = nn.TransformerEncoder(layer, layers)
        self.norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, vocab)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.head(self.norm(self.enc(self.inp(value) + self.pos[:, :value.shape[1]])))


def load_head(path: str, device: str) -> dict:
    if path.endswith(".safetensors"):
        from safetensors.torch import load_file
        return load_file(path, device=device)
    value = torch.load(path, map_location=device, weights_only=False)
    return value["model"] if "model" in value else value


def build_dataset(manifest: dict, source: Path) -> Path:
    from yue2.protocol import SongRequest, token_prefixes
    from yue2.tokenization_yue2 import YuE2TextTokenizer

    paths = manifest["paths"]
    run_dir = Path(paths["run_dir"])
    prep = run_dir / "prep"
    dataset_path = run_dir / "ar" / "dataset.pt"
    device = "cuda"
    head = TokenizerHead().to(device).eval()
    head.load_state_dict(load_head(paths["tokenizer_head"], device))
    tokenizer = YuE2TextTokenizer(str(Path(paths["yue2_model"]) / "qwen.tiktoken"))
    window = 512

    @torch.no_grad()
    def predict(features: np.ndarray) -> np.ndarray:
        normalized = features.astype(np.float32)
        normalized = (normalized - normalized.mean(0)) / (normalized.std(0) + 1e-5)
        total = len(normalized)
        output = np.zeros(total, dtype=np.int64)
        starts = list(range(0, max(1, total - window + 1), window // 2))
        if starts[-1] + window < total:
            starts.append(max(0, total - window))
        for start in starts:
            part = normalized[start:start + window]
            length = len(part)
            if length < window:
                part = np.pad(part, ((0, window - length), (0, 0)))
            with torch.autocast("cuda", dtype=torch.bfloat16):
                prediction = head(torch.tensor(part[None], device=device))[0, :length].float().argmax(-1).cpu().numpy()
            low = start + (0 if start == 0 else window // 4)
            high = start + length - (0 if start + length >= total else window // 4)
            output[low:high] = prediction[low - start:high - start]
        return output

    data = []
    for directory in sorted(path for path in prep.iterdir() if path.is_dir()):
        name = directory.name
        codec = predict(np.load(directory / "mert.npy"))
        style = read_style(source / f"{name}.txt")
        prefix = token_prefixes(SongRequest(style=style, lyrics="[instrumental]", cot="off", seed=1, id="instrumental"), tokenizer)
        data.append({"name": name, "src": "artist", "style": style, "lyrics": "[instrumental]", "prefix": prefix, "codec": codec.astype(np.int32)})
        print(f"tokenized {name}: {len(codec)} frames", flush=True)
    torch.save(data, dataset_path)
    print(f"AR PREP DONE {len(data)} tracks -> {dataset_path}", flush=True)
    return dataset_path


def train(manifest: dict, dataset_path: Path) -> None:
    from yue2.modeling_yue2 import YuE2ForCausalLM
    from yue2.nar import attention as nar_attention
    from yue2.protocol import CODEC_OFFSET, MUSIC_END

    print("STAGE training", flush=True)
    paths = manifest["paths"]
    config = manifest["training"]
    output = Path(paths["run_dir"]) / "checkpoints"
    output.mkdir(parents=True, exist_ok=True)
    device = "cuda"
    steps = int(config["steps"])
    rank = int(config["rank"])
    learning_rate = float(config["learning_rate"])
    checkpoint_every = max(1, int(config["checkpoint_every"]))
    max_length, accumulation, chunk = 12288, 2, 1024
    schedule_steps = 3000
    seed = int(config.get("seed", 1))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    model = YuE2ForCausalLM.from_pretrained(paths["yue2_model"], local_files_only=True, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).eval().to(device)
    model.requires_grad_(False)
    backbone = model.model

    class LoRALinear(nn.Module):
        def __init__(self, base: nn.Linear, lora_rank: int):
            super().__init__()
            self.base = base
            self.A = nn.Parameter(torch.randn(lora_rank, base.in_features, device=base.weight.device) * (1 / math.sqrt(base.in_features)))
            self.B = nn.Parameter(torch.zeros(base.out_features, lora_rank, device=base.weight.device))

        def forward(self, value: torch.Tensor) -> torch.Tensor:
            return self.base(value) + ((value.float() @ self.A.T) @ self.B.T).to(value.dtype)

    lora = []
    for layer in backbone.layers:
        for module, names in ((layer.self_attn, ("q_proj", "k_proj", "v_proj", "o_proj")), (layer.mlp, ("gate_proj", "up_proj", "down_proj"))):
            for name in names:
                replacement = LoRALinear(getattr(module, name), rank)
                setattr(module, name, replacement)
                lora.extend([replacement.A, replacement.B])
    cursor_head = nn.Linear(model.config.hidden_size, model.config.hidden_size, bias=False).to(device)
    nn.init.eye_(cursor_head.weight)
    optimizer = torch.optim.AdamW(
        [{"params": lora, "lr": learning_rate, "weight_decay": 0.0}, {"params": cursor_head.parameters(), "lr": learning_rate, "weight_decay": 0.0}],
        betas=(0.9, 0.95),
    )
    data = torch.load(dataset_path, weights_only=False)
    if not data:
        raise RuntimeError("Prepared training dataset is empty.")
    print(f"AR LoRA params {sum(parameter.numel() for parameter in lora) / 1e6:.1f}M lr {learning_rate}", flush=True)
    print(f"artist {len(data)} regularizer 0", flush=True)

    def sequence(item: dict) -> tuple[torch.Tensor, int]:
        prefix = list(item["prefix"])
        codec = [int(code) + CODEC_OFFSET for code in item["codec"]]
        room = max_length - len(prefix) - 1
        body = codec[:room] + ([MUSIC_END] if len(codec) <= room else [])
        return torch.tensor([prefix + body], device=device), len(prefix)

    def ar_layer(layer, value, cosine, sine):
        query, key, val = layer.self_attn.project_qkv(layer.input_layernorm(value), cosine, sine)
        hidden = nar_attention(query[0], key[0], val[0], causal=True)
        value = value + layer.self_attn.o_proj(hidden.flatten(1)[None])
        return value + layer.mlp(layer.post_attention_layernorm(value))

    def language_loss(ids: torch.Tensor, prefix_length: int, gradient: bool = True) -> torch.Tensor:
        value = backbone.embed_tokens(ids)
        length = ids.shape[1]
        cosine, sine = backbone.rotary_emb(torch.arange(length, device=device)[None])
        for layer in backbone.layers:
            value = checkpoint(ar_layer, layer, value, cosine, sine, use_reentrant=False) if gradient else ar_layer(layer, value, cosine, sine)
        hidden = backbone.norm(value[0])[prefix_length - 1:-1]
        target = ids[0, prefix_length:]
        total = 0.0
        for start in range(0, hidden.shape[0], chunk):
            logits = model.lm_head(hidden[start:start + chunk]).float()
            total = total + F.cross_entropy(logits, target[start:start + chunk], reduction="sum")
        return total / hidden.shape[0]

    @torch.no_grad()
    def evaluate() -> float:
        return sum(language_loss(*sequence(item), gradient=False).item() for item in data[:6]) / min(6, len(data))

    def save(path: Path) -> None:
        torch.save(
            {"lora": [parameter.detach().cpu() for parameter in lora], "rank": rank, "targets": "ar self_attn qkvo + mlp gate/up/down", "cursor_head": cursor_head.state_dict()},
            path,
        )
        print(f"CHECKPOINT {path.name}", flush=True)

    initial = evaluate()
    print(f"EVAL step 0 minted_val 0.000 artist {initial:.3f}", flush=True)
    started = time.time()
    best = initial
    for step in range(1, steps + 1):
        for group in optimizer.param_groups:
            group["lr"] = learning_rate * min(1, step / 50) * (0.2 + 0.8 * 0.5 * (1 + math.cos(math.pi * min(step, schedule_steps) / schedule_steps)))
        last_loss = None
        for _ in range(accumulation):
            item = data[np.random.randint(len(data))]
            ids, prefix_length = sequence(item)
            last_loss = language_loss(ids, prefix_length)
            (last_loss / accumulation).backward()
        torch.nn.utils.clip_grad_norm_(lora + list(cursor_head.parameters()), 1.0)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        print(f"step {step} loss {last_loss.item():.3f} cursor nan len {ids.shape[1]} {time.time() - started:.0f}s mem {torch.cuda.max_memory_allocated() / 2**30:.1f}G", flush=True)
        if step % 100 == 0 or step == steps:
            artist_loss = evaluate()
            print(f"EVAL step {step} minted_val 0.000 artist {artist_loss:.3f} {time.time() - started:.0f}s", flush=True)
            if artist_loss < best:
                best = artist_loss
                save(output / "best.pt")
            save(output / "last.pt")
        if step % checkpoint_every == 0 or step == steps:
            save(output / f"step-{step}.pt")
    print(f"RESULT {manifest['run_id']}: best artist CE {best:.3f}", flush=True)


def update_manifest(path: Path, **changes) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    value.update(changes)
    value["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    os.environ.setdefault("HF_HOME", str(Path(manifest["paths"]["run_dir"]) / "hf-cache"))
    try:
        update_manifest(manifest_path, status="staging", stage="staging")
        source = stage(manifest)
        update_manifest(manifest_path, status="preparing", stage="preparing")
        prepare_features(manifest, source)
        dataset_path = build_dataset(manifest, source)
        update_manifest(manifest_path, status="training", stage="training")
        train(manifest, dataset_path)
        update_manifest(manifest_path, status="completed", stage="completed")
        print("STAGE completed", flush=True)
        return 0
    except BaseException as exc:
        update_manifest(manifest_path, status="failed", stage="failed", error=str(exc))
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
