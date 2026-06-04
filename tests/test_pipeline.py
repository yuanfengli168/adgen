"""Basic unit tests for AdGen pipeline."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from adgen.brand import BrandKit
from adgen.llm import LLMClient
from adgen.comfyui import ComfyUIClient
from adgen.postprocess import FFmpegWrapper


class TestBrandKit:
    def test_load_valid(self, tmp_path):
        brand_file = tmp_path / "brand.json"
        brand_file.write_text(json.dumps({
            "name": "TestBrand",
            "logo": "logo.png",
            "colors": ["#FF0000"],
            "fonts": ["Arial"],
            "product_images": ["product.png"],
        }))
        brand = BrandKit.load(str(brand_file))
        assert brand.name == "TestBrand"
        assert brand.colors == ["#FF0000"]

    def test_load_missing(self):
        with pytest.raises(FileNotFoundError):
            BrandKit.load("/nonexistent/brand.json")

    def test_brand_context(self):
        brand = BrandKit(name="TestBrand", colors=["#FF0000"], fonts=["Arial"])
        ctx = brand.to_brand_context()
        assert "TestBrand" in ctx
        assert "#FF0000" in ctx

    def test_brand_context_empty(self):
        brand = BrandKit()
        assert brand.to_brand_context() == ""

    def test_validate(self):
        brand = BrandKit(name="", logo="/nonexistent.png")
        issues = brand.validate()
        assert len(issues) >= 2  # empty name + missing logo


class TestLLMClient:
    def test_parse_json_response(self):
        client = LLMClient()
        response = json.dumps({
            "taglines": ["a", "b", "c"],
            "image_prompts": ["p1", "p2", "p3"],
            "video_prompts": ["v1", "v2", "v3"],
        })
        result = client._parse_json_response(response)
        assert len(result["taglines"]) == 3

    def test_parse_json_with_fences(self):
        client = LLMClient()
        response = '```json\n{"taglines":["a","b","c"],"image_prompts":["p1","p2","p3"],"video_prompts":["v1","v2","v3"]}\n```'
        result = client._parse_json_response(response)
        assert len(result["taglines"]) == 3

    def test_parse_json_pad_short(self):
        client = LLMClient()
        result = client._parse_json_response('{"taglines":["a"],"image_prompts":["p1"],"video_prompts":["v1"]}')
        assert len(result["taglines"]) == 3  # padded to 3

    def test_parse_invalid_json(self):
        client = LLMClient()
        with pytest.raises(ValueError):
            client._parse_json_response("not json at all")

    def test_parse_missing_keys(self):
        client = LLMClient()
        with pytest.raises(ValueError):
            client._parse_json_response('{"taglines":["a","b","c"]}')


class TestComfyUIClient:
    @patch("adgen.comfyui.requests.get")
    def test_is_available(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        client = ComfyUIClient()
        assert client.is_available()

    @patch("adgen.comfyui.requests.get")
    def test_is_not_available(self, mock_get):
        mock_get.side_effect = __import__("requests").RequestException("connection refused")
        client = ComfyUIClient()
        assert not client.is_available()

    def test_inject_params(self):
        workflow = {
            "3": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 20}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "old prompt"}},
        }
        params = {"3": {"seed": 137}, "6": {"text": "new prompt"}}
        result = ComfyUIClient._inject_params(workflow, params)
        assert result["3"]["inputs"]["seed"] == 137
        assert result["6"]["inputs"]["text"] == "new prompt"
        # Original should not be modified
        assert workflow["3"]["inputs"]["seed"] == 42


class TestFFmpegWrapper:
    def test_is_available(self):
        # This just checks if ffmpeg is on PATH, likely True on most systems
        ffmpeg = FFmpegWrapper()
        # Don't assert True/False since it depends on the system
        assert isinstance(ffmpeg.is_available(), bool)