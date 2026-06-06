# AdGen — Session Handoff (June 2026)

> Pickup guide for the next time we (or anyone) opens this repo. Read this before touching the code or running the pipeline.

## What's working end-to-end ✅

| Stage | Status | Notes |
|---|---|---|
| 1. LLM copy (Ollama + Qwen3 32B) | ✅ Works | Uses `format: "json"`, tolerant parser |
| 2. Posters (SDXL via ComfyUI) | ✅ Works | 3 posters, ~30 s each |
| 3. Product fusion (IP-Adapter) | ⚠️ Partial | Code uploads but workflow doesn't actually VAE-encode the poster |
| 4a. Video fast (AnimateDiff + SDXL) | ✅ Works | ~1–2 min/clip, 8 fps, 512×512 |
| 4b. Video high (Wan2.1 14B I2V) | ⚠️ In progress | GGUF workflow migration committed; full 3-clip E2E still to re-validate after restart |
| 5. Post-processing (stitch + drawtext) | ✅ Works | Needs `ffmpeg-full` for drawtext |
| Tests | ✅ 44 passing | `pytest -q` |
| Custom-node deps | ✅ Installed | `ComfyUI-GGUF` in `~/ComfyUI/custom_nodes/` |

## What was discovered this session (and fixed in commits)

1. **Repo hygiene** (commits in `1cba643`, `9a21902`):
   - Removed 11 stray files (AGENTS.md, SOUL.md, etc.) moved to `~/Documents/All Backups/adgen-backup/`
   - Flattened `adgen/adgen/adgen/` → `adgen/adgen/`
   - Deleted duplicate root `README.md`, root `docs/`, `setup.py`
2. **Critical pipeline bugs** (commit `9a21902`):
   - Positive prompt detection via `KSampler.inputs.positive` (was overwriting negative too)
   - Output filenames prefixed with `prompt_id` to avoid collisions
   - `wait_for_result` waits for `status.completed`, not just first partial output
   - `drawtext` special-char escaping (`\`, `:`, `'`, `%`)
   - `add_text_overlay` uses `-an` instead of `-codec:a copy` (silent inputs)
   - LLM JSON parser tolerates prose + uses `format=json` mode
   - `brand_context` only inserted when non-empty
   - LLM timeout 120s → 300s
   - `ComfyUIClient.upload_image()` helper added
   - Workflows moved into package + shipped via `package-data`
3. **Wan2.1 video mode** (commit `3081cff` — pulled from external branch):
   - Splits `_generate_videos` into `_generate_videos_animatediff` (fast) and `_generate_videos_wan` (high)
   - Adds quality booster prefix to AnimateDiff prompts
   - Uses Wan2.1 I2V with the poster as input frame
4. **ComfyUI `gifs` key fix** (commit `a076540`): pulls video outputs from `outputs[node]['gifs']` too (VHS_VideoCombine)
5. **ffmpeg drawtext detection** (commit `6ee6ae9`): `FFmpegWrapper.has_drawtext()` + warn-with-fix in `adgen setup` and pipeline
6. **Docs refresh** (commit `13f7c09`): README, design.md, issues.md all aligned with v0.2 / Wan2.1
7. **Wan GGUF migration + handoff refresh** (commit `0015331`):
  - `adgen/workflows/wan_i2v_video.json` moved to `UnetLoaderGGUF` + `WanImageToVideo`
  - `adgen/pipeline.py` high-quality Wan path aligned to new workflow expectations
  - `adgen/comfyui.py` supports upload target renaming for hardcoded workflow filenames
  - `docs/SESSION_HANDOFF.md` added for resumable continuation

## Wan2.1 I2V — what you need to know

This was the hardest part. Two gotchas:

### 1. The original `wan2.1_i2v_480p_14B_fp8_e4m3fn_scaled.safetensors` doesn't work on Apple Silicon
PyTorch's MPS backend doesn't support `Float8_e4m3fn` dtype. KSampler fails with:
```
Trying to convert Float8_e4m3fn to the MPS backend but it does not have support for that dtype.
```

### 2. The fix: use the GGUF-quantized model + `ComfyUI-GGUF` custom node
| | fp8 (broken) | GGUF Q4_K_M (works) |
|---|---|---|
| File | `wan2.1_i2v_480p_14B_fp8_e4m3fn_scaled.safetensors` | `wan2.1-i2v-14b-480p-Q4_K_M.gguf` |
| Size | 15.2 GB | 10.5 GB |
| Loader | `UNETLoader` (for fp8) | `UnetLoaderGGUF` (custom node) |
| Apple Silicon | ❌ | ✅ |
| Quality | best | ~slightly less (Q4 vs fp8) |

### Models currently installed in `~/ComfyUI/models/`
```
diffusion_models/Wan2.1/wan2.1-i2v-14b-480p-Q4_K_M.gguf   (10.5 GB, 14B I2V 480p)
text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors      (6.3 GB, Wan2.1 T5 encoder)
clip_vision/clip_vision_h.safetensors                    (1.2 GB, Wan2.1 CLIP-ViT)
vae/wan_2.1_vae.safetensors                              (242 MB, Wan2.1 VAE)
checkpoints/SDXL/sd_xl_base_1.0.safetensors              (6.5 GB, for posters)
ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors         (for product fusion)
clip_vision/CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors (for IP-Adapter)
animatediff_models/mm_sdxl_v10_beta.ckpt                 (AnimateDiff motion)
```

### Custom nodes installed
```
~/ComfyUI/custom_nodes/
├── ComfyUI-GGUF/              # UnetLoaderGGUF, CLIPLoaderGGUF, etc. — required for Wan2.1 on Mac
├── ComfyUI_IPAdapter_plus/    # IP-Adapter (product fusion)
├── ComfyUI-AnimateDiff-Evolved/  # AnimateDiff loader
├── ComfyUI-VideoHelperSuite/  # VHS_VideoCombine (mp4 output)
└── ComfyUI-Manager/           # GUI for managing custom nodes
```

### Python deps in `~/ComfyUI/venv`
```bash
~/ComfyUI/venv/bin/pip install gguf sentencepiece protobuf
```

## Pipeline run records (this session)

### Smoke test (single clip, 12 steps, 480×480, ~5s):
- **Time**: ~2 hours from cold start (model load + 12 sampling steps)
- **Result**: ✅ `wan_video_00001.mp4` (1.3 MB) successfully generated
- **Proof**: `output/wan_smoketest_00001.mp4` in the repo (the only Wan2.1 video produced this session)

### Full E2E run ("top up lah", 3 clips, 8 steps each, in progress at session end)
- 3 posters ✅ (from earlier `--quality fast` run that was already done)
- 3 Wan2.1 video clips — running in background when this doc was written
- See `output_run.log` and `output/` for the latest state

### Restart check (latest)
- `pytest -q` passes (**44 passed**).
- ComfyUI was not reachable on `http://localhost:8188` at restart-check time.
- `output_run.log` currently ends during poster generation, and `output/` is empty, so no completed high-mode artifact was verified in this restart window.

## Wan2.1 timing expectations

On a 64 GB M-series Max (M2/M3/M4), per the community:

| Steps | Resolution | Frames | Time per 5s clip |
|---|---|---|---|
| 8 | 480×480 | 81 | ~10–15 min |
| 12 | 480×480 | 81 | ~15–20 min |
| 20 | 480×480 | 81 | ~25–40 min |
| 20 | 720×720 | 81 | ~50–80 min (2-3× slower) |

For a full pipeline run (3 clips):
- 3 × (poster gen ~30s + Wan2.1 ~15min + upload + stitching) ≈ 45–60 min minimum
- Add 2-3 min for LLM + first model load

**Recommendation**: use `steps=8` for fast iteration, `steps=20` for final quality.

## Known issues that still need work

See [issues.md](issues.md) for the full list. Key open items:
1. **#2 IP-Adapter workflow redesign** — current `sdxl_ipadapter.json` doesn't actually VAE-encode the poster. Needs a workflow that uses the poster as the initial latent for img2img.
2. **#13 Publish to PyPI** — README now says "from source", still not on PyPI.
3. **#15 Multi-product rotation** — `_fuse_products` only uses `product_images[0]`.
4. **#16 Concat re-encode** — `-c copy` is fragile.

## Git state at pause point

- Latest branch: `master`
- Latest pushed commit: `0015331 fix(wan): switch high quality path to GGUF workflow and document handoff`
- Working tree at last check: clean

## Resume checklist (next session)

1. Start ComfyUI and ensure `http://localhost:8188` is reachable.
2. Run `adgen setup` and confirm all checks are green.
3. Run `adgen generate "top up lah" --quality high --output ./output`.
4. Verify expected artifacts in `output/clips/` and `output/videos/`.
5. If high-mode fails, check ComfyUI history for node/model mismatch and update `docs/issues.md` with exact error.

## Questions for the user to decide next time

1. Is the I2V video quality acceptable, or should we use a higher-fidelity model?
2. Should we go back and fix IP-Adapter (proper img2img) or accept its current limitation?
3. Should we drop fast mode entirely, or keep it for quick iteration?
4. Do we want a simple web UI on top of this, or stay CLI-only?
