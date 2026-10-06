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


def test_scene_timings_cover_audio():
    from pocketlogic.visuals import scene_timings
    words = [{"word": f"w{i}", "start": i * 0.4, "end": i * 0.4 + 0.3} for i in range(100)]
    scenes = [{"text": " ".join(["x"] * n)} for n in (10, 30, 20, 40)]
    t = scene_timings(scenes, words, audio_dur=40.0, tail=0.6)
    assert t[0][0] == 0.0 and t[-1][1] == 40.6
    assert all(a[1] == b[0] for a, b in zip(t, t[1:]))      # lueckenlos
    assert all(e > s for s, e in t)


def test_subtitle_chunks_and_ass(cfg, tmp_path):
    from pocketlogic.subtitles import ass_color, build_ass, chunk_words
    words = [{"word": "Pay", "start": 0.0, "end": 0.2}, {"word": "the", "start": 0.25, "end": 0.35},
             {"word": "minimum", "start": 0.4, "end": 0.8}, {"word": "now", "start": 1.5, "end": 1.7}]
    chunks = chunk_words(words, max_words=2, pause=0.25)
    assert [len(c) for c in chunks] == [2, 1, 1]           # Pause vor "now" trennt
    assert ass_color("#C77DFF") == "&H00FF7DC7"
    text = build_ass(cfg, words, tmp_path / "s.ass").read_text()
    assert text.count("Dialogue:") == 4 and "MINIMUM" in text
