//+------------------------------------------------------------------+
//| SpreadProfile.mq5                                                |
//| Misst den echten Spread je Serverstunde aus den Ticks der letzten|
//| InpDays Tage. Je Minute zaehlt der letzte Tick (zeitgewichtet).  |
//| Schreibt MQL5\Files\<InpFolder>\spread_profile.json.             |
//| Liest nur Daten. Platziert, aendert oder schliesst keine Orders. |
//+------------------------------------------------------------------+
#property copyright "Carlos"
#property version   "1.00"

input string InpSymbols = "EURUSD;GBPUSD;USDJPY;USDCHF;USDCAD;AUDUSD;NZDUSD;EURGBP;EURJPY;GBPJPY;EURCHF;AUDJPY;EURAUD;GBPCHF;AUDNZD;CADJPY;EURCAD;GBPAUD;AUDCAD;NZDJPY;CHFJPY;XAUUSD;XAGUSD;US500|SPX500|US500.cash;US100|NAS100|USTEC;GER40|DE40|GER30;UK100|FTSE100;JPN225|JP225|NIKKEI225;WTI|XTIUSD|USOIL|WTI.cash;BRENT|XBRUSD|UKOIL|BRENT.cash;US30|DJ30|WS30";
input int    InpDays    = 15;
input string InpFolder  = "m1export";

//+------------------------------------------------------------------+
void OnStart()
  {
   string entries[];
   int n = StringSplit(InpSymbols, ';', entries);
   string js = "{\n";
   bool first_entry = true;
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
         continue;
      string part = Profile(alts[0], sym);
      if(part == "")
         continue;
      js += (first_entry ? "" : ",\n") + part;
      first_entry = false;
     }
   js += "\n}\n";
   int h = FileOpen(InpFolder + "\\spread_profile.json", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
     {
      FileWriteString(h, js);
      FileClose(h);
     }
   Print("SpreadProfile: fertig");
  }

//+------------------------------------------------------------------+
string Profile(const string name, const string sym)
  {
   bool was_selected = (bool)SymbolInfoInteger(sym, SYMBOL_SELECT);
   if(!was_selected)
      SymbolSelect(sym, true);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);

   double sum[24];
   long   cnt[24];
   ArrayInitialize(sum, 0.0);
   ArrayInitialize(cnt, 0);

   datetime now = TimeTradeServer();
   datetime day_end = now - (now % 86400) + 86400;
   for(int d = InpDays; d >= 1 && !IsStopped(); d--)
     {
      ulong from_msc = (ulong)(day_end - d * 86400) * 1000;
      ulong to_msc   = from_msc + 86400 * 1000 - 1;
      MqlTick ticks[];
      int got = -1;
      for(int t = 0; t < 20 && got < 0; t++)
        {
         got = CopyTicksRange(sym, ticks, COPY_TICKS_INFO, from_msc, to_msc);
         if(got < 0)
            Sleep(300);
        }
      if(got <= 0)
         continue;
      long cur_min = -1;
      double last_spread = 0.0;
      for(int x = 0; x <= got; x++)
        {
         long m = (x < got) ? (long)(ticks[x].time / 60) : -2;
         if(m != cur_min && cur_min >= 0)
           {
            int hr = (int)((cur_min / 60) % 24);
            sum[hr] += last_spread;
            cnt[hr]++;
           }
         if(x == got)
            break;
         if(ticks[x].bid > 0 && ticks[x].ask > 0)
            last_spread = (ticks[x].ask - ticks[x].bid) / point;
         cur_min = m;
        }
     }
   if(!was_selected)
      SymbolSelect(sym, false);

   long total = 0;
   string hours = "";
   for(int hr = 0; hr < 24; hr++)
     {
      total += cnt[hr];
      hours += (hr ? ", " : "") + (cnt[hr] > 0 ? DoubleToString(sum[hr] / cnt[hr], 2) : "null");
     }
   PrintFormat("SpreadProfile: %s (%s) %I64d Minuten", name, sym, total);
   if(total == 0)
      return "";
   return StringFormat("  \"%s\": {\"symbol\": \"%s\", \"point\": %.10f, \"minutes\": %I64d, \"hourly_points\": [%s]}",
                       name, sym, point, total, hours);
  }
//+------------------------------------------------------------------+
