# AdGen 🎬

> One-line ad generator: text prompt → posters + promo video, using local AI models.

## What It Does

```bash
adgen "Top Up Lah - Singapore restaurant stored-value card tracker, never forget your balances"
```

Automatically generates:
1. **3 ad copy variations** (via Ollama / local LLM)
2. **3 poster images** (via Flux 1.dev / SDXL)
3. **Product fusion** (via IP-Adapter — blend your logo/product into posters)
4. **15s promo video** (via AnimateDiff / Wan2.1 — animate posters into video)
5. Everything saved to `output/`

## Requirements

- Mac with Apple Silicon (M1+), 32GB+ RAM recommended (64GB ideal)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running locally
- [Ollama](https://ollama.ai) with a model installed (e.g. `qwen3:32b`)

## Models Used

| Step | Model | Size | Purpose |
|------|-------|------|---------|
| Copywriting | Qwen3 32B (Q4) | ~20GB | Generate ad text + image prompts |
| Poster Gen | Flux 1.dev | ~12GB | High-quality poster images |
| Poster gen (alt) | SDXL | ~6.5GB | Faster generation, larger ecosystem |
| Product fusion | IP-Adapter SDXL | ~1GB | Blend product/logo into scenes |
| Video | AnimateDiff + SDXL | ~4GB | Animate still images |
| Video (alt) | Wan2.1 8B | ~16GB | Higher quality video |

## Architecture

```
┌─────────────────────────────────────────┐
│  CLI / Web UI                            │
│  adgen "your product description"        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Pipeline Orchestrator                  │
│  1. Copy Gen → 2. Image Gen →          │
│  3. Product Fusion → 4. Video Gen      │
└──────┬──────────┬──────────┬───────────┘
       │          │          │
┌──────▼──┐ ┌────▼─────┐ ┌──▼──────────┐
│ Ollama  │ │ ComfyUI  │ │ ComfyUI     │
│ (LLM)   │ │ (Flux/   │ │ (AnimateDiff│
│         │ │  SDXL)   │ │  /Wan2.1)  │
└─────────┘ └──────────┘ └─────────────┘
```

## Status

🚧 **Early development** — Research phase. See `docs/research.md` for tool analysis.

## Quick Start (when ready)

```bash
# Install
pip install adgen

# Or from source
git clone https://github.com/yuanfengli168/adgen.git
cd adgen
pip install -e .

# Make sure ComfyUI and Ollama are running
adgen "Your product tagline here"
```

## Research

See [`docs/research.md`](docs/research.md) for:
- Analysis of existing tools (Creatify, Arcads, Pencil AI, etc.)
- What they do well vs. poorly
- How AdGen improves on them
- Model selection rationale

## License

MIT