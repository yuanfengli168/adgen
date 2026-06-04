"""AdGen CLI entry point."""

import click
import sys

from adgen.pipeline import Pipeline
from adgen.brand import BrandKit


@click.group()
@click.version_option(package_name="adgen")
def cli():
    """AdGen — One-line AI ad generator: text → posters + promo video."""
    pass


@cli.command()
@click.argument("product_description")
@click.option("--brand", "brand_path", default=None, help="Path to brand kit JSON")
@click.option("--quality", type=click.Choice(["fast", "high"]), default="fast", help="Quality mode")
@click.option("--output", default="./output", help="Output directory")
@click.option("--comfy-url", default="http://localhost:8188", help="ComfyUI API URL")
@click.option("--ollama-url", default="http://localhost:11434", help="Ollama API URL")
@click.option("--model", default="qwen3:32b", help="Ollama LLM model name")
def generate(product_description, brand_path, quality, output, comfy_url, ollama_url, model):
    """Generate ad posters and video from a product description.

    PRODUCT_DESCRIPTION: Text describing the product to advertise.
    """
    brand = None
    if brand_path:
        try:
            brand = BrandKit.load(brand_path)
            click.echo(f"📦 Brand kit loaded: {brand.name}")
        except Exception as e:
            click.echo(f"⚠️  Failed to load brand kit: {e}", err=True)
            sys.exit(1)

    pipeline = Pipeline(
        comfy_url=comfy_url,
        ollama_url=ollama_url,
        model=model,
        quality=quality,
        output_dir=output,
        brand=brand,
    )

    try:
        pipeline.run(product_description)
    except Exception as e:
        click.echo(f"\n❌ Pipeline failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--download-models", is_flag=True, help="Download required models")
@click.option("--comfy-url", default="http://localhost:8188", help="ComfyUI API URL")
@click.option("--ollama-url", default="http://localhost:11434", help="Ollama API URL")
def setup(download_models, comfy_url, ollama_url):
    """Check dependencies and optionally download models."""
    from adgen.comfyui import ComfyUIClient
    from adgen.llm import LLMClient
    from adgen.postprocess import FFmpegWrapper

    ok = True

    # Check ComfyUI
    comfy = ComfyUIClient(base_url=comfy_url)
    if comfy.is_available():
        click.echo("✅ ComfyUI is running")
    else:
        click.echo("❌ ComfyUI is not running (start it first)")
        ok = False

    # Check Ollama
    llm = LLMClient(base_url=ollama_url)
    if llm.is_available():
        click.echo("✅ Ollama is running")
    else:
        click.echo("❌ Ollama is not running (start it first)")
        ok = False

    # Check FFmpeg
    ffmpeg = FFmpegWrapper()
    if ffmpeg.is_available():
        click.echo("✅ FFmpeg is installed")
        if ffmpeg.has_drawtext():
            click.echo("   ✅ drawtext filter available (text overlay enabled)")
        else:
            click.echo("   ⚠️  drawtext filter NOT available (text overlay will be skipped)")
            click.echo("      Fix on macOS Homebrew:")
            click.echo("        brew install ffmpeg-full")
            click.echo("        export PATH=\"/opt/homebrew/opt/ffmpeg-full/bin:$PATH\"")
    else:
        click.echo("❌ FFmpeg is not installed")
        ok = False

    if download_models:
        click.echo("\n📥 Downloading models...")
        if comfy.is_available():
            click.echo("  ComfyUI models need to be placed manually in ComfyUI models directory.")
            click.echo("  See docs for model download links.")
        if llm.is_available():
            click.echo("  Pulling Ollama model (this may take a while)...")
            llm.pull_model()

    if ok:
        click.echo("\n🎉 All dependencies ready!")
    else:
        click.echo("\n⚠️  Some dependencies are missing. Fix the issues above and run again.")
        sys.exit(1)


if __name__ == "__main__":
    cli()