# AdGen — Code Review / Issues to Fix

Audit of `adgen/` package against current source. Items are roughly ordered by severity.

> **Status legend:** ✅ Fixed · 🟡 Partially fixed · ⬜ Open

## 🔴 Critical (functional bugs)

### ✅ 1. Positive & negative prompts both get overwritten with the same text
Fixed in `_build_poster_params` and `_generate_videos` by walking `KSampler.inputs.positive` to find the real positive node. New helper `_find_positive_prompt_node` + tests.

### 🟡 2. IP-Adapter "fusion" never feeds the poster into the workflow
Partially fixed: added `ComfyUIClient.upload_image()` and now uploads both the product and the poster to ComfyUI's input dir before submitting. The current `sdxl_ipadapter.json` still doesn't conditioning-feed the poster into a VAEEncode latent — proper fix requires a redesigned workflow with img2img. TODO is documented in the code.

### ✅ 3. ComfyUI output filenames collide across runs
Fixed: `get_output_images` now saves as `<prompt_id>_<filename>`. Test covers it.

### ✅ 4. `drawtext` filter breaks on special characters
Fixed via `_escape_drawtext()` (escapes `\`, `:`, `'`, `%`). 6 unit tests added.

### ✅ 5. `add_text_overlay` fails when input has no audio
Fixed: dropped `-codec:a copy`, replaced with `-an` (AnimateDiff outputs are silent anyway).

**Companion improvement:** added `FFmpegWrapper.has_drawtext()` and pipeline now checks it before calling `add_text_overlay`. If the local ffmpeg doesn't bundle libfreetype (Homebrew's default `ffmpeg` does not), the pipeline emits a clear, actionable warning with the `brew install ffmpeg-full` fix and skips overlay gracefully. `adgen setup` also reports drawtext availability.

### ✅ 6. `wait_for_result` returns prematurely on partial output
Fixed: now waits for `status.completed is True` or `status_str == "success"`. Test covers partial-then-complete sequence.

### ✅ 7. Workflows folder not shipped with installed package
Fixed: moved `workflows/` → `adgen/workflows/`, updated `WORKFLOWS_DIR`, added `[tool.setuptools.package-data]` for `*.json`. Test asserts the dir lives under the package.

## 🟠 High (LLM / robustness)

### ✅ 8. LLM JSON parser fails on prose around the JSON
Fixed: now passes `format: "json"` to Ollama (forces JSON-only output), plus regex fallback that extracts `{...}` from surrounding prose.

### ✅ 9. Empty `brand_context` left a stray blank line
Fixed: brand context only inserted when non-empty.

### ✅ 10. No timeout for large local models
Default bumped from 120 s → 300 s.

## 🟡 Medium (packaging / hygiene)

### ✅ 11. `setup.py` duplicates `pyproject.toml`
Deleted.

### ✅ 12. `adgen.egg-info/` and other build junk committed
Cleaned: deleted from working tree, `.gitignore` already covers them.

### ⬜ 13. README claims `pip install adgen` works
Still not on PyPI. Either publish or change the snippet.

### ✅ 14. Tests don't cover the new code paths
Added `tests/test_fixes.py` with coverage for workflow packaging, positive-prompt detection, drawtext escaping, LLM JSON tolerance, filename prefixing, completion polling, upload. Current suite: **44 passing**.

### ⬜ 15. `_fuse_products` only uses `product_images[0]`
Remaining product images are still ignored. Will revisit when the workflow gets redesigned (#2).

### ⬜ 16. Stitching with `-c copy` is fragile
Untouched — works for current homogeneous outputs.

## 🟢 Low (cleanup)

- ✅ Mixed-language docstring in `pipeline.py` rewritten in English.
- ✅ `__init__.py` now re-exports `Pipeline` and `BrandKit`.
- ⬜ `pipeline.py` still uses `click.echo` directly; a logger/callback abstraction can wait for the web UI work.
- 🟡 High-quality mode falls back to fast mode on Wan failures (with warning output).

## Remaining / deferred

- #2 IP-Adapter workflow redesign (img2img-style) — still open. The current IP-Adapter workflow `sdxl_ipadapter.json` takes a product image and generates from text, with the poster not actually fed in as conditioning. The pulled Wan2.1 workflow now correctly does image-to-video with the poster as the input frame.
- #13 PyPI publication or README correction — README now says "from source" (not `pip install`).
- #15 multi-product rotation
- #16 Concat re-encode for safety
- Web UI, multi-format export, A/B scoring, Flux 1.dev poster workflow

