# AdGen Research — Existing Tool Analysis

## Goal

Build an open-source, locally-running tool that takes a text prompt and outputs:
- 3 ad copy variations
- 3 poster images (with product/logo fusion)
- ~15s promo video

All running on MacBook Pro M1 Max 64GB, no cloud needed.

---

## Existing Tools Analysis

### 1. Creatify (creatify.ai)
**What it does:** Input product URL → auto-generate video ads with AI voiceover, subtitles, b-roll.

**Strengths:**
- Dead simple UX — paste URL, get video
- Auto-fetches product info from website
- Built-in AI voiceover (multiple languages)
- Multiple format exports (16:9, 9:16, 1:1)
- A/B testing built in

**Weaknesses:**
- Cloud-only, SaaS pricing
- Generic/templated output — many ads look the same
- No local execution
- Limited style control
- Can't blend custom product images easily

**What AdGen should adopt:**
- "One input → full output" simplicity
- Multiple format support
- A/B variant generation (3 versions by default)

**What AdGen should improve:**
- Full local execution (privacy, no subscription)
- Custom style control (not locked to templates)
- Product image fusion (IP-Adapter) — Creatify doesn't do this well

---

### 2. Arcads (arcads.ai)
**What it does:** AI virtual actors deliver UGC-style ad scripts on camera.

**Strengths:**
- Very realistic AI avatars
- UGC format works well on TikTok/Reels
- Script-to-video pipeline
- Multiple avatar/ethnicity options

**Weaknesses:**
- Cloud-only, expensive
- Avatar uncanny valley at close inspection
- Limited to "talking head" format
- No poster/image generation

**What AdGen should adopt:**
- UGC vertical format (9:16) as default video output
- Script-first approach (copy → video)

**What AdGen should improve:**
- Don't need avatars — can do motion graphics / animated posters instead
- Poster + video combo (Arcads only does video)

---

### 3. Pencil AI (pencil.ai)
**What it does:** Generate + test multiple ad variants, optimize for performance.

**Strengths:**
- Multi-variant generation (dozens of versions)
- Built-in A/B testing with real metrics
- Brand kit integration (fonts, colors, logo)
- Iterative improvement based on performance data

**Weaknesses:**
- Enterprise pricing
- Requires ad platform integration (Meta, Google)
- Generation quality is decent but not stunning
- Not open source

**What AdGen should adopt:**
- Brand kit support (logo, colors, fonts)
- Multi-variant generation
- Brand consistency across outputs

**What AdGen should improve:**
- Open source
- Local execution
- Higher quality base images (Flux > their gen)

---

### 4. AdCreative.ai
**What it does:** Batch generate ad creatives with data-driven design suggestions.

**Strengths:**
- Very fast batch generation
- CTR prediction scoring
- Integration with ad platforms
- Template library

**Weaknesses:**
- Template-based = repetitive
- Low creative ceiling
- Cloud-only
- More "design automation" than "creative AI"

**What AdGen should adopt:**
- Speed (batch generation)
- Score/rank outputs

**What AdGen should improve:**
- Not template-based — use generative AI
- More creative freedom
- Quality over quantity

---

### 5. ComfyUI Ecosystem (open source)
**What it does:** Node-based workflow builder for Stable Diffusion and friends.

**Strengths:**
- Most flexible image gen tool
- Huge model ecosystem (SDXL, Flux, IP-Adapter, ControlNet, AnimateDiff)
- Local execution
- Community workflows shared online
- API access (can script it)

**Weaknesses:**
- Steep learning curve
- No "one button" experience
- Video gen workflows are complex to set up
- No LLM integration for copywriting
- No brand kit management

**What AdGen should adopt:**
- ComfyUI as backend engine
- API-based workflow execution
- Model flexibility

**What AdGen should improve:**
- Wrap ComfyUI complexity behind simple CLI
- Auto-select best models for each step
- Add LLM copywriting layer
- Add brand kit + product fusion

---

### 6. AnimateDiff Ecosystem
**What it does:** Animate Stable Diffusion images using motion modules.

**Strengths:**
- Good quality short animations
- Works with existing SDXL checkpoints
- ControlNet support for guided motion
- Can do 3-5 second clips reliably

**Weaknesses:**
- 15s is at the edge of what it does well
- Motion can be inconsistent
- Need careful prompt engineering
- Slow on consumer hardware

**What AdGen should consider:**
- Use AnimateDiff for 3× 5s clips → stitch together for 15s
- Or use Wan2.1 for end-to-end video gen (higher quality but slower)

---

### 7. Wan2.1 (open source, by Alibaba)
**What it does:** Text/image-to-video generation, open weights.

**Strengths:**
- Higher quality than AnimateDiff for video
- Better temporal consistency
- Open weights, local execution
- 8B version fits in 64GB RAM

**Weaknesses:**
- Very slow on M1 (minutes per 3s clip)
- 15s would need 5× 3s clips stitched
- Higher VRAM usage
- Less community tooling than SD-based approaches

**What AdGen should consider:**
- Offer both paths: AnimateDiff (faster, lower quality) and Wan2.1 (slower, higher quality)
- Let user choose via `--quality fast|high`

---

## Model Selection for AdGen

| Pipeline Step | Primary Model | Alternative | Rationale |
|---------------|--------------|-------------|-----------|
| Copywriting | Qwen3 32B (Q4) | Llama 4 Scout 17B | Qwen3 multilingual (good for SG/Asia market) |
| Poster image | Flux 1.dev | SDXL | Flux quality > SDXL, but SDXL faster + more LoRAs |
| Product fusion | IP-Adapter SDXL | — | Only real option for zero-shot product insertion |
| Video | AnimateDiff + SDXL | Wan2.1 8B | AnimateDiff faster; Wan2.1 for --quality high |
| Upscale | RealESRGAN | — | Optional, for final output polish |

---

## AdGen Pipeline Design

```
Input: "Product description text"
  │
  ├─ Step 1: LLM generates
  │   - 3 ad copy variations
  │   - 3 image generation prompts (per copy)
  │   - 3 video motion prompts (per copy)
  │
  ├─ Step 2: ComfyUI generates posters
  │   - Flux 1.dev (or SDXL) renders each prompt
  │   - IP-Adapter fuses product image/logo
  │   → 3 poster images
  │
  ├─ Step 3: ComfyUI generates video
  │   - AnimateDiff animates each poster (5s each)
  │   - Or Wan2.1 generates from prompt + poster as reference
  │   → 3 video clips
  │
  └─ Step 4: Post-processing
      - Stitch 3 clips → 15s video
      - Add text overlay (ad copy) via FFmpeg
      - Export: poster PNGs + video MP4
      → output/
```

---

## Open Questions

1. **IP-Adapter + Flux compatibility** — IP-Adapter was built for SD/SDXL. Need to verify it works with Flux or if we need SDXL path for product fusion.

2. **AnimateDiff + SDXL vs Wan2.1** — Quality vs speed tradeoff. Need benchmarks on M1 Max.

3. **Text overlay** — Should we render text via ComfyUI (ControlNet) or overlay via FFmpeg? FFmpeg is simpler and more reliable for ad copy.

4. **Brand kit format** — How to specify: logo PNG, brand colors, fonts. JSON config file?

5. **ComfyUI API stability** — ComfyUI's API is unofficial. May need to pin a specific version or use [comfy-cli](https://github.com/Comfy-Org/comfy-cli).

---

## Next Steps

1. Prototype ComfyUI API calls from Python
2. Test Flux + IP-Adapter pipeline on M1 Max
3. Test AnimateDiff + SDXL pipeline on M1 Max
4. Build CLI scaffold with pipeline orchestration
5. Add brand kit support
6. Add web UI (optional, v2)