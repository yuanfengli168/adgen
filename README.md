# AdGen 🎬

> One-line ad generator: text prompt → posters + promo video, using local AI models.

## What It Does

```bash
adgen "5 US dollar to keep your phone number for three months" --quality high
```

Automatically generates:
1. **3 ad copy variations** (via Ollama / local LLM)
2. **3 poster images** (via SDXL — Flux workflow planned)
3. **Product fusion** (via IP-Adapter — blend your logo/product into posters; optional)
4. **3 video clips** (via AnimateDiff in fast mode, or **Wan2.1 image-to-video** in high mode)
5. **Stitched final video with text overlay** (via FFmpeg)
6. Everything saved to `output/`

## Requirements

- Mac with Apple Silicon (M1+), 32GB+ RAM recommended (64GB ideal)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running locally
- [Ollama](https://ollama.ai) with a model installed (e.g. `qwen3:32b`)
- [FFmpeg](https://ffmpeg.org) with the `drawtext` filter (for text overlay)

> **macOS Homebrew users:** the default `ffmpeg` formula does **not** ship
> `drawtext` (libfreetype/fontconfig excluded by default). Install the
> `ffmpeg-full` variant and put it first on your PATH:
> ```bash
> brew install ffmpeg-full
> export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"
> ```
> `adgen setup` will warn you if drawtext is missing.

## Models Used

| Step | Model | Size | Purpose |
|------|-------|------|---------|
| Copywriting | Qwen3 32B (Q4) | ~20GB | Generate ad text + image/video prompts |
| Poster Gen | SDXL (Flux workflow TODO) | ~6.5GB | Poster images |
| Product fusion | IP-Adapter SDXL | ~1GB | Blend product/logo into scenes |
| Video (fast) | AnimateDiff + SDXL | ~4GB | 5 s clips, 8 fps |
| Video (high) | **Wan2.1 14B I2V** (480p, GGUF Q4) | ~10.5GB | 5 s clips, 16 fps — animates the actual poster |

## Architecture

```
┌─────────────────────────────────────────┐
│  CLI / Web UI                            │
│  adge                                   │
│  adgen "your product description"       │
│            --quality fast|high          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Pipeline (5 steps)                     │
│  1. Copy Gen (Ollama)                   │
│  2. Image Gen (ComfyUI - SDXL)          │
│  3. Product Fusion (ComfyUI - IP-Ad)    │
│  4. Video Gen (ComfyUI - AnimateDiff    │
│                or Wan2.1 I2V)           │
│  5. Post-process (FFmpeg stitch+text)   │
└──────┬──────────┬──────────┬───────────┘
       │          │          │
┌──────▼──┐ ┌────▼─────┐ ┌──▼──────────┐
│ Ollama  │ │ ComfyUI  │ │ ComfyUI     │
│ (LLM)   │ │ (SDXL)   │ │ (AnimateDiff│
│         │ │          │ │  /Wan2.1)  │
└─────────┘ └──────────┘ └─────────────┘
```

## Status

🚧 **MVP / early development** — End-to-end pipeline working. Wan2.1 I2V added for high quality mode. See `docs/issues.md` for known issues.

## Quality Modes

| Flag | Poster model | Video model | Speed (1 clip) | Quality |
|---|---|---|---|---|
| `--quality fast` (default) | SDXL | AnimateDiff @ 8 fps | ~1–2 min | Decent |
| `--quality high` | SDXL | **Wan2.1 14B I2V** @ 16 fps | ~5–10 min (M-series Max) | Much better, video matches poster |

Wan2.1 I2V (image-to-video) takes the **generated poster as the first frame** and animates from it — so the final video visually matches the poster instead of being a separate generation. Falls back to AnimateDiff if the Wan2.1 model isn't installed in ComfyUI.

On Apple Silicon, use the GGUF workflow/model path for Wan2.1 high mode.

You can drop the workflow files (`adgen/workflows/wan_i2v_video.json`, `animatediff_video.json`, `sdxl_poster.json`, `sdxl_ipadapter.json`) directly into the ComfyUI browser UI at `http://localhost:8188` to iterate on them manually.

## Quick Start

```bash
# From source (package is not on PyPI yet)
git clone https://github.com/yuanfengli168/adgen.git
cd adgen
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Make sure ComfyUI and Ollama are running
adgen setup
adgen "Your product tagline here"
adgen "Your product tagline here" --quality high --brand brand.json
```

## Research

See [`docs/research.md`](docs/research.md) for:
- Analysis of existing tools (Creatify, Arcads, Pencil AI, etc.)
- What they do well vs. poorly
- How AdGen improves on them
- Model selection rationale

## License

MIT