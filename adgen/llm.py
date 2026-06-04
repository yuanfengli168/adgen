"""Ollama LLM integration for ad copywriting."""

import json
import requests
from typing import Optional


COPY_PROMPT_TEMPLATE = """You are an expert advertising copywriter. Given a product description, generate compelling ad content.

Product: {product_description}
{brand_context}

Generate exactly 3 variations. For each variation, provide:
1. A short tagline (5-10 words)
2. A detailed image generation prompt (for creating an ad poster image)
3. A short video motion prompt (for animating the poster into a video)

Respond ONLY with valid JSON in this exact format:
{{
  "taglines": ["tagline1", "tagline2", "tagline3"],
  "image_prompts": ["detailed prompt 1", "detailed prompt 2", "detailed prompt 3"],
  "video_prompts": ["motion prompt 1", "motion prompt 2", "motion prompt 3"]
}}

Image prompts should describe the visual scene, style, lighting, and composition for an ad poster.
Video prompts should describe the motion/camera movement to animate the poster (e.g., "slow zoom in, particles floating").
Do not include any other text outside the JSON."""


class LLMClient:
    """Client for Ollama HTTP API."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:32b", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def pull_model(self) -> bool:
        """Pull the model via Ollama API."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                timeout=600,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def generate_copy(self, product_description: str, brand_context: str = "") -> dict:
        """Generate ad copy: taglines, image prompts, video prompts.

        Returns dict with keys: taglines, image_prompts, video_prompts.
        """
        prompt = COPY_PROMPT_TEMPLATE.format(
            product_description=product_description,
            brand_context=brand_context,
        )

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.8},
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Ollama API error: {e}") from e

        data = resp.json()
        raw_response = data.get("response", "")

        # Extract JSON from response (may have surrounding text)
        return self._parse_json_response(raw_response)

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response, handling possible markdown fences."""
        # Try to find JSON block
        text = text.strip()

        # Remove markdown code fences if present
        if "```json" in text:
            text = text.split("```json", 1)[1]
            text = text.split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1]
            text = text.split("```", 1)[0]

        text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON response: {e}\nRaw: {text[:500]}") from e

        # Validate structure
        required_keys = {"taglines", "image_prompts", "video_prompts"}
        if not required_keys.issubset(result.keys()):
            raise ValueError(f"Missing keys in LLM response. Got: {list(result.keys())}")

        # Ensure 3 variations
        for key in ["taglines", "image_prompts", "video_prompts"]:
            if len(result[key]) < 3:
                # Pad with duplicates if fewer than 3
                while len(result[key]) < 3:
                    result[key].append(result[key][-1])
            result[key] = result[key][:3]

        return result