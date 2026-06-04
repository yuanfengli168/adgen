"""FFmpeg post-processing: text overlay, stitching, audio."""

import subprocess
import shutil
from pathlib import Path
from typing import Optional


def _escape_drawtext(text: str) -> str:
    """Escape characters that are special inside an FFmpeg drawtext filter argument."""
    # Order matters: escape backslash first.
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


class FFmpegWrapper:
    """Wrapper around FFmpeg CLI for video post-processing."""

    def is_available(self) -> bool:
        """Check if FFmpeg is installed."""
        return shutil.which("ffmpeg") is not None

    def has_drawtext(self) -> bool:
        """Check whether the installed ffmpeg has the drawtext filter compiled in.

        Homebrew's default `ffmpeg` formula does not bundle libfreetype/fontconfig,
        so the drawtext filter is missing. The user must install `ffmpeg-full`
        (keg-only) and put it on PATH for text overlay to work.
        """
        if not self.is_available():
            return False
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-filters"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        # Filter list contains lines like " ... drawtext          V->V       ..."
        return any(line.lstrip().startswith(("T. drawtext", ".. drawtext", "... drawtext", "T.. drawtext"))
                   for line in result.stdout.splitlines())

    def add_text_overlay(
        self,
        video_path: str,
        text: str,
        output_path: str,
        fontsize: int = 48,
        fontcolor: str = "white",
        position: str = "bottom",
        fontfile: Optional[str] = None,
    ) -> Path:
        """Add text overlay to video using FFmpeg drawtext filter."""
        # Calculate position
        if position == "bottom":
            y_expr = "h-th-30"
        elif position == "top":
            y_expr = "30"
        elif position == "center":
            y_expr = "(h-th)/2"
        else:
            y_expr = "h-th-30"

        x_expr = "(w-text_w)/2"

        drawtext = (
            f"drawtext=text='{_escape_drawtext(text)}':fontsize={fontsize}:fontcolor={fontcolor}"
            f":x={x_expr}:y={y_expr}"
        )
        if fontfile:
            drawtext += f":fontfile={fontfile}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", drawtext,
            "-an",
            str(output_path),
        ]

        self._run(cmd)
        return Path(output_path)

    def stitch_clips(self, clip_paths: list[str], output_path: str) -> Path:
        """Stitch multiple video clips into one."""
        if len(clip_paths) < 2:
            if clip_paths:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(clip_paths[0], output_path)
                return Path(output_path)
            raise ValueError("Need at least 1 clip to stitch")

        # Create concat file
        out_dir = Path(output_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        concat_file = out_dir / "_concat.txt"

        with open(concat_file, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{Path(clip).resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]

        try:
            self._run(cmd)
        finally:
            concat_file.unlink(missing_ok=True)

        return Path(output_path)

    def add_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> Path:
        """Add background audio to video."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ]

        self._run(cmd)
        return Path(output_path)

    def _run(self, cmd: list[str]):
        """Run an FFmpeg command."""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed (exit {result.returncode}): {result.stderr[:500]}"
            )