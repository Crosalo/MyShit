"""Offline-Tests (ohne Claude/Netz): Rotation, Aehnlichkeit, JSON-Parsing, Skript-Limits."""
import pytest

from pocketlogic.claude_client import extract_json
from pocketlogic.config import load_config
from pocketlogic.script import Script, check_limits
from pocketlogic.topic import pick_rotation, too_similar


@pytest.fixture
def cfg():
    return load_config()


def test_rotation_never_repeats_last(cfg):
    entries = []
    for _ in range(12):
        cat, fmt = pick_rotation(cfg, entries)
        if entries:
            assert cat != entries[-1]["category"]
            assert fmt != entries[-1]["format"]
        entries.append({"category": cat, "format": fmt})
    # nach N Runs wurde jede Kategorie genutzt
    assert {e["category"] for e in entries} == set(cfg["content"]["categories"])


def test_similarity():
    used = ["Why minimum payments keep you in debt"]
    assert too_similar("Why minimum credit card payments keep you in debt", used)
    assert not too_similar("How grocery stores use decoy pricing", used)


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": [1,2]} done') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        extract_json("no json here")


def _script(words: int, hook="Your bank loves this tiny number.") -> Script:
    body = hook + " " + " ".join(["word"] * (words - len(hook.split())))
    return Script(title="T", hook=hook, script=body,
                  scenes=[{"text": "x", "search_terms": ["bank"]}] * 3,
                  description="Desc.", tags=["money"], category="c", format="f")


def test_limits_ok_adds_shorts_and_disclaimer(cfg):
    s = check_limits(_script(110), cfg)
    assert "#Shorts" in s.description
    assert cfg["content"]["disclaimer"] in s.description


@pytest.mark.parametrize("words", [40, 200])
def test_limits_reject_length(cfg, words):
    with pytest.raises(ValueError):
        check_limits(_script(words), cfg)
