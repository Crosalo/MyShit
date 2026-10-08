"""Baut das Docker-Compose für MT5 auf dem Hostinger-VPS (srv1421899).

- MT5 läuft unter Wine in einem Browser-Desktop (linuxserver/baseimage-kasmvnc), nur über HTTPS (Port 3001)
  mit Benutzer und Passwort erreichbar.
- Die EA-Quellen (BBFade, TwinScalp + Exposure.mqh; ORB passt nicht ins Hostinger-Limit von 2 x 8192 Zeichen) und Chart-Vorlagen werden als Paket mitgegeben
  und beim Start auf dem Server kompiliert. In allen Vorlagen ist "Algo-Handel erlauben" AUS (expertmode=0):
  einloggen und einschalten macht Carlos selbst.
- Das Passwort für den Browser-Zugang wird zufällig erzeugt und nur lokal in ~/claude/vps-mt5-zugang.txt
  abgelegt (Rechte 600), nicht im Repo.

    python3 trading-bot/deploy/build_bundle.py
Ausgabe: <scratch>/docker-compose.yaml und <scratch>/env.txt
"""
import base64
import io
import os
import re
import secrets
import tarfile
from pathlib import Path

MT5 = Path.home() / "Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/MQL5"
OUT = Path(os.environ.get("BUNDLE_OUT", "/private/tmp/claude-501/mt5-vps"))
SECRET = Path.home() / "claude/vps-mt5-zugang.txt"
HERE = Path(__file__).parent


def chart_inputs(chr_name: str) -> list[str]:
    t = (MT5 / "Profiles/Charts/Default" / chr_name).read_text(encoding="utf-16")
    return re.search(r"<expert>.*?<inputs>\n(.*?)</inputs>", t, re.S).group(1).strip().splitlines()


def template(symbol: str, minutes: int, ea: str, inputs: list[str]) -> bytes:
    lines = ["<chart>", f"symbol={symbol}", "period_type=0", f"period_size={minutes}", "mode=1", "scale=8", "",
             "<expert>", f"name={ea}", f"path=Experts\\{ea}.ex5", "expertmode=0", "<inputs>", *inputs, "</inputs>",
             "</expert>", "", "<window>", "height=100.000000", "<indicator>", "name=Main", "path=", "apply=1",
             "</indicator>", "</window>", "</chart>", ""]
    return b"\xff\xfe" + "\r\n".join(lines).encode("utf-16-le")


def slim(data: bytes) -> bytes:
    """Quelltext ohne ganze Kommentarzeilen, Einrückung und Leerzeilen (Hostinger erlaubt nur 2 x 8192 Zeichen)."""
    text = data.decode("utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else data.decode("utf-8-sig")
    keep = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in keep if ln and not ln.startswith("//")).encode("utf-8")


def bundle() -> str:
    twin = ["InpRiskEUR=1.0", "InpMaxRiskPct=20.0", "InpRMult=3.0", "InpNYOffsetHours=7", "InpStartNY=3", "InpEndNY=16",
            "InpMaxSpreadPts=0", "InpMarginBuffer=0.5", "InpMagic=20261008", "InpComment=TWIN1M",
            "InpAllowedSymbols=US30,NAS100,US500", "InpCorrGroup=NAS100,US500,US30", "InpMaxCorrPos=2"]
    files = {f"Experts/{n}.mq5": slim((MT5 / f"Experts/{n}.mq5").read_bytes()) for n in ("BBFade", "TwinScalp")}
    files |= {f"Include/{n}.mqh": slim((MT5 / f"Include/{n}.mqh").read_bytes()) for n in ("Exposure",)}
    files |= {
        "Profiles/Templates/BBFade_NAS100_M15.tpl": template("NAS100", 15, "BBFade", chart_inputs("chart03.chr")),
        "Profiles/Templates/BBFade_US30_M15.tpl": template("US30", 15, "BBFade", chart_inputs("chart05.chr")),
        "Profiles/Templates/TwinScalp_NAS100_M1.tpl": template("NAS100", 1, "TwinScalp", twin),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz", preset=9) as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
    return base64.b64encode(buf.getvalue()).decode()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b64 = bundle()
    compose = (HERE / "mt5-vps/docker-compose.template.yaml").read_text()
    # Compose ersetzt $VAR auch in configs.content -> Shell-Variablen als $$ schreiben
    start = (HERE / "mt5-vps/start.sh").read_text().replace("$", "$$")
    indent = lambda s: "\n".join("      " + line for line in s.splitlines())
    compose = compose.replace("__START__", indent(start))
    head = "VNC_USER=carlos\nVNC_PASSWORD=" + "x" * 24 + "\nBUNDLE="
    cut = 8192 - len(head) - 50                      # Teil 1 in die Umgebungsvariable
    rest = b64[cut:]
    compose = compose.replace("__BUNDLE2__", "      " + rest)  # Teil 2 in die Compose-Datei
    if len(compose) > 8192:
        raise SystemExit(f"zu gross: compose {len(compose)} Zeichen (Paket {len(b64)})")
    b64 = b64[:cut]
    (OUT / "docker-compose.yaml").write_text(compose)
    if not SECRET.exists():
        SECRET.write_text(f"MT5 auf dem VPS: https://72.62.146.219:3001\nBenutzer: carlos\nPasswort: {secrets.token_urlsafe(18)}\n")
        SECRET.chmod(0o600)
    pw = re.search(r"Passwort: (\S+)", SECRET.read_text()).group(1)
    (OUT / "env.txt").write_text(f"VNC_USER=carlos\nVNC_PASSWORD={pw}\nBUNDLE={b64}\n")
    (OUT / "env.txt").chmod(0o600)
    print(f"compose {len(compose)} Zeichen, Paket {len(b64)} Zeichen -> {OUT}")


if __name__ == "__main__":
    main()
