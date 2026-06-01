from pathlib import Path

import pytest
import yaml

from app.prompts.registry import PromptRegistry


@pytest.fixture
def registry_dir(tmp_path: Path) -> Path:
    """Create a minimal prompt YAML for testing."""
    prompt_dir = tmp_path / "greet"
    prompt_dir.mkdir()
    data = {
        "name": "greet",
        "version": "1.0.0",
        "description": "Greeting prompt",
        "model": "claude-sonnet-4-6",
        "author": "test",
        "created_at": "2024-01-01",
        "variables": ["name", "lang"],
        "template": "Hello {name}, please speak in {lang}.",
        "metadata": {"tags": ["test"], "eval_score": 0.9},
    }
    (prompt_dir / "1.0.0.yaml").write_text(yaml.dump(data), encoding="utf-8")
    (prompt_dir / "2.0.0.yaml").write_text(
        yaml.dump({**data, "version": "2.0.0", "template": "Hi {name} ({lang})."}),
        encoding="utf-8",
    )
    return tmp_path


def test_load_returns_prompt_template(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    p = reg.load("greet", "1.0.0")
    assert p.name == "greet"
    assert p.version == "1.0.0"
    assert "name" in p.variables
    assert "lang" in p.variables


def test_load_caches_on_second_call(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    p1 = reg.load("greet", "1.0.0")
    p2 = reg.load("greet", "1.0.0")
    assert p1 is p2


def test_render_substitutes_variables(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    result = reg.render("greet", "1.0.0", {"name": "Alice", "lang": "French"})
    assert "Alice" in result
    assert "French" in result


def test_render_raises_on_missing_variable(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    with pytest.raises(ValueError, match="missing variables"):
        reg.render("greet", "1.0.0", {"name": "Alice"})


def test_load_raises_file_not_found(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    with pytest.raises(FileNotFoundError):
        reg.load("nonexistent", "9.9.9")


def test_list_versions(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    versions = reg.list_versions("greet")
    assert versions == ["1.0.0", "2.0.0"]


def test_list_versions_empty_for_unknown_prompt(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    assert reg.list_versions("unknown") == []


def test_list_prompts(registry_dir: Path) -> None:
    reg = PromptRegistry(registry_dir)
    assert "greet" in reg.list_prompts()


def test_example_prompt_in_real_registry() -> None:
    """Smoke-test the bundled example prompt."""
    reg = PromptRegistry()
    p = reg.load("example", "1.0.0")
    assert "task" in p.variables
    result = reg.render("example", "1.0.0", {"task": "summarise", "context": "test"})
    assert "summarise" in result
