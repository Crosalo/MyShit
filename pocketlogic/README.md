# Pocket Logic – YouTube-Shorts-Pipeline

*Money, explained in 40 seconds.* Erstellt täglich automatisch einen englischen Short zum Thema Alltagsgeld und lädt ihn hoch. Läuft als Docker-Container auf dem Hostinger-VPS.

> Status: Stufen 1–6 (Thema, Skript, Sprache, Visuals, Untertitel, Schnitt) fertig und getestet. Upload, Benachrichtigung, Container und die vollständige Anleitung folgen.

## Struktur
```
config.yaml          alle Einstellungen (Kategorien, Formate, Stimme, Farben, Zeiten)
.env                 Geheimnisse (nicht im Repo, Vorlage: .env.example)
assets/logo.png      Logo (steigende Balken, Violett→Pink)
pocketlogic/
  topic.py           1. Themenwahl: Rotation, 60-Tage-Sperre, 5 Vorschläge von Claude
  script.py          2. Skript (Hook → Progression → Climax), JSON-Validierung, 3 Retries
  tts.py             3. edge-tts mit Wortzeitmarken, kürzt bei > 58 s
  visuals.py         4. Szenen-Timing, Pixabay-Clips (Cache, keine Wiederholung), Fallback-Karten
  cards.py              Grafiken im Pocket-Logic-Stil (Hook, Fakten, Wasserzeichen, Thumbnail)
  subtitles.py       5. .ass-Untertitel, 2 Wörter pro Einblendung, aktives Wort in Orchid
  render.py          6. ffmpeg: Szenen + Überblendung, Untertitel, Musik-Ducking, -14 LUFS
  claude_client.py   `claude -p … --output-format json` (Pro-Abo, KEIN API-Key)
  runlog.py          Run-Log (data/run_log.jsonl)
  brand.py           Logo-Erzeugung
  cli.py             Kommandozeile, Lock-Datei
```

## Befehle
```bash
pip install -r requirements.txt
python -m pocketlogic.cli --dry-run                         # alle Stufen ohne Upload
python -m pocketlogic.cli --stage topic --run data/runs/x   # nur eine Stufe
python -m pocketlogic.cli --from-stage tts --run data/runs/x
python -m pocketlogic.cli --topic "Why minimum payments keep you in debt"
python -m pytest tests                                      # Offline-Tests
```
Jeder Run legt einen Ordner unter `data/runs/` an (`topic.json`, `script.json`, `tts/`, `visuals/`, `subs.ass`, `final.mp4`, `thumbnail.png`).

## Hintergrundmusik (optional)
Lizenzfreie Musik (mp3/m4a/wav) in `data/music/` ablegen, z. B. aus der YouTube Audio Library oder von Pixabay Music.
Pro Video wird zufällig ein Titel gewählt und automatisch unter die Stimme geduckt. Ohne Dateien gibt es keine Musik.
Einzelstufen-Läufe zählen nicht für die Themen-Rotation, nur vollständige Runs.

## Branding
| Rolle | Farbe |
|---|---|
| Hintergrund | `#120A24` |
| Flächen | `#221542` |
| Text | `#F5F0FF` |
| Akzent (Schlüsselwort, Zahl, aktives Untertitelwort) | `#C77DFF` |
| Label (Serie/Format) | `#FF5CC8` |

Schrift: Inter ExtraBold (Titel, Hook, Untertitel), Inter Medium (Text, Quellen).
