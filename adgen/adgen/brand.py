"""Brand kit loader."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BrandKit:
    """Brand configuration loaded from JSON."""

    name: str = ""
    logo: Optional[str] = None
    colors: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    product_images: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> "BrandKit":
        """Load brand kit from JSON file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Brand kit not found: {path}")

        with open(p) as f:
            data = json.load(f)

        return cls(
            name=data.get("name", ""),
            logo=data.get("logo"),
            colors=data.get("colors", []),
            fonts=data.get("fonts", []),
            product_images=data.get("product_images", []),
        )

    def to_brand_context(self) -> str:
        """Generate brand context string for LLM prompts."""
        parts = []
        if self.name:
            parts.append(f"Brand name: {self.name}")
        if self.colors:
            parts.append(f"Brand colors: {', '.join(self.colors)}")
        if self.fonts:
            parts.append(f"Brand fonts: {', '.join(self.fonts)}")
        if self.product_images:
            parts.append(f"Product images available: {len(self.product_images)}")

        if parts:
            return "Brand context:\n" + "\n".join(f"  {p}" for p in parts)
        return ""

    def validate(self) -> list[str]:
        """Validate brand kit and return list of issues."""
        issues = []
        if not self.name:
            issues.append("Brand name is empty")

        if self.logo and not Path(self.logo).exists():
            issues.append(f"Logo file not found: {self.logo}")

        for img in self.product_images:
            if not Path(img).exists():
                issues.append(f"Product image not found: {img}")

        return issues