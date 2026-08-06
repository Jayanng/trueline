from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_guard_posts_comment_before_enforcing_recorded_exit_code():
    workflow = (ROOT / ".github" / "workflows" / "trueline.yml").read_text(
        encoding="utf-8"
    )
    post = workflow.index("- name: Post comment")
    enforce = workflow.index("- name: Enforce guard decision")

    assert post < enforce
    enforce_block = workflow[enforce:]
    assert "steps.guard.outputs.exit_code" in enforce_block
    assert "exit $code" in enforce_block
