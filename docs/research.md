# AdGen Research — Deep Dive

## Goal

Build an open-source, locally-running tool that takes a text prompt and outputs:
- 3 ad copy variations
- 3 poster images (with product/logo fusion)
- ~15s promo video

All running on MacBook Pro M1 Max 64GB, no cloud needed.

---

## 1. ComfyUI API — How to Programmatically Control ComfyUI

### API Overview
ComfyUI runs a local HTTP server (default `localhost:8188`) with a REST API:
- `POST /prompt` — Submit a workflow (JSON format) for execution
- `GET /history/{prompt_id}` — Check execution status and get outputs
- `GET /view` — Retrieve generated images
- WebSocket at `ws://localhost:8188/ws` — Real-time progress updates

### Workflow JSON Format
ComfyUI workflows are node graphs serialized as JSON. Each node has:
- `class_type` — The node type (e.g., "KSampler", "CLIPTextEncode")
- `inputs` — Connected node IDs or direct values
- `widgets` — UI-only values (need to be merged into inputs for API use)

**Key insight:** When you save a workflow in ComfyUI UI, you get UI-format JSON. For API use, you need to use "Save (API Format)" which produces the correct structure.

### comfy-cli
Official CLI tool from Comfy-Org:
- `comfy install` — Install ComfyUI
- `comfy run <workflow.json>` — Run a workflow from CLI
- `comfy model download` — Download models from HF/CivitAI
- Cross-platform (macOS, Linux, Windows)
- Can manage custom nodes

**This is huge for AdGen:** Instead of building our own ComfyUI API client from scratch, we can use `comfy-cli` as the runtime layer. AdGen just needs to generate workflow JSONs and call `comfy run`.

### ComfyUI-Manager
Extension for managing custom nodes:
- Install/remove/disable/enable custom nodes
- Model management
- Now officially maintained by Comfy-Org

**For AdGen:** We need these custom nodes:
1. `ComfyUI_IPAdapter_plus` — IP-Adapter support
2. `ComfyUI-AnimateDiff-Evolved` — AnimateDiff support
3. `ComfyUI-VideoHelperSuite` — Video encoding from frames

---

## 2. Flux 1.dev — Image Generation

### Model Variants
| Variant | Size | Steps | Quality | Speed on M1 Max |
|---------|------|-------|---------|-----------------|
| Flux 1.dev | ~24GB (full) | 28-50 | Best | ~30-60s/image |
| Flux 1.dev FP8 | ~12GB | 28-50 | Slight degradation | ~15-25s/image |
| Flux 1.schnell | ~12GB | 4 | Good (fast) | ~3-5s/image |

### ComfyUI Setup for Flux
Required files:
- `flux1-dev-fp8.safetensors` → `models/checkpoints/` (12GB)
- `t5xxl_fp16.safetensors` → `models/text_encoders/` (9.5GB, recommended for 64GB)
  - Or `t5xxl_fp8_e4m3fn_scaled.safetensors` for lower memory
- `clip_l.safetensors` → `models/text_encoders/`
- `ae.safetensors` (VAE) → `models/vae/`

Total disk: ~25GB for FP8 setup

### Flux + IP-Adapter Compatibility
**Confirmed:** InstantX released [FLUX.1-dev-IP-Adapter](https://huggingface.co/InstantX/FLUX.1-dev-IP-Adapter)
- Uses `google/siglip-so400m-patch14-384` as image encoder (not CLIP)
- Added into 38 single + 19 double transformer blocks
- Works with Flux 1.dev
- **But:** NOT yet integrated into ComfyUI_IPAdapter_plus (which is in maintenance mode)
- Need custom ComfyUI node or diffusers-based approach

**Decision:** For product fusion, we have two paths:
1. **Path A (easier):** Use SDXL + IP-Adapter (well-tested, ComfyUI support)
2. **Path B (higher quality):** Use Flux + InstantX IP-Adapter (needs custom node or direct diffusers call)

**Recommendation:** Start with Path A (SDXL + IP-Adapter) for MVP, add Flux IP-Adapter later.

### Flux Kontext (Image Editing)
New Flux model for image editing — could be useful for:
- Adapting generated posters (change text, colors, layout)
- Inpainting product images into scenes
- Worth investigating for v2

---

## 3. SDXL + IP-Adapter — Product Fusion

### SDXL in ComfyUI
- Native support, no extra setup
- `sdxl_base_1.0.safetensors` → `models/checkpoints/` (6.5GB)
- Faster than Flux, larger LoRA ecosystem

### IP-Adapter for SDXL
Available models (in `models/ipadapter/`):
- `ip-adapter_sdxl.safetensors` — Standard, good for style transfer
- `ip-adapter-plus_sdxl.safetensors` — Stronger, better for subject preservation
- `ip-adapter-plus-face_sdxl.safetensors` — Face-specific

Required:
- `CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors` → `models/clip_vision/` (3.5GB)

### How IP-Adapter Works for AdGen
1. Load product image (logo, product photo)
2. Load SDXL checkpoint
3. IP-Adapter encodes product image as conditioning
4. Generate new image that incorporates the product
5. Weight parameter (0.0-1.0) controls how strongly product influences output

**Perfect for:** "Put my product/logo into a stylish ad scene"

### ComfyUI_IPAdapter_plus Status
⚠️ **Maintenance mode** (April 2025) — author no longer actively developing
- Still works, but may lag behind ComfyUI updates
- Alternative: use diffusers directly for IP-Adapter

---

## 4. Video Generation — AnimateDiff vs Wan2.1

### AnimateDiff Evolved (ComfyUI)
- Animates SDXL images using motion modules
- Requires: `ComfyUI-AnimateDiff-Evolved` + `ComfyUI-VideoHelperSuite`
- Motion models: `mm_sdxl_v10_beta.ckpt` or similar
- Typically generates 16-32 frames at 512x512
- ~2-5 min per 3-5s clip on M1 Max

**Pros:**
- Consistent with SDXL pipeline (same model)
- Good for subtle motion (pan, zoom, floating)
- Well-integrated with ControlNet for guided motion

**Cons:**
- Short clips (3-5s reliable, longer gets inconsistent)
- Lower resolution
- Motion can be subtle/gentle — not dramatic

### Wan 2.1 (ComfyUI Native)
Native ComfyUI support since Feb 2025.

Model variants:
| Variant | Size | Quality | M1 Max Speed |
|---------|------|---------|-------------|
| T2V 1.3B | ~2.5GB | Decent | ~3-5 min/5s clip |
| T2V 14B | ~28GB | Excellent | ~15-30 min/5s clip (fp8) |
| I2V 14B 480p | ~28GB | Excellent | ~15-30 min/5s clip |

Required files:
- `umt5_xxl_fp8_e4m3fn_scaled.safetensors` → `models/text_encoders/`
- `wan_2.1_vae.safetensors` → `models/vae/`
- Diffusion model → `models/diffusion_models/`
- For I2V: `clip_vision_h.safetensors` → `models/clip_vision/`

**Key feature:** Image-to-Video (I2V) — can take a poster image and animate it!
- Perfect for AdGen pipeline: poster → video
- 14B I2V is the highest quality path

### Wan 2.2
Also now available with ComfyUI examples. Newer, likely better quality. Not yet fully benchmarked.

### Video Strategy for AdGen

**Option A: AnimateDiff (fast path)**
```
SDXL poster → AnimateDiff → 3× 5s clips → FFmpeg stitch → 15s
```
- Pros: Faster, consistent style, lower VRAM
- Cons: Lower quality, subtle motion only

**Option B: Wan2.1 I2V (quality path)**
```
SDXL poster → Wan2.1 I2V 14B → 3× 5s clips → FFmpeg stitch → 15s
```
- Pros: Higher quality, more dramatic motion, text-in-video
- Cons: Much slower (45-90min for full 15s), needs fp8 model

**Option C: Wan2.1 T2V 1.3B (budget path)**
```
Text prompt → Wan2.1 T2V 1.3B → 3× 5s clips → FFmpeg stitch → 15s
```
- Pros: Lightest model, decent quality
- Cons: No poster-to-video consistency, lowest quality

**Recommendation:**
- MVP: Option A (AnimateDiff) — fast iteration
- Quality mode: Option B (Wan2.1 I2V) — best results
- Let user choose with `--quality fast|high`

---

## 5. LLM Integration — Copywriting

### Ollama API
- `POST http://localhost:11434/api/generate` — Generate text
- `POST http://localhost:11434/api/chat` — Chat format
- Simple HTTP, no SDK needed

### Model Selection
| Model | Size (Q4) | Quality | M1 Max Speed |
|-------|-----------|---------|-------------|
| Qwen3 32B | ~20GB | Best for multilingual/copy | ~15-20 tok/s |
| Llama 4 Scout 17B | ~10GB | Good, fast | ~30-40 tok/s |
| Gemma 3 27B | ~17GB | Good, multimodal | ~20-25 tok/s |
| DeepSeek R1 distill 32B | ~20GB | Strong reasoning | ~15-20 tok/s |

**Recommendation:** Qwen3 32B for best multilingual copy (SG/Asia market), Llama 4 Scout as fast fallback.

### Prompt Engineering for Ad Copy
AdGen needs the LLM to generate:
1. 3 short ad taglines (5-10 words each)
2. 3 image generation prompts (detailed, for Flux/SDXL)
3. 3 video motion prompts (short, for AnimateDiff/Wan)
4. Brand color/style suggestions

All from a single product description input.

---

## 6. Post-Processing — FFmpeg

### Text Overlay
```bash
ffmpeg -i video.mp4 \
  -vf "drawtext=text='Top Up Lah':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-th-30" \
  -codec:a copy output.mp4
```

### Stitch Clips
```bash
ffmpeg -f concat -safe 0 -i clips.txt -c copy output.mp4
```

### Add Background Music
```bash
ffmpeg -i video.mp4 -i music.mp3 -c:v copy -c:a aac -shortest output.mp4
```

**For AdGen:** FFmpeg handles all post-processing — text overlay, stitching, format conversion. No AI needed here.

---

## 7. Complete AdGen Pipeline (Updated Design)

```
Input: "Product description" [--brand brand.json] [--quality fast|high]
  │
  ├─ Step 1: LLM (Ollama)
  │   Generate: 3 taglines + 3 image prompts + 3 video prompts
  │
  ├─ Step 2: Poster Generation (ComfyUI)
  │   ├── fast:  SDXL + prompt → 3 posters
  │   └── high:  Flux 1.dev FP8 + prompt → 3 posters
  │
  ├─ Step 3: Product Fusion (ComfyUI + IP-Adapter)
  │   ├── fast:  SDXL + IP-Adapter → product in scene
  │   └── high:  SDXL + IP-Adapter → product in scene (same for now)
  │   Note: Flux IP-Adapter not yet in ComfyUI, use SDXL path
  │
  ├─ Step 4: Video Generation (ComfyUI)
  │   ├── fast:  AnimateDiff + SDXL → 3× 5s clips
  │   └── high:  Wan2.1 I2V 14B (fp8) → 3× 5s clips
  │
  └─ Step 5: Post-Processing (FFmpeg)
      - Stitch 3 clips → 15s
      - Add text overlay (tagline + brand name)
      - Add brand color border/watermark
      - Export: 3 PNGs + 1 MP4
      → output/
```

---

## 8. Disk Space & Model Requirements

### Minimum Setup (fast mode: SDXL + AnimateDiff)
| Model | Size | Location |
|-------|------|----------|
| SDXL Base 1.0 | 6.5GB | checkpoints/ |
| IP-Adapter SDXL Plus | 700MB | ipadapter/ |
| CLIP Vision BigG | 3.5GB | clip_vision/ |
| AnimateDiff SDXL | 1.5GB | animatediff_models/ |
| Qwen3 32B Q4 | 20GB | Ollama |
| **Total** | **~32GB** | |

### Full Setup (high mode: + Flux + Wan2.1)
| Model | Size | Location |
|-------|------|----------|
| Flux 1.dev FP8 | 12GB | checkpoints/ |
| T5-XXL FP8 | 5GB | text_encoders/ |
| CLIP-L | 250MB | text_encoders/ |
| Flux VAE | 300MB | vae/ |
| Wan2.1 I2V 14B FP8 | 15GB | diffusion_models/ |
| UMT5-XXL FP8 | 5GB | text_encoders/ |
| Wan VAE | 300MB | vae/ |
| CLIP Vision H | 2GB | clip_vision/ |
| **Additional** | **~40GB** | |
| **Grand Total** | **~72GB** | |

M1 Max 64GB RAM can run this but will need model swapping. FP8 models are essential.

---

## 9. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| ComfyUI interface | comfy-cli + direct API | Best of both worlds |
| Image gen default | SDXL | Faster, IP-Adapter support mature |
| Image gen quality | Flux 1.dev FP8 | Better quality when patient |
| Product fusion | SDXL + IP-Adapter Plus | Only mature option currently |
| Video gen fast | AnimateDiff + SDXL | Quick iteration |
| Video gen quality | Wan2.1 I2V 14B FP8 | Best quality, poster→video |
| Copywriting | Ollama + Qwen3 32B | Multilingual, strong copy |
| Text overlay | FFmpeg | Simple, reliable, no AI |
| Brand kit | JSON config file | Portable, simple |

---

## 10. Open Questions & Risks

1. **Flux IP-Adapter in ComfyUI** — InstantX released weights but ComfyUI_IPAdapter_plus is in maintenance mode. May need custom node or direct diffusers call.

2. **Wan2.1 I2V on M1 Max** — 14B FP8 needs ~28GB VRAM. Apple Silicon shares RAM so 64GB should work, but speed is unknown. Need real benchmarks.

3. **AnimateDiff quality** — May not be dramatic enough for "promo video" feel. Need to test with motion ControlNet.

4. **ComfyUI API stability** — API format changes between versions. Should pin ComfyUI version in docs.

5. **Model download automation** — First-time setup needs ~32-72GB of models. Should provide `adgen setup` command that downloads everything.

6. **Text rendering in video** — Wan2.1 can generate text in video (Chinese + English). Could we use this instead of FFmpeg overlay for more natural-looking ad copy?

---

## Next Steps

1. ✅ Research complete
2. Build CLI scaffold with pipeline orchestrator
3. Implement Ollama integration (Step 1)
4. Create SDXL + IP-Adapter workflow JSON templates
5. Create AnimateDiff workflow JSON template
6. Implement ComfyUI API client (or comfy-cli wrapper)
7. Implement FFmpeg post-processing
8. End-to-end test
9. Add Flux + Wan2.1 support (quality mode)
10. Add brand kit support