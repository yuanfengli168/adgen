"""Tests for the bug fixes applied to AdGen."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adgen.comfyui import ComfyUIClient
from adgen.llm import LLMClient
from adgen.pipeline import WORKFLOWS_DIR, _find_positive_prompt_node
from adgen.postprocess import FFmpegWrapper, _escape_drawtext


# ---------- workflow packaging ----------

class TestWorkflowsPackaging:
    def test_workflows_dir_exists(self):
        assert WORKFLOWS_DIR.exists() and WORKFLOWS_DIR.is_dir()

    def test_expected_workflows_present(self):
        names = {p.name for p in WORKFLOWS_DIR.glob("*.json")}
        assert {"sdxl_poster.json", "sdxl_ipadapter.json", "animatediff_video.json"} <= names

    def test_workflows_dir_is_inside_package(self):
        # Important: must be under the adgen package so pip install ships it.
        import adgen
        pkg_root = Path(adgen.__file__).parent
        assert WORKFLOWS_DIR.is_relative_to(pkg_root)


# ---------- positive prompt node detection ----------

class TestFindPositivePromptNode:
    def test_basic_workflow(self):
        wf = {
            "3": {"class_type": "KSampler", "inputs": {"positive": ["6", 0], "negative": ["7", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "positive"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "negative"}},
        }
        assert _find_positive_prompt_node(wf) == "6"

    def test_real_sdxl_poster_workflow(self):
        wf = json.loads((WORKFLOWS_DIR / "sdxl_poster.json").read_text())
        # In sdxl_poster.json the positive is node "6", negative is node "7".
        assert _find_positive_prompt_node(wf) == "6"

    def test_no_ksampler_returns_none(self):
        wf = {"4": {"class_type": "CheckpointLoaderSimple", "inputs": {}}}
        assert _find_positive_prompt_node(wf) is None

    def test_ksampler_advanced_supported(self):
        wf = {
            "1": {"class_type": "KSamplerAdvanced", "inputs": {"positive": ["9", 0]}},
            "9": {"class_type": "CLIPTextEncode", "inputs": {"text": "pos"}},
        }
        assert _find_positive_prompt_node(wf) == "9"


# ---------- drawtext escaping ----------

class TestDrawtextEscape:
    def test_escapes_colon(self):
        assert _escape_drawtext("Hello: world") == "Hello\\: world"

    def test_escapes_single_quote(self):
        assert _escape_drawtext("it's") == "it\\'s"

    def test_escapes_percent(self):
        assert _escape_drawtext("50% off") == "50\\% off"

    def test_escapes_backslash_first(self):
        # backslash must be escaped before others so we don't double-process
        assert _escape_drawtext("a\\b") == "a\\\\b"

    def test_combined(self):
        out = _escape_drawtext("Don't: pay 50%")
        assert out == "Don\\'t\\: pay 50\\%"

    def test_plain_text_unchanged(self):
        assert _escape_drawtext("simple text") == "simple text"


# ---------- LLM JSON parsing tolerance ----------

class TestLLMParsing:
    def test_extracts_json_from_surrounding_prose(self):
        client = LLMClient()
        raw = (
            "Sure! Here is the JSON you asked for:\n"
            '{"taglines":["a","b","c"],"image_prompts":["p","p","p"],"video_prompts":["v","v","v"]}\n'
            "Hope that helps!"
        )
        result = client._parse_json_response(raw)
        assert len(result["taglines"]) == 3

    def test_extracts_from_fenced_block(self):
        client = LLMClient()
        raw = '```json\n{"taglines":["a"],"image_prompts":["p"],"video_prompts":["v"]}\n```'
        result = client._parse_json_response(raw)
        assert result["taglines"] == ["a", "a", "a"]  # padded

    def test_empty_list_rejected(self):
        client = LLMClient()
        with pytest.raises(ValueError):
            client._parse_json_response('{"taglines":[],"image_prompts":["p"],"video_prompts":["v"]}')

    @patch("adgen.llm.requests.post")
    def test_generate_copy_sends_json_format(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"response": '{"taglines":["a","b","c"],"image_prompts":["p","p","p"],"video_prompts":["v","v","v"]}'},
        )
        client = LLMClient()
        client.generate_copy("a product")
        payload = mock_post.call_args.kwargs["json"]
        assert payload.get("format") == "json"

    @patch("adgen.llm.requests.post")
    def test_brand_context_omitted_when_empty(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"response": '{"taglines":["a","b","c"],"image_prompts":["p","p","p"],"video_prompts":["v","v","v"]}'},
        )
        client = LLMClient()
        client.generate_copy("a product")
        prompt = mock_post.call_args.kwargs["json"]["prompt"]
        # No stray blank line where brand_context would go.
        assert "Product: a product\n\nGenerate" in prompt


# ---------- ComfyUI client: filename collision + completion + upload ----------

class TestComfyUIClientFixes:
    def test_output_filename_prefixed_with_prompt_id(self, tmp_path):
        client = ComfyUIClient()
        prompt_id = "test-prompt-42"
        history_payload = {
            prompt_id: {
                "outputs": {"9": {"images": [{"filename": "ComfyUI_00001_.png", "subfolder": "", "type": "output"}]}}
            }
        }

        with patch("adgen.comfyui.requests.get") as mock_get:
            # First call: /history/<id>
            history_resp = MagicMock(status_code=200, raise_for_status=lambda: None, json=lambda: history_payload)
            # Second call: /view -> binary
            view_resp = MagicMock(status_code=200, raise_for_status=lambda: None, content=b"PNGDATA")
            mock_get.side_effect = [history_resp, view_resp]

            saved = client.get_output_images(prompt_id, str(tmp_path))

        assert len(saved) == 1
        assert saved[0].name == f"{prompt_id}_ComfyUI_00001_.png"
        assert saved[0].read_bytes() == b"PNGDATA"

    def test_get_output_handles_video_gifs_key(self, tmp_path):
        """VHS_VideoCombine surfaces mp4s under the 'gifs' key, not 'images'."""
        client = ComfyUIClient()
        prompt_id = "vid-1"
        history_payload = {
            prompt_id: {
                "outputs": {
                    "9": {
                        "gifs": [{"filename": "video_00007.mp4", "subfolder": "adgen", "type": "output"}]
                    }
                }
            }
        }
        with patch("adgen.comfyui.requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(status_code=200, raise_for_status=lambda: None, json=lambda: history_payload),
                MagicMock(status_code=200, raise_for_status=lambda: None, content=b"MP4DATA"),
            ]
            saved = client.get_output_images(prompt_id, str(tmp_path))

        assert len(saved) == 1
        assert saved[0].name == f"{prompt_id}_video_00007.mp4"
        assert saved[0].read_bytes() == b"MP4DATA"

    def test_wait_for_result_returns_only_when_completed(self):
        client = ComfyUIClient()
        client.poll_interval = 0  # don't actually sleep
        partial = {"abc": {"status": {"completed": False, "status_str": "running"}, "outputs": {"9": {"images": [{}]}}}}
        done = {"abc": {"status": {"completed": True, "status_str": "success"}, "outputs": {"9": {"images": [{}]}}}}
        responses = [
            MagicMock(status_code=200, json=lambda p=partial: p),
            MagicMock(status_code=200, json=lambda d=done: d),
        ]
        with patch("adgen.comfyui.requests.get", side_effect=responses):
            entry = client.wait_for_result("abc", max_wait=5)
        assert entry["status"]["completed"] is True

    def test_wait_for_result_raises_on_error_status(self):
        client = ComfyUIClient()
        client.poll_interval = 0
        err = {"abc": {"status": {"status_str": "error", "messages": ["boom"]}, "outputs": {}}}
        with patch("adgen.comfyui.requests.get", return_value=MagicMock(status_code=200, json=lambda: err)):
            with pytest.raises(RuntimeError, match="ComfyUI execution error"):
                client.wait_for_result("abc", max_wait=5)

    def test_upload_image_missing_file_raises(self):
        client = ComfyUIClient()
        with pytest.raises(FileNotFoundError):
            client.upload_image("/nonexistent/path/poster.png")

    def test_upload_image_posts_and_returns_name(self, tmp_path):
        img = tmp_path / "poster.png"
        img.write_bytes(b"PNGDATA")

        with patch("adgen.comfyui.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None,
                json=lambda: {"name": "poster.png", "subfolder": "", "type": "input"},
            )
            client = ComfyUIClient()
            name = client.upload_image(str(img))

        assert name == "poster.png"
        call = mock_post.call_args
        assert call.args[0].endswith("/upload/image")


# ---------- ffmpeg drawtext detection ----------

class TestFFmpegDrawtextDetection:
    def test_has_drawtext_returns_bool(self):
        assert isinstance(FFmpegWrapper().has_drawtext(), bool)

    @patch("adgen.postprocess.shutil.which", return_value=None)
    def test_has_drawtext_false_when_no_ffmpeg(self, _mock_which):
        assert FFmpegWrapper().has_drawtext() is False

    @patch("adgen.postprocess.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("adgen.postprocess.subprocess.run")
    def test_has_drawtext_true_when_filter_listed(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(
            stdout="Filters:\n T. drawtext          V->V       Draw text using libfreetype.\n ...\n",
            stderr="",
        )
        assert FFmpegWrapper().has_drawtext() is True

    @patch("adgen.postprocess.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("adgen.postprocess.subprocess.run")
    def test_has_drawtext_false_when_filter_missing(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(
            stdout="Filters:\n ... scale ...\n ... overlay ...\n",
            stderr="",
        )
        assert FFmpegWrapper().has_drawtext() is False

    @patch("adgen.postprocess.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("adgen.postprocess.subprocess.run", side_effect=OSError("not found"))
    def test_has_drawtext_false_on_oserror(self, _mock_run, _mock_which):
        assert FFmpegWrapper().has_drawtext() is False

    @patch("adgen.postprocess.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("adgen.postprocess.subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(cmd="ffmpeg", timeout=10))
    def test_has_drawtext_false_on_timeout(self, _mock_run, _mock_which):
        assert FFmpegWrapper().has_drawtext() is False
