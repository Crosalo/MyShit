# Pocket Logic – YouTube-Shorts-Pipeline

*Money, explained in 40 seconds.* Erstellt täglich automatisch einen englischen Short zum Thema Alltagsgeld und lädt ihn hoch. Läuft als Docker-Container auf dem Hostinger-VPS.

> Status: Stufen 1–3 (Thema, Skript, Sprache) fertig und getestet. Visuals, Untertitel, Schnitt, Upload, Container und die vollständige Anleitung folgen.

## Struktur
```
config.yaml          alle Einstellungen (Kategorien, Formate, Stimme, Farben, Zeiten)
.env                 Geheimnisse (nicht im Repo, Vorlage: .env.example)
assets/logo.png      Logo (steigende Balken, Violett→Pink)
pocketlogic/
  topic.py           1. Themenwahl: Rotation, 60-Tage-Sperre, 5 Vorschläge von Claude
  script.py          2. Skript (Hook → Progression → Climax), JSON-Validierung, 3 Retries
  tts.py             3. edge-tts mit Wortzeitmarken, kürzt bei > 58 s
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
Jeder Run legt einen Ordner unter `data/runs/` an (`topic.json`, `script.json`, `tts/voice.mp3`, `tts/words.json`).
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
