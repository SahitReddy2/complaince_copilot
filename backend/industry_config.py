"""
Industry configuration loader.

Loads industry-specific compliance rules from YAML files in config/industries/.
This makes the compliance pipeline reusable across cosmetics, food, supplements,
pharma, and any other regulated industry — only the YAML changes.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import yaml

_CONFIG_DIR = Path(__file__).parent.parent / "config" / "industries"


@lru_cache(maxsize=16)
def load_industry(industry: str) -> Dict:
    """Load an industry config by name (e.g. 'cosmetics', 'food')."""
    path = _CONFIG_DIR / f"{industry}.yaml"
    if not path.exists():
        available = list_industries()
        raise FileNotFoundError(
            f"Industry config '{industry}' not found. Available: {available}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_industries() -> List[str]:
    """Return all available industry config names."""
    if not _CONFIG_DIR.exists():
        return []
    return sorted(p.stem for p in _CONFIG_DIR.glob("*.yaml"))


def get_law_frameworks(industry: str, jurisdiction: str = None) -> List[Dict]:
    """Get the regulatory frameworks for an industry, optionally filtered by jurisdiction."""
    cfg = load_industry(industry)
    frameworks = cfg.get("law_frameworks", [])
    if jurisdiction:
        frameworks = [f for f in frameworks if f.get("jurisdiction") == jurisdiction]
    return frameworks


def get_high_risk_components(industry: str) -> List[str]:
    return load_industry(industry).get("high_risk_components", [])
