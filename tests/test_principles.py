"""Tests for mirage_core principles parser and thinking mode selection."""

from pathlib import Path

from mirage_core.principles import (
    PrinciplesIndex,
    ThinkingMode,
    clear_cache,
    get_principles,
    load_principles,
    parse_principles,
)

PRINCIPLES_PATH = Path(__file__).parent.parent / "knowledge" / "principles.md"


def test_parse_sections():
    idx = load_principles(PRINCIPLES_PATH)
    assert len(idx.sections) >= 10
    assert idx.get_section("Core Philosophy") is not None
    assert idx.get_section("nonexistent") is None


def test_parse_decision_filters():
    idx = load_principles(PRINCIPLES_PATH)
    assert len(idx.decision_filters) == 7
    names = [f.name for f in idx.decision_filters]
    assert "Identity alignment" in names
    assert "2-minute test" in names
    assert "Compound potential" in names


def test_validate_required_sections():
    idx = load_principles(PRINCIPLES_PATH)
    missing = idx.validate()
    assert len(missing) == 0, f"Missing required sections: {missing}"


def test_validate_detects_missing():
    idx = parse_principles("## Some Random Section\nHello world\n")
    missing = idx.validate()
    assert len(missing) > 0
    assert "Core Philosophy" in missing


def test_section_quotes():
    idx = load_principles(PRINCIPLES_PATH)
    philosophy = idx.get_section("Core Philosophy")
    assert philosophy is not None
    assert len(philosophy.quotes) > 0


def test_section_tactics():
    idx = load_principles(PRINCIPLES_PATH)
    env = idx.get_section("Environment Design")
    assert env is not None
    assert len(env.tactics) > 0


def test_content_hash_stable():
    idx1 = load_principles(PRINCIPLES_PATH)
    idx2 = load_principles(PRINCIPLES_PATH)
    assert idx1.content_hash == idx2.content_hash


def test_cache_returns_same():
    clear_cache()
    idx1 = get_principles(PRINCIPLES_PATH)
    idx2 = get_principles(PRINCIPLES_PATH)
    assert idx1 is idx2


def test_cache_clear_reloads():
    clear_cache()
    idx1 = get_principles(PRINCIPLES_PATH)
    clear_cache()
    idx2 = get_principles(PRINCIPLES_PATH)
    assert idx1 is not idx2
    assert idx1.content_hash == idx2.content_hash


def test_thinking_mode_capture():
    idx = load_principles(PRINCIPLES_PATH)
    ctx = ThinkingMode.get_context(ThinkingMode.CAPTURE, idx)
    assert "Decision Filters" in ctx
    assert "2-Minute" in ctx


def test_thinking_mode_prioritize():
    idx = load_principles(PRINCIPLES_PATH)
    ctx = ThinkingMode.get_context(ThinkingMode.PRIORITIZE, idx)
    assert "Decision Filters" in ctx
    assert "Keystone" in ctx


def test_thinking_mode_review():
    idx = load_principles(PRINCIPLES_PATH)
    ctx = ThinkingMode.get_context(ThinkingMode.REVIEW, idx)
    assert "Decision Filters" in ctx
    assert "Review" in ctx or "Annual" in ctx


def test_thinking_mode_plan():
    idx = load_principles(PRINCIPLES_PATH)
    ctx = ThinkingMode.get_context(ThinkingMode.PLAN, idx)
    assert "Decision Filters" in ctx


def test_all_modes_produce_output():
    idx = load_principles(PRINCIPLES_PATH)
    for mode in [ThinkingMode.CAPTURE, ThinkingMode.PRIORITIZE, ThinkingMode.REVIEW, ThinkingMode.PLAN]:
        ctx = ThinkingMode.get_context(mode, idx)
        assert len(ctx) > 100, f"Mode {mode} produced too little context ({len(ctx)} chars)"


if __name__ == "__main__":
    test_parse_sections()
    test_parse_decision_filters()
    test_validate_required_sections()
    test_validate_detects_missing()
    test_section_quotes()
    test_section_tactics()
    test_content_hash_stable()
    test_cache_returns_same()
    test_cache_clear_reloads()
    test_thinking_mode_capture()
    test_thinking_mode_prioritize()
    test_thinking_mode_review()
    test_thinking_mode_plan()
    test_all_modes_produce_output()
    print("All principles tests passed!")
