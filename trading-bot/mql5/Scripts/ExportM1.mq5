//+------------------------------------------------------------------+
//| ExportM1.mq5                                                     |
//| Exportiert M1-Kerzen (Serverzeit, Spread in Points) und die      |
//| Symbol-Spezifikation nach MQL5\Files\<InpFolder>.                |
//| Liest nur Daten. Platziert, aendert oder schliesst keine Orders. |
//+------------------------------------------------------------------+
#property copyright "Carlos"
#property version   "1.00"

// Eintraege mit ';' getrennt, Alternativnamen mit '|'. Erster Name = Dateiname.
input string InpSymbols = "EURUSD;GBPUSD;USDJPY;USDCHF;USDCAD;AUDUSD;NZDUSD;EURGBP;EURJPY;GBPJPY;EURCHF;AUDJPY;EURAUD;GBPCHF;AUDNZD;CADJPY;EURCAD;GBPAUD;AUDCAD;NZDJPY;CHFJPY;XAUUSD;XAGUSD;US500|SPX500|US500.cash;US100|NAS100|USTEC;GER40|DE40|GER30;UK100|FTSE100;JPN225|JP225|NIKKEI225;WTI|XTIUSD|USOIL|WTI.cash;BRENT|XBRUSD|UKOIL|BRENT.cash;US30|DJ30|WS30";
input int    InpDays    = 365;
input string InpFolder  = "m1export";

const int CHUNK_DAYS = 30;

//+------------------------------------------------------------------+
void OnStart()
  {
   WriteMeta();
   WriteCatalog();

   string entries[];
   int n = StringSplit(InpSymbols, ';', entries);
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
         PrintFormat("ExportM1: %s nicht gefunden", alts[0]);
         continue;
        }
      ExportSymbol(alts[0], sym, from, to);
     }
   Print("ExportM1: fertig");
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
void WriteCatalog()
  {
   int h = FileOpen(InpFolder + "\\catalog.csv", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      return;
   FileWriteString(h, "name;path;trade_mode;digits\n");
   int total = SymbolsTotal(false);
   for(int i = 0; i < total; i++)
     {
      string s = SymbolName(i, false);
      FileWriteString(h, StringFormat("%s;%s;%d;%d\n", s, SymbolInfoString(s, SYMBOL_PATH),
                                      SymbolInfoInteger(s, SYMBOL_TRADE_MODE), SymbolInfoInteger(s, SYMBOL_DIGITS)));
     }
   FileClose(h);
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
string JsonEscape(string s)
  {
   StringReplace(s, "\\", "\\\\");
   StringReplace(s, "\"", "\\\"");
   return s;
  }

//+------------------------------------------------------------------+
void ExportSymbol(const string name, const string sym, const datetime from, const datetime to)
  {
   bool was_selected = (bool)SymbolInfoInteger(sym, SYMBOL_SELECT);
   if(!was_selected)
      SymbolSelect(sym, true);
   WriteSpec(name, sym);

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   int h = FileOpen(InpFolder + "\\" + name + "_M1.csv", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("ExportM1: %s Datei nicht offen (%d)", name, GetLastError());
      return;
     }
   FileWriteString(h, "time,open,high,low,close,spread\n");

   long     total = 0;
   int      empty_chunks = 0;
   datetime last = 0, first = 0;
   for(datetime a = from; a < to && !IsStopped(); a += CHUNK_DAYS * 86400)
     {
      datetime b = (datetime)MathMin((long)a + CHUNK_DAYS * 86400, (long)to);
      MqlRates r[];
      int got = -1;
      for(int t = 0; t < 30 && got <= 0; t++)
        {
         got = CopyRates(sym, PERIOD_M1, a, b - 1, r);
         if(got <= 0)
            Sleep(300);
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
         FileWriteString(h, StringFormat("%I64d,%s,%s,%s,%s,%d\n", (long)r[x].time,
                                         DoubleToString(r[x].open, digits), DoubleToString(r[x].high, digits),
                                         DoubleToString(r[x].low, digits), DoubleToString(r[x].close, digits),
                                         r[x].spread));
         total++;
        }
     }
   FileClose(h);
   if(!was_selected)
      SymbolSelect(sym, false);
   PrintFormat("ExportM1: %s (%s) %I64d Kerzen, %s bis %s, leere Abschnitte %d", name, sym, total,
               TimeToString(first), TimeToString(last), empty_chunks);
  }
//+------------------------------------------------------------------+
