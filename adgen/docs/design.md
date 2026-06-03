# AdGen — AI Ad Generator

## Overview

One-line ad generator: text → posters + promo video using local AI models.

## Pipeline

1. **Copywriting** — Ollama (Qwen3 32B) generates ad text + image/video prompts
2. **Poster Gen** — ComfyUI (Flux 1.dev / SDXL) renders poster images
3. **Product Fusion** — IP-Adapter blends product/logo into posters
4. **Video Gen** — AnimateDiff / Wan2.1 animates posters into video
5. **Post-processing** — FFmpeg adds text overlay, stitches clips

## Requirements

- Apple Silicon Mac, 32GB+ RAM (64GB recommended)
- ComfyUI running on localhost:8188
- Ollama running on localhost:11434
- Python 3.10+

## Usage

```bash
# Basic
adgen "Your product tagline"

# With brand kit
adgen "Your product tagline" --brand brand.json

# Quality options
adgen "Your product tagline" --quality fast   # SDXL + AnimateDiff
adgen "Your product tagline" --quality high   # Flux + Wan2.1
```

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
adgen/
├── adgen/              # Python package
│   ├── cli.py          # CLI entry point
│   ├── pipeline.py     # Pipeline orchestrator
│   ├── llm.py          # Ollama integration
│   ├── comfyui.py      # ComfyUI API client
│   ├── postprocess.py  # FFmpeg overlay + stitching
│   └── brand.py        # Brand kit loader
├── workflows/          # ComfyUI workflow JSONs
│   ├── poster_flux.json
│   ├── poster_sdxl.json
│   ├── ipadapter.json
│   ├── video_anidiff.json
│   └── video_wan.json
├── output/             # Generated files
├── docs/
│   └── research.md
└── tests/
```

## Implementation Phases

### Phase 1: MVP
- [ ] CLI scaffold + pipeline orchestrator
- [ ] Ollama copywriting integration
- [ ] ComfyUI API client (poster gen with SDXL)
- [ ] FFmpeg text overlay + stitching
- [ ] End-to-end test with SDXL + AnimateDiff

### Phase 2: Quality
- [ ] Flux 1.dev support
- [ ] IP-Adapter product fusion
- [ ] Wan2.1 video gen option
- [ ] Brand kit support

### Phase 3: Polish
- [ ] Web UI
- [ ] RealESRGAN upscaling
- [ ] Multi-format export (16:9, 9:16, 1:1)
- [ ] A/B variant scoring