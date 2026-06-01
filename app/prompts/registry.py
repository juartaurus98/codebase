from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.core.logging import get_logger

_logger = get_logger(__name__)

_DEFAULT_REGISTRY_DIR = Path(__file__).parent / "registry"


class PromptTemplate(BaseModel):
    """Parsed and validated prompt YAML file."""

    name: str
    version: str
    description: str
    model: str
    author: str
    created_at: str
    variables: list[str]
    template: str
    metadata: dict[str, Any] = {}


class PromptRegistry:
    """
    Loads versioned prompt templates from YAML files at:
        prompts/registry/<name>/<version>.yaml

    Templates are cached in memory after first load (process lifetime).
    Hot-reload requires a process restart — by design, prompts live in version control.
    """

    def __init__(self, registry_dir: Path | None = None) -> None:
        self._dir = registry_dir or _DEFAULT_REGISTRY_DIR
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str, version: str) -> PromptTemplate:
        """Load and cache a prompt template by name + version."""
        key = f"{name}:{version}"
        if key not in self._cache:
            path = self._dir / name / f"{version}.yaml"
            if not path.exists():
                raise FileNotFoundError(
                    f"Prompt '{name}' version '{version}' not found at {path}"
                )
            with open(path, encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
            self._cache[key] = PromptTemplate(**raw)
            _logger.debug("prompt_loaded", name=name, version=version)
        return self._cache[key]

    def render(self, name: str, version: str, variables: dict[str, Any]) -> str:
        """
        Render a prompt template by substituting variables.
        Raises ValueError if any declared variable is missing.
        Uses Python str.format_map — escape literal braces as {{ and }}.
        """
        prompt = self.load(name, version)
        missing = [v for v in prompt.variables if v not in variables]
        if missing:
            raise ValueError(
                f"Prompt '{name}' v{version} missing variables: {missing}"
            )
        return prompt.template.format_map(variables)

    def list_versions(self, name: str) -> list[str]:
        """Return all available versions for a prompt, sorted ascending."""
        prompt_dir = self._dir / name
        if not prompt_dir.is_dir():
            return []
        return sorted(p.stem for p in prompt_dir.glob("*.yaml"))

    def list_prompts(self) -> list[str]:
        """Return all prompt names registered in the registry directory."""
        if not self._dir.is_dir():
            return []
        return sorted(d.name for d in self._dir.iterdir() if d.is_dir())
