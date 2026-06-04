"""Pipeline orchestrator —串联 LLM → ComfyUI → FFmpeg 所有步骤."""

import json
import time
from pathlib import Path

import click

from adgen.comfyui import ComfyUIClient
from adgen.llm import LLMClient
from adgen.postprocess import FFmpegWrapper
from adgen.brand import BrandKit


# Workflow template paths (relative to package)
WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"


class Pipeline:
    """Main ad generation pipeline."""

    def __init__(
        self,
        comfy_url: str = "http://localhost:8188",
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen3:32b",
        quality: str = "fast",
        output_dir: str = "./output",
        brand: BrandKit | None = None,
    ):
        self.comfy = ComfyUIClient(base_url=comfy_url)
        self.llm = LLMClient(base_url=ollama_url, model=model)
        self.ffmpeg = FFmpegWrapper()
        self.quality = quality
        self.output_dir = Path(output_dir)
        self.brand = brand

    def run(self, product_description: str):
        """Execute the full ad generation pipeline."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        click.echo(f"🎨 AdGen Pipeline ({self.quality} mode)")
        click.echo(f"   Product: {product_description}")
        click.echo(f"   Output: {self.output_dir}")
        click.echo()

        # Step 1: LLM generates ad copy
        click.echo("📝 Step 1/5: Generating ad copy with LLM...")
        brand_context = self.brand.to_brand_context() if self.brand else ""
        copy = self.llm.generate_copy(product_description, brand_context)
        click.echo(f"   Taglines: {copy['taglines']}")
        click.echo()

        # Step 2: Generate poster images with ComfyUI
        click.echo("🖼️  Step 2/5: Generating poster images...")
        poster_paths = self._generate_posters(copy["image_prompts"], copy["taglines"])
        click.echo(f"   Generated {len(poster_paths)} posters")
        click.echo()

        # Step 3: IP-Adapter product fusion
        fused_paths = poster_paths
        if self.brand and self.brand.product_images:
            click.echo("🔗 Step 3/5: Fusing product images with IP-Adapter...")
            fused_paths = self._fuse_products(poster_paths)
            click.echo(f"   Fused {len(fused_paths)} images")
        else:
            click.echo("🔗 Step 3/5: Skipping product fusion (no product images in brand kit)")
        click.echo()

        # Step 4: Generate video clips
        click.echo("🎬 Step 4/5: Generating video clips...")
        clip_paths = self._generate_videos(copy["video_prompts"])
        click.echo(f"   Generated {len(clip_paths)} clips")
        click.echo()

        # Step 5: Post-processing
        click.echo("🎞️  Step 5/5: Post-processing...")
        self._postprocess(clip_paths, copy["taglines"])
        click.echo()

        click.echo("✅ Done! Check output directory:")
        click.echo(f"   {self.output_dir.resolve()}")

    def _generate_posters(self, image_prompts: list[str], taglines: list[str]) -> list[Path]:
        """Generate poster images via ComfyUI."""
        if self.quality == "high":
            workflow_file = WORKFLOWS_DIR / "sdxl_poster.json"  # TODO: flux workflow
            click.echo("   ⚠️  High quality mode uses SDXL for now (Flux workflow not yet implemented)")
        else:
            workflow_file = WORKFLOWS_DIR / "sdxl_poster.json"

        if not workflow_file.exists():
            click.echo(f"   ⚠️  Workflow not found: {workflow_file}, using placeholder")
            return self._create_placeholder_images(image_prompts, taglines)

        workflow = ComfyUIClient.load_workflow(str(workflow_file))
        poster_paths = []

        for i, (prompt, tagline) in enumerate(zip(image_prompts, taglines)):
            click.echo(f"   Generating poster {i+1}/3...")

            # Inject prompt into workflow
            params = self._build_poster_params(workflow, prompt, i)
            prompt_id = self.comfy.submit_workflow(workflow, params)
            self.comfy.wait_for_result(prompt_id)
            images = self.comfy.get_output_images(prompt_id, str(self.output_dir / "posters"))

            poster_paths.extend(images)

        return poster_paths[:3]  # Ensure max 3

    def _build_poster_params(self, workflow: dict, prompt: str, index: int) -> dict:
        """Build parameter overrides for poster workflow."""
        params = {}
        seeds = [42, 137, 2024]

        for node_id, node in workflow.items():
            if node.get("class_type") == "KSampler":
                params[node_id] = {"seed": seeds[index % len(seeds)]}
            elif node.get("class_type") in ("CLIPTextEncode", "CLIPTextEncodeSDXL"):
                inputs = node.get("inputs", {})
                # Positive prompt node typically has no reference to another node for text
                if "text" in inputs and isinstance(inputs["text"], str):
                    params.setdefault(node_id, {})["text"] = prompt

        return params

    def _fuse_products(self, poster_paths: list[Path]) -> list[Path]:
        """Fuse product images into posters using IP-Adapter."""
        workflow_file = WORKFLOWS_DIR / "sdxl_ipadapter.json"

        if not workflow_file.exists():
            click.echo("   ⚠️  IP-Adapter workflow not found, skipping fusion")
            return poster_paths

        workflow = ComfyUIClient.load_workflow(str(workflow_file))
        product_image = self.brand.product_images[0] if self.brand and self.brand.product_images else None
        fused = []

        for i, poster in enumerate(poster_paths):
            click.echo(f"   Fusing product {i+1}/3...")
            params = {}
            # Override product image path and prompt
            for node_id, node in workflow.items():
                if node.get("class_type") == "LoadImage" and product_image:
                    params.setdefault(node_id, {})["image"] = product_image
                elif node.get("class_type") == "KSampler":
                    params.setdefault(node_id, {})["seed"] = 42 + i

            prompt_id = self.comfy.submit_workflow(workflow, params)
            self.comfy.wait_for_result(prompt_id)
            images = self.comfy.get_output_images(prompt_id, str(self.output_dir / "fused"))
            fused.extend(images)

        return fused[:3] if fused else poster_paths

    def _generate_videos(self, video_prompts: list[str]) -> list[Path]:
        """Generate video clips via ComfyUI."""
        if self.quality == "high":
            click.echo("   ⚠️  High quality video (Wan2.1) not yet implemented, using AnimateDiff")

        workflow_file = WORKFLOWS_DIR / "animatediff_video.json"

        if not workflow_file.exists():
            click.echo("   ⚠️  Video workflow not found, using placeholder")
            return self._create_placeholder_videos(video_prompts)

        workflow = ComfyUIClient.load_workflow(str(workflow_file))
        clip_paths = []

        for i, vprompt in enumerate(video_prompts):
            click.echo(f"   Generating clip {i+1}/3...")

            params = {}
            seeds = [42, 137, 2024]
            for node_id, node in workflow.items():
                if node.get("class_type") == "KSampler":
                    params.setdefault(node_id, {})["seed"] = seeds[i]
                elif node.get("class_type") in ("CLIPTextEncode", "CLIPTextEncodeSDXL"):
                    inputs = node.get("inputs", {})
                    if "text" in inputs and isinstance(inputs["text"], str):
                        params.setdefault(node_id, {})["text"] = vprompt

            prompt_id = self.comfy.submit_workflow(workflow, params)
            self.comfy.wait_for_result(prompt_id, max_wait=600)
            images = self.comfy.get_output_images(prompt_id, str(self.output_dir / "clips"))
            clip_paths.extend(images)

        return clip_paths[:3]

    def _postprocess(self, clip_paths: list[Path], taglines: list[str]):
        """FFmpeg post-processing: stitch, overlay text."""
        if not self.ffmpeg.is_available():
            click.echo("   ⚠️  FFmpeg not available, skipping post-processing")
            return

        if not clip_paths:
            click.echo("   ⚠️  No video clips to process, skipping post-processing")
            return

        videos_dir = self.output_dir / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)

        # Stitch clips if multiple
        if len(clip_paths) >= 2:
            try:
                final = videos_dir / "final.mp4"
                self.ffmpeg.stitch_clips([str(p) for p in clip_paths], str(final))
                click.echo(f"   Stitched: {final}")
            except Exception as e:
                click.echo(f"   ⚠️  Stitching failed: {e}")
        elif len(clip_paths) == 1:
            import shutil
            final = videos_dir / "final.mp4"
            shutil.copy2(clip_paths[0], final)

        # Add text overlay with primary tagline
        final = videos_dir / "final.mp4"
        if final.exists() and taglines:
            try:
                tagged = videos_dir / "final_tagged.mp4"
                brand_name = self.brand.name if self.brand else ""
                text = f"{taglines[0]}  |  {brand_name}" if brand_name else taglines[0]
                fontcolor = self.brand.colors[0].lstrip("#") if self.brand and self.brand.colors else "ffffff"
                self.ffmpeg.add_text_overlay(str(final), text, str(tagged), fontcolor=fontcolor)
                click.echo(f"   Text overlay: {tagged}")
            except Exception as e:
                click.echo(f"   ⚠️  Text overlay failed: {e}")

    def _create_placeholder_images(self, image_prompts: list[str], taglines: list[str]) -> list[Path]:
        """Create placeholder poster images when ComfyUI is unavailable."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            poster_dir = self.output_dir / "posters"
            poster_dir.mkdir(parents=True, exist_ok=True)
            paths = []

            colors = [(30, 30, 80), (80, 30, 30), (30, 80, 30)]
            for i, (prompt, tagline) in enumerate(zip(image_prompts, taglines)):
                img = Image.new("RGB", (1024, 1024), colors[i % 3])
                draw = ImageDraw.Draw(img)
                # Draw tagline
                draw.text((50, 450), tagline, fill="white")
                # Draw prompt hint
                draw.text((50, 550), prompt[:80] + "...", fill="gray")
                path = poster_dir / f"poster_{i+1}.png"
                img.save(str(path))
                paths.append(path)

            return paths
        except ImportError:
            click.echo("   ⚠️  Pillow not available for placeholders")
            return []

    def _create_placeholder_videos(self, video_prompts: list[str]) -> list[Path]:
        """Create placeholder video clips when ComfyUI is unavailable."""
        clips_dir = self.output_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        click.echo("   ⚠️  Video generation skipped (no workflow available)")
        return []