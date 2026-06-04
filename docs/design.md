# AdGen — AI Ad Generator

## Overview

One-line ad generator: text → posters + promo video using local AI models.

## Pipeline (5 steps)

1. **Copywriting** — Ollama (Qwen3 32B) generates ad text + image/video prompts
2. **Poster Gen** — ComfyUI (SDXL) renders poster images
3. **Product Fusion** — ComfyUI (IP-Adapter SDXL) blends product/logo into posters (optional — requires `--brand` with `product_images`)
4. **Video Gen** — ComfyUI (AnimateDiff for fast mode, Wan2.1 14B I2V for high mode)
5. **Post-processing** — FFmpeg stitches clips + adds text overlay

## Requirements

- Apple Silicon Mac, 32GB+ RAM (64GB recommended for Wan2.1)
- ComfyUI running on `localhost:8188`
- Ollama running on `localhost:11434`
- Python 3.10+
- FFmpeg with `drawtext` filter (see README — Homebrew users need `ffmpeg-full`)

## Usage

```bash
# Basic
adgen "Your product tagline"

# With brand kit
adgen "Your product tagline" --brand brand.json

# Quality options
adgen "Your product tagline" --quality fast   # SDXL + AnimateDiff (~1-2 min/clip)
adgen "Your product tagline" --quality high   # SDXL + Wan2.1 I2V (~5-10 min/clip)
```

`--quality high` requires Wan2.1 14B weights (~16 GB) installed in ComfyUI. If missing, falls back to AnimateDiff with a warning.

## Brand Kit Format

```json
{
  "name": "Top Up Lah",
  "logo": "assets/logo.png",
  "colors": ["#FF6B35", "#E85D2C"],
  "fonts": ["system-ui"],
  "product_images": ["assets/product1.png"]
}
```

## Project Structure

```
adgen/                          # this repo (git root)
├── adgen/                      # Python package
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── pipeline.py             # Pipeline orchestrator
│   ├── llm.py                  # Ollama integration
│   ├── comfyui.py              # ComfyUI API client
│   ├── postprocess.py          # FFmpeg overlay + stitching
│   ├── brand.py                # Brand kit loader
│   └── workflows/              # ComfyUI workflow JSONs (ship with pip install)
│       ├── sdxl_poster.json
│       ├── sdxl_ipadapter.json
│       ├── animatediff_video.json
│       └── wan_i2v_video.json
├── tests/
│   ├── test_pipeline.py
│   └── test_fixes.py
├── docs/
│   ├── design.md               # this file
│   ├── research.md
│   └── issues.md
├── output/                     # gitignored — generated files
├── pyproject.toml
└── README.md
```

## Implementation Status

### Phase 1: MVP — ✅ done
- [x] CLI scaffold + pipeline orchestrator
- [x] Ollama copywriting integration
- [x] ComfyUI API client (poster gen with SDXL)
- [x] FFmpeg text overlay + stitching
- [x] End-to-end test with SDXL + AnimateDiff

### Phase 2: Quality — ✅ mostly done
- [x] IP-Adapter product fusion
- [x] Wan2.1 video gen option (`--quality high`)
- [x] Brand kit support
- [ ] Flux 1.dev poster workflow (currently SDXL only)

### Phase 3: Polish — ⬜ open
- [ ] Web UI
- [ ] RealESRGAN upscaling
- [ ] Multi-format export (16:9, 9:16, 1:1)
- [ ] A/B variant scoring
- [ ] Better IP-Adapter workflow (img2img-style, real poster → latent conditioning)
- [ ] PyPI publication

See [issues.md](issues.md) for the full list of known issues and fixes applied.
