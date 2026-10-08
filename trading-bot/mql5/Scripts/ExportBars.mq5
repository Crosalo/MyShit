//+------------------------------------------------------------------+
//| ExportBars.mq5                                                   |
//| Exportiert Kerzen eines Zeitrahmens (Serverzeit, Spread in       |
//| Points) und die Symbol-Spezifikation nach MQL5\Files\<InpFolder>.|
//| Dateien: <NAME>_<TF>.csv, <NAME>_spec.json, meta.json            |
//| Liest nur Daten. Platziert, aendert oder schliesst keine Orders. |
//+------------------------------------------------------------------+
#property copyright "Carlos"
#property version   "1.00"

// Eintraege mit ';' getrennt, Alternativnamen mit '|'. Erster Name = Dateiname.
// MT5 kuerzt String-Inputs auf 255 Zeichen - Liste kurz halten.
input string          InpSymbols = "EURUSD;GBPUSD;USDJPY;USDCHF;USDCAD;AUDUSD;NZDUSD;EURGBP;EURJPY;GBPJPY;EURCHF;AUDJPY;EURAUD;GBPCHF;AUDNZD;CADJPY;EURCAD;GBPAUD;AUDCAD;NZDJPY;CHFJPY;XAUUSD;XAGUSD;US500;US100|NAS100;GER40;UK100;JPN225;WTI|XTIUSD;BRENT|XBRUSD;US30";
input ENUM_TIMEFRAMES InpPeriod  = PERIOD_M5;
input int             InpDays    = 365;
input string          InpFolder  = "m1export";
input int             InpBars    = 0;    // > 0: die letzten InpBars Kerzen am Stueck holen statt nach Datum (fuer D1/H1)
input string          InpSymbolFile = ""; // optional: Datei in MQL5\Files mit einem Symbol je Zeile (statt InpSymbols)

const int CHUNK_DAYS = 30;

//+------------------------------------------------------------------+
string TfName()
  {
   string s = EnumToString(InpPeriod);
   StringReplace(s, "PERIOD_", "");
   return s;
  }

//+------------------------------------------------------------------+
void OnStart()
  {
   WriteMeta();
   string entries[];
   int n = 0;
   if(InpSymbolFile != "")
     {
      int fh = FileOpen(InpSymbolFile, FILE_READ | FILE_TXT | FILE_ANSI);
      if(fh == INVALID_HANDLE)
        {
         PrintFormat("ExportBars: Symboldatei %s nicht lesbar (%d)", InpSymbolFile, GetLastError());
         return;
        }
      while(!FileIsEnding(fh))
        {
         string line = FileReadString(fh);
         StringTrimLeft(line);
         StringTrimRight(line);
         if(line == "")
            continue;
         ArrayResize(entries, n + 1);
         entries[n++] = line;
        }
      FileClose(fh);
     }
   else
      n = StringSplit(InpSymbols, ';', entries);
   datetime to   = TimeTradeServer() + 86400;
   datetime from = to - (datetime)((InpDays + 1) * 86400);

   for(int i = 0; i < n && !IsStopped(); i++)
     {
      string alts[];
      int k = StringSplit(entries[i], '|', alts);
      string sym = "";
      for(int j = 0; j < k; j++)
        {
         bool custom = false;
         if(SymbolExist(alts[j], custom))
           {
            sym = alts[j];
            break;
           }
        }
      if(sym == "")
        {
         PrintFormat("ExportBars: %s nicht gefunden", alts[0]);
         continue;
        }
      ExportSymbol(alts[0], sym, from, to);
     }
   PrintFormat("ExportBars: %s fertig", TfName());
  }

//+------------------------------------------------------------------+
void WriteMeta()
  {
   int h = FileOpen(InpFolder + "\\meta.json", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      return;
   long offset = (long)(TimeTradeServer() - TimeGMT());
   FileWriteString(h, StringFormat("{\"server_offset_seconds\": %I64d, \"server\": \"%s\", \"account_currency\": \"%s\", \"maxbars\": %d}\n",
                                   offset, AccountInfoString(ACCOUNT_SERVER), AccountInfoString(ACCOUNT_CURRENCY),
                                   TerminalInfoInteger(TERMINAL_MAXBARS)));
   FileClose(h);
  }

//+------------------------------------------------------------------+
string JsonEscape(string s)
  {
   StringReplace(s, "\\", "\\\\");
   StringReplace(s, "\"", "\\\"");
   return s;
  }

//+------------------------------------------------------------------+
void WriteSpec(const string name, const string sym)
  {
   int h = FileOpen(InpFolder + "\\" + name + "_spec.json", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      return;
   string js = "{";
   js += StringFormat("\"symbol\": \"%s\", ", sym);
   js += StringFormat("\"path\": \"%s\", ", JsonEscape(SymbolInfoString(sym, SYMBOL_PATH)));
   js += StringFormat("\"currency_profit\": \"%s\", ", SymbolInfoString(sym, SYMBOL_CURRENCY_PROFIT));
   js += StringFormat("\"trade_mode\": %d, ", SymbolInfoInteger(sym, SYMBOL_TRADE_MODE));
   js += StringFormat("\"digits\": %d, ", SymbolInfoInteger(sym, SYMBOL_DIGITS));
   js += StringFormat("\"point\": %.10f, ", SymbolInfoDouble(sym, SYMBOL_POINT));
   js += StringFormat("\"trade_tick_size\": %.10f, ", SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE));
   js += StringFormat("\"trade_tick_value\": %.10f, ", SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE));
   js += StringFormat("\"trade_tick_value_loss\": %.10f, ", SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS));
   js += StringFormat("\"trade_contract_size\": %.4f, ", SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE));
   js += StringFormat("\"volume_min\": %.4f, ", SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN));
   js += StringFormat("\"volume_step\": %.4f, ", SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP));
   js += StringFormat("\"spread_now\": %d", SymbolInfoInteger(sym, SYMBOL_SPREAD));
   js += "}\n";
   FileWriteString(h, js);
   FileClose(h);
  }

//+------------------------------------------------------------------+
void ExportSymbol(const string name, const string sym, const datetime from, const datetime to)
  {
   bool was_selected = (bool)SymbolInfoInteger(sym, SYMBOL_SELECT);
   if(!was_selected)
      SymbolSelect(sym, true);
   WriteSpec(name, sym);

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   int h = FileOpen(InpFolder + "\\" + name + "_" + TfName() + ".csv", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("ExportBars: %s Datei nicht offen (%d)", name, GetLastError());
      return;
     }
   FileWriteString(h, "time,open,high,low,close,spread,volume\n");

   long     total = 0;
   int      empty_chunks = 0;
   datetime last = 0, first = 0;
   if(InpBars > 0)
     {
      MqlRates r[];
      int got = -1, prev = -2, stable = 0;
      // Der Server liefert aeltere Historie stueckweise nach: warten, bis die Anzahl stabil ist
      for(int t = 0; t < 120 && stable < 6 && got < InpBars && !IsStopped(); t++)
        {
         got = CopyRates(sym, InpPeriod, 0, InpBars, r);
         stable = (got > 0 && got == prev) ? stable + 1 : 0;
         prev = got;
         if(got < InpBars)
            Sleep(500);
        }
      for(int x = 0; x < got; x++)
        {
         if(first == 0)
            first = r[x].time;
         last = r[x].time;
         FileWriteString(h, StringFormat("%I64d,%s,%s,%s,%s,%d,%I64d\n", (long)r[x].time,
                                         DoubleToString(r[x].open, digits), DoubleToString(r[x].high, digits),
                                         DoubleToString(r[x].low, digits), DoubleToString(r[x].close, digits),
                                         r[x].spread, r[x].tick_volume));
         total++;
        }
      FileClose(h);
      if(!was_selected)
         SymbolSelect(sym, false);
      PrintFormat("ExportBars: %s %s (%s) %I64d Kerzen, %s bis %s", TfName(), name, sym, total,
                  TimeToString(first), TimeToString(last));
      return;
     }
   // Start ab erster Kerze auf dem Server, sonst wartet jeder leere Abschnitt 30 s
   long srv_first = 0;
   for(int t = 0; t < 20 && srv_first == 0; t++)
     {
      SeriesInfoInteger(sym, InpPeriod, SERIES_SERVER_FIRSTDATE, srv_first);
      if(srv_first == 0)
         Sleep(250);
     }
   datetime start = (srv_first > (long)from) ? (datetime)srv_first : from;
   for(datetime a = start; a < to && !IsStopped(); a += CHUNK_DAYS * 86400)
     {
      datetime b = (datetime)MathMin((long)a + CHUNK_DAYS * 86400, (long)to);
      MqlRates r[];
      int got = -1;
      // Aeltere Historie laedt der Server nach - bis zu 30 s je Abschnitt warten
      for(int t = 0; t < 60 && got <= 0 && !IsStopped(); t++)
        {
         got = CopyRates(sym, InpPeriod, a, b - 1, r);
         if(got <= 0)
            Sleep(500);
        }
      if(got <= 0)
        {
         empty_chunks++;
         continue;
        }
      for(int x = 0; x < got; x++)
        {
         if(r[x].time <= last)
            continue;
         if(first == 0)
            first = r[x].time;
         last = r[x].time;
         FileWriteString(h, StringFormat("%I64d,%s,%s,%s,%s,%d,%I64d\n", (long)r[x].time,
                                         DoubleToString(r[x].open, digits), DoubleToString(r[x].high, digits),
                                         DoubleToString(r[x].low, digits), DoubleToString(r[x].close, digits),
                                         r[x].spread, r[x].tick_volume));
         total++;
        }
     }
   FileClose(h);
   if(!was_selected)
      SymbolSelect(sym, false);
   PrintFormat("ExportBars: %s %s (%s) %I64d Kerzen, %s bis %s, leere Abschnitte %d", TfName(), name, sym, total,
               TimeToString(first), TimeToString(last), empty_chunks);
  }
//+------------------------------------------------------------------+
