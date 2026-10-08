#!/bin/bash
# MT5 unter Wine einrichten und starten (Benutzer abc). Login und Algo-Haken macht Carlos selbst.
export WINEPREFIX=/config/.wine WINEDEBUG=-all
MT5="$WINEPREFIX/drive_c/Program Files/MetaTrader 5"
exec > >(tee -a /config/mt5-start.log) 2>&1   # auch in die Container-Logs (Hostinger-Panel/API)
echo "== $(date -u) Start"

if [ ! -f "$MT5/terminal64.exe" ]; then
  echo "Wine einrichten (ohne Mono/Gecko-Dialoge)"
  WINEDLLOVERRIDES="mscoree,mshtml=" wineboot -i
  wineserver -w
  wine reg add "HKEY_CURRENT_USER\\Software\\Wine" /v Version /t REG_SZ /d win10 /f
  echo "Wine Mono still installieren (sonst wartet ein Dialog auf einen Klick)"
  wget -qO /tmp/mono.msi https://dl.winehq.org/wine/wine-mono/10.3.0/wine-mono-10.3.0-x86.msi
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
  sleep 30
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

echo "Terminal starten (startet nach Absturz neu)"
while true; do
  wine "$MT5/terminal64.exe"
  echo "$(date -u) Terminal beendet, Neustart in 10 s"
  sleep 10
done
