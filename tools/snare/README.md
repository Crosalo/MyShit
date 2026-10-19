# Snare aus einem Song holen

Zwei Stufen:

1. **Demucs** (`htdemucs_ft`) trennt den Song in Drums, Bass, Vocals und Rest.
   Die Modelle kommen als safetensors aus dem Hugging-Face-Repo des
   Demucs-Autors (`adefossez/HTDemucs-ft`).
2. **drumsep** trennt die Drum-Spur in Kick, Snare, Becken und Toms.
   Braucht die Datei `49469ca8.th`, die nicht im Repo liegt (siehe unten).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r tools/snare/requirements.txt
```

`ffmpeg` muss installiert sein, Demucs liest MP3s darüber.

## Benutzen

Song nach `tools/snare/input/` legen, dann:

```bash
.venv/bin/python tools/snare/separate_snare.py tools/snare/input/song.mp3 \
    --drumsep path/to/49469ca8.th
```

Ergebnis landet in `tools/snare/output/<songname>/`: `drums.wav`, und mit
drumsep zusätzlich `kick.wav`, `snare.wav`, `cymbals.wav`, `toms.wav`.
Ohne `--drumsep` läuft nur Stufe 1.

Auf einer CPU mit 4 Kernen dauert Stufe 1 ungefähr so lange wie der Song
selbst, eher etwas länger.

## Snare ohne drumsep: `analyze_snare.py`

Sucht in `drums.wav` alle Schläge, sortiert sie nach Klangfarbe in vier
Gruppen und nimmt die Gruppe, die nach Snare aussieht. Daraus schneidet es
den saubersten Schlag als `snare_oneshot.wav` (Hochpass bei 100 Hz) und misst
Grundton, Helligkeit und Ausklingzeit.

```bash
.venv/bin/python tools/snare/analyze_snare.py tools/snare/output/<song>/drums.wav tools/snare/output/<song>
```

Die automatische Wahl kann danebenliegen. Die Ausgabe listet jede Gruppe mit
Abstand zwischen den Schlägen; die Snare kommt gleichmäßig alle 2 Beats.
Passt das nicht, die richtige Gruppe als drittes Argument mitgeben.

Fertige One-Shots liegen in `samples/`.

## drumsep-Modell

Original: <https://github.com/inagoy/drumsep> (Google-Drive-Download im
Skript `drumsepInstall`). Spiegel: <https://huggingface.co/vincewin/drumsep>.

`.th`-Dateien sind Pickle-Dateien, die beim normalen Laden beliebigen Code
ausführen können. Das Skript lädt sie deshalb mit `weights_only=True` und
erlaubt nur die Demucs-Modellklassen. Eine manipulierte Datei wird
abgewiesen statt ausgeführt.
