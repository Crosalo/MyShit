"""Texte ausschliesslich ueber Claude Code headless (`claude -p`), Pro-Abo, keine API.

Auth im Dauerbetrieb: CLAUDE_CODE_OAUTH_TOKEN (aus `claude setup-token`).
ANTHROPIC_API_KEY wird bewusst entfernt, damit nie versehentlich API-Kosten entstehen.
"""
import json
import logging
import os
import re
import subprocess
import time

log = logging.getLogger(__name__)

RATE_LIMIT_HINTS = ("usage limit", "rate limit", "limit reached", "overloaded", "429")


class ClaudeError(RuntimeError):
    pass


class ClaudeRateLimit(ClaudeError):
    pass


def _env() -> dict:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)  # harte Regel: keine kostenpflichtige API
    return env


def run_claude(prompt: str, cfg: dict, extra_args: list[str] | None = None, cwd=None) -> str:
    """Ein Aufruf; liefert den Text aus dem `result`-Feld. extra_args z. B. ["--allowedTools", "Read"]."""
    c = cfg["claude"]
    try:
        proc = subprocess.run(
            [c["command"], "-p", prompt, "--output-format", "json", *(extra_args or [])],
            capture_output=True, text=True, timeout=c["timeout_seconds"], env=_env(), cwd=cwd,
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeError(f"claude Timeout nach {c['timeout_seconds']}s") from e
    except FileNotFoundError as e:
        raise ClaudeError("claude CLI nicht gefunden (PATH pruefen)") from e

    raw = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 or '"is_error":true' in proc.stdout.replace(" ", ""):
        if any(h in raw.lower() for h in RATE_LIMIT_HINTS):
            raise ClaudeRateLimit(raw[:300])
        raise ClaudeError(f"claude Fehler (rc={proc.returncode}): {raw[:300]}")
    try:
        return json.loads(proc.stdout)["result"]
    except (json.JSONDecodeError, KeyError) as e:
        raise ClaudeError(f"claude-Ausgabe nicht lesbar: {proc.stdout[:200]}") from e


def extract_json(text: str):
    """Holt JSON aus einer Antwort, auch wenn sie in ```-Bloecken oder Text steckt."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    candidate = m.group(1) if m else text
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = candidate.find(opener), candidate.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(candidate[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("kein gueltiges JSON in der Antwort")


def ask_json(prompt: str, cfg: dict, validate=None, attempts: int | None = None,
             extra_args: list[str] | None = None, cwd=None):
    """Fragt Claude, parst JSON, validiert; bis zu N Retries. Bei Pro-Limit wird gewartet."""
    attempts = attempts or cfg["script"]["max_attempts"]
    waits = 0
    last_err: Exception | None = None
    n = 0
    while n < attempts:
        try:
            data = extract_json(run_claude(prompt, cfg, extra_args, cwd))
            return validate(data) if validate else data
        except ClaudeRateLimit as e:
            waits += 1
            if waits > cfg["claude"]["rate_limit_max_waits"]:
                raise
            mins = cfg["claude"]["rate_limit_wait_minutes"]
            log.warning("Pro-Limit erreicht, warte %d min (%d/%d)", mins, waits,
                        cfg["claude"]["rate_limit_max_waits"])
            time.sleep(mins * 60)
            continue  # zaehlt nicht als Versuch
        except (ValueError, ClaudeError) as e:
            last_err = e
            n += 1
            log.warning("Versuch %d/%d fehlgeschlagen: %s", n, attempts, e)
            if isinstance(e, ClaudeError) and n < attempts:
                time.sleep(3 * n)
    raise ClaudeError(f"nach {attempts} Versuchen aufgegeben: {last_err}")
