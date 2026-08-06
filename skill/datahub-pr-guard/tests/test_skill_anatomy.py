from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent


def test_frontmatter_anatomy():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---")
    front = text.split("---")[1]
    for key in ("name:", "description:", "user-invocable:", "min-cli-version:", "allowed-tools:"):
        assert key in front, f"missing frontmatter key {key}"
    assert "Bash(datahub *)" in front


def test_required_sections():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for section in ("## Multi-Agent Compatibility", "## Not This Skill", "## Step 1", "## Step 6",
                    "## Common Mistakes", "## Red Flags"):
        assert section in text


def test_references_and_templates_exist():
    assert (SKILL_DIR / "references" / "severity-model.md").exists()
    assert (SKILL_DIR / "templates" / "pr-verdict.template.md").exists()