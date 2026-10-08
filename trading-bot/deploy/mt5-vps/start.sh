#!/bin/bash
# MT5 unter Wine einrichten und starten (Benutzer abc). Login und Algo-Haken macht Carlos selbst.
export WINEPREFIX=/config/.wine WINEDEBUG=-all
MT5="$WINEPREFIX/drive_c/Program Files/MetaTrader 5"
exec > >(tee -a /config/mt5-start.log) 2>&1   # auch in die Container-Logs (Hostinger-Panel/API)
echo "== $(date -u) Start"

if [ ! -f "$MT5/terminal64.exe" ]; then
  echo "Wine einrichten (frisches Profil, ohne Mono/Gecko-Dialoge): $(wine --version)"
  rm -rf "$WINEPREFIX"
  WINEDLLOVERRIDES="mscoree,mshtml=" wineboot -i
  wineserver -w
  wine reg add "HKEY_CURRENT_USER\\Software\\Wine" /v Version /t REG_SZ /d win10 /f
  echo "Wine Mono still installieren (sonst wartet ein Dialog auf einen Klick)"
  wget -qO /tmp/mono.msi https://dl.winehq.org/wine/wine-mono/9.4.0/wine-mono-9.4.0-x86.msi
  wine msiexec /i /tmp/mono.msi /qn
  wineserver -w
  echo "MT5 vom offiziellen MetaQuotes-Server installieren"
  wget -qO /tmp/mt5setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
  wine /tmp/mt5setup.exe /auto &
  for i in $(seq 1 180); do
    [ -f "$MT5/terminal64.exe" ] && break
    [ $((i % 6)) = 0 ] && echo "warte $((i * 5)) s, offene Fenster: $(wmctrl -l 2>/dev/null | cut -c 15- | tr '\n' '|')"
    sleep 5
  done
  # Die Standard-Bibliothek (Include/Trade/Trade.mqh) legt erst das laufende Terminal an, sonst scheitert das Kompilieren
  for i in $(seq 1 36); do [ -f "$MT5/MQL5/Include/Trade/Trade.mqh" ] && break; sleep 5; done
  sleep 10
  pkill -f terminal64.exe; pkill -f mt5setup.exe
  wineserver -w
  echo "MT5 installiert: $(ls "$MT5" | tr '\n' ' ')"
fi

echo "EAs und Vorlagen einspielen (Algo-Handel in allen Vorlagen AUS)"
mkdir -p "$MT5/MQL5"
# Die Desktop-Sitzung erbt nicht immer alle Container-Variablen: dann aus s6 lesen
B="${BUNDLE:-$(cat /run/s6/container_environment/BUNDLE 2>/dev/null)}"
B="$B$(tr -d ' \n' < /bot/bundle2.b64)"
echo "$B" | base64 -d | tar xJ -C "$MT5/MQL5" && echo "Paket entpackt: $(ls "$MT5/MQL5/Experts" | tr '\n' ' ')"
cd "$MT5" || exit 1
for f in BBFade TwinScalp; do
  wine MetaEditor64.exe /compile:"MQL5\\Experts\\$f.mq5" /log:"MQL5\\Experts\\$f.log"
  echo "$f: $(iconv -f UTF-16LE -t UTF-8 "MQL5/Experts/$f.log" 2>/dev/null | grep -a Result)"
done

# MT5-Journal und EA-Logs (UTF-16) alle 30 s in die Container-Logs kopieren, damit sie per Hostinger-API lesbar sind
logpump() {
  while true; do
    for f in "$MT5/logs/$(date -u +%Y%m%d).log" "$MT5/MQL5/Logs/$(date -u +%Y%m%d).log"; do
      [ -f "$f" ] || continue
      k=/tmp/off_$(echo "$f" | md5sum | cut -c1-8); off=$(cat "$k" 2>/dev/null || echo 0); size=$(stat -c %s "$f")
      [ "$size" -lt "$off" ] && off=0
      if [ "$size" -gt "$off" ]; then
        tag=$(basename "$(dirname "$f")")
        tail -c +$((off + 1)) "$f" | iconv -f UTF-16LE -t UTF-8 2>/dev/null | tr -d '\r' | sed -e 's/\xEF\xBB\xBF//g' -e "s|^|[$tag] |"
        echo "$size" > "$k"
      fi
    done
    sleep 30
  done
}
logpump &

echo "Terminal starten (startet nach Absturz neu)"
while true; do
  wine "$MT5/terminal64.exe"
  echo "$(date -u) Terminal beendet, Neustart in 10 s"
  sleep 10
done
