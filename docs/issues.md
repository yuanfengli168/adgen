# AdGen — Code Review / Issues to Fix

Audit of `adgen/` package against current source. Items are roughly ordered by severity.

## 🔴 Critical (functional bugs)

### 1. Positive & negative prompts both get overwritten with the same text
**File:** [adgen/adgen/pipeline.py](adgen/adgen/pipeline.py#L113-L122) (`_build_poster_params`)

The loop iterates every `CLIPTextEncode` node and injects the new prompt. In `sdxl_poster.json` node `6` is the positive prompt and node `7` is the negative prompt — both will be set to the product prompt, destroying the negative-prompt steering. Same bug exists in `_generate_videos`.

**Fix:** Identify positive vs. negative node explicitly (e.g. hard-code node IDs in a small template config, or look up which `CLIPTextEncode` node is referenced by `KSampler.inputs.positive`).

### 2. IP-Adapter "fusion" never feeds the poster into the workflow
**File:** [adgen/adgen/pipeline.py](adgen/adgen/pipeline.py#L139-L165) (`_fuse_products`)

The function iterates `poster_paths` but only overrides the `LoadImage` node with `product_image` and a new seed. The poster itself is never injected, so each "fused" output is just a fresh IP-Adapter render from the product image — the posters from step 2 are discarded.

**Fix:** Either upload the poster to ComfyUI's input dir and reference it from a second `LoadImage` node, or use an img2img-style IP-Adapter workflow that takes the poster as the base latent.

### 3. ComfyUI output filenames collide across runs
**File:** [adgen/adgen/comfyui.py](adgen/adgen/comfyui.py#L96-L125) (`get_output_images`)

ComfyUI typically returns names like `ComfyUI_00001_.png`. Three posters submitted in a row all save to `posters/ComfyUI_00001_.png`, overwriting each other. The pipeline then calls `poster_paths[:3]` expecting 3 distinct files.

**Fix:** Prefix saved filenames with `prompt_id` or an index, e.g. `f"{prompt_id}_{filename}"`.

### 4. `drawtext` filter breaks on special characters in the tagline
**File:** [adgen/adgen/postprocess.py](adgen/adgen/postprocess.py#L19-L52) (`add_text_overlay`)

`text='{text}'` is interpolated raw. Any `'`, `:`, `\`, or `%` in a tagline (very common in ad copy) will produce a malformed FFmpeg filter graph.

**Fix:** Escape per the [drawtext docs](https://ffmpeg.org/ffmpeg-filters.html#drawtext): replace `\` → `\\\\`, `'` → `\\'`, `:` → `\\:`, `%` → `\\%`. Better, write the text to a temp `.txt` file and use `textfile=`.

### 5. `add_text_overlay` fails when the input video has no audio
**File:** [adgen/adgen/postprocess.py](adgen/adgen/postprocess.py#L46-L52)

AnimateDiff outputs have no audio track; `-codec:a copy` errors with "Output file does not contain any stream".

**Fix:** Drop `-codec:a copy` (or use `-an`) when input has no audio. Probe with `ffprobe` or just always re-encode video with `-an`.

### 6. `wait_for_result` returns prematurely on partial output
**File:** [adgen/adgen/comfyui.py](adgen/adgen/comfyui.py#L52-L80)

It returns as soon as `outputs` is non-empty. Multi-node workflows (e.g. AnimateDiff + VideoCombine) can have intermediate `outputs` registered while still executing.

**Fix:** Only return when `entry["status"]["completed"] is True` (or `status_str == "success"`).

### 7. Workflows folder is not shipped with the installed package
**File:** [adgen/pyproject.toml](adgen/pyproject.toml#L29-L31), [adgen/adgen/pipeline.py](adgen/adgen/pipeline.py#L17)

`WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"` works from a source checkout but `pip install adgen` won't include the `workflows/` directory — it lives outside the package and isn't declared as package data. Pipeline will silently fall through to placeholder images.

**Fix:** Move `workflows/` to `adgen/adgen/workflows/`, update the path to `Path(__file__).parent / "workflows"`, and add `[tool.setuptools.package-data]\nadgen = ["workflows/*.json"]` to `pyproject.toml`.

## 🟠 High (LLM / robustness)

### 8. LLM JSON parser fails when model adds prose around the JSON
**File:** [adgen/adgen/llm.py](adgen/adgen/llm.py#L94-L120)

Only handles markdown fences. Local models (Qwen, Llama) very often emit `"Sure! Here is the JSON: { ... }"`. Use Ollama's `format: "json"` option or extract via `re.search(r"\{.*\}", text, re.DOTALL)`.

### 9. Empty `brand_context` leaves a stray blank line in the prompt
Minor, but `COPY_PROMPT_TEMPLATE` always inserts a newline after `{brand_context}`. Guard with a leading newline only when non-empty.

### 10. No timeout / no streaming for large local models
`generate_copy` runs synchronously with a 120s timeout. Qwen3 32B on Apple Silicon can easily exceed that. Either bump the default or stream.

## 🟡 Medium (packaging / hygiene)

### 11. `setup.py` duplicates `pyproject.toml` and is out of sync
[adgen/setup.py](adgen/setup.py) doesn't list the `[project.optional-dependencies]` (`ffmpeg`, `dev`). With `pyproject.toml` providing the full PEP 621 metadata, `setup.py` should be deleted.

### 12. `adgen.egg-info/` is committed
[adgen/adgen.egg-info/](adgen/adgen.egg-info/) is build output and should be in `.gitignore` along with `output/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`.

### 13. README claims `pip install adgen` works
[adgen/README.md](adgen/README.md#L60-L62) — package is not on PyPI yet; either upload or change the instructions.

### 14. Tests don't cover `Pipeline`
[adgen/tests/test_pipeline.py](adgen/tests/test_pipeline.py) only tests sub-clients. There is no end-to-end mocked test of `Pipeline.run`, even though that's where most of the bugs above live.

### 15. `Pipeline._fuse_products` only ever uses `product_images[0]`
[adgen/adgen/pipeline.py](adgen/adgen/pipeline.py#L141) — remaining product images are silently ignored. Either rotate through them per poster or document the limitation.

### 16. Stitching with `-c copy` requires identical streams
[adgen/adgen/postprocess.py](adgen/adgen/postprocess.py#L73-L93) — generally OK because all clips come from the same workflow, but a single off-spec clip aborts concat. Safer to re-encode (`-c:v libx264 -crf 18 -an`).

## 🟢 Low (cleanup)

- Mixed-language docstring in [adgen/adgen/pipeline.py](adgen/adgen/pipeline.py#L1) (Chinese + English).
- `__init__.py` exposes only `__version__`; consider re-exporting `Pipeline`, `BrandKit` for `from adgen import Pipeline`.
- `pipeline.py` uses `click.echo` directly — fine, but couples the library to Click. Consider passing a logger/callback so `Pipeline` is usable from a web UI later.
- High-quality mode silently falls back to fast mode (acknowledged TODOs). Consider raising or warning louder.
- `get_output_images` does `img_info["filename"]` without a `KeyError` guard.

## Suggested order to tackle

1. Fix #7 (workflows packaging) and #3 (filename collisions) — without these, the happy path never works.
2. Fix #1 and #2 — these silently degrade image quality and make "fusion" a no-op.
3. Fix #4, #5, #6 — these crash the post-processing / video stages.
4. Fix #8 — LLM step is the entry point; flaky JSON parsing blocks everything.
5. Then packaging/hygiene (#11–#16).
