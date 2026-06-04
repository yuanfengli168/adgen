"""ComfyUI REST API client."""

import json
import time
import requests
from pathlib import Path
from typing import Any, Optional


class ComfyUIClient:
    """Client for ComfyUI REST API."""

    def __init__(self, base_url: str = "http://localhost:8188", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = 2  # seconds between status checks

    def is_available(self) -> bool:
        """Check if ComfyUI is running."""
        try:
            resp = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def submit_workflow(self, workflow: dict, params: Optional[dict] = None) -> str:
        """Submit a workflow for execution. Returns prompt_id."""
        if params:
            workflow = self._inject_params(workflow, params)

        payload = {"prompt": workflow}

        try:
            resp = requests.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to submit workflow: {e}") from e

        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"ComfyUI workflow error: {data['error']}")

        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"No prompt_id in response: {data}")

        return prompt_id

    def wait_for_result(self, prompt_id: str, max_wait: int = 600) -> dict:
        """Wait for workflow execution to complete. Returns history entry."""
        start = time.time()
        while time.time() - start < max_wait:
            try:
                resp = requests.get(
                    f"{self.base_url}/history/{prompt_id}",
                    timeout=self.timeout,
                )
            except requests.RequestException:
                time.sleep(self.poll_interval)
                continue

            if resp.status_code == 200:
                history = resp.json()
                if prompt_id in history:
                    entry = history[prompt_id]
                    # Check for errors
                    if entry.get("status", {}).get("status_str") == "error":
                        raise RuntimeError(f"ComfyUI execution error: {entry['status']}")
                    # Check if completed
                    outputs = entry.get("outputs", {})
                    if outputs or entry.get("status", {}).get("completed", False):
                        return entry

            time.sleep(self.poll_interval)

        raise TimeoutError(f"Workflow {prompt_id} did not complete within {max_wait}s")

    def get_output_images(self, prompt_id: str, output_dir: str) -> list[Path]:
        """Download output images from a completed workflow."""
        try:
            resp = requests.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get history: {e}") from e

        history = resp.json()
        if prompt_id not in history:
            raise ValueError(f"No history found for prompt_id: {prompt_id}")

        entry = history[prompt_id]
        outputs = entry.get("outputs", {})
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        for node_id, node_output in outputs.items():
            images = node_output.get("images", [])
            for img_info in images:
                filename = img_info["filename"]
                subfolder = img_info.get("subfolder", "")
                img_type = img_info.get("type", "output")

                # Download image
                try:
                    params = {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": img_type,
                    }
                    resp = requests.get(
                        f"{self.base_url}/view",
                        params=params,
                        timeout=self.timeout,
                    )
                    resp.raise_for_status()
                except requests.RequestException as e:
                    raise RuntimeError(f"Failed to download image {filename}: {e}") from e

                save_path = out_dir / filename
                save_path.write_bytes(resp.content)
                saved.append(save_path)

        return saved

    @staticmethod
    def _inject_params(workflow: dict, params: dict) -> dict:
        """Inject parameters into workflow nodes.

        Params is a dict mapping node IDs to their input overrides.
        Example: {"6": {"text": "new prompt"}, "3": {"seed": 42}}
        """
        workflow = json.loads(json.dumps(workflow))  # deep copy
        for node_id, overrides in params.items():
            if node_id in workflow:
                node = workflow[node_id]
                if "inputs" in node:
                    node["inputs"].update(overrides)
        return workflow

    @staticmethod
    def load_workflow(path: str) -> dict:
        """Load a workflow JSON file."""
        with open(path) as f:
            return json.load(f)