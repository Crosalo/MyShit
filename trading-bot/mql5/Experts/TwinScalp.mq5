//+------------------------------------------------------------------+
//|  TwinScalp.mq5                                                   |
//|  TwinTraders "1-Minuten-Scalping" (YouTube yc0-tOcjmH0)          |
//|                                                                  |
//|  Regel (wie research/videos_oct8.py, Test D):                    |
//|    1. H1: Marktrichtung = zuletzt respektierte Fair Value Gap.   |
//|       Respektiert: Kurs war in der Luecke und schliesst danach   |
//|       auf ihrer Ausgangsseite. Durchbrochen: Schluss jenseits    |
//|       der Luecke -> Richtung dreht.                              |
//|    2. Kurs laeuft in die juengste H1-FVG in Marktrichtung.       |
//|    3. M5: Sweep (Extrem jenseits der 6 Kerzen davor), danach     |
//|       BOS binnen 12 Kerzen, mit einer M5-FVG im Ausbruchsbein.   |
//|    4. Kurs laeuft binnen 2 Stunden in die M5-FVG.                |
//|    5. M1: Sweep (jenseits der 5 Kerzen davor), BOS binnen 10     |
//|       Kerzen -> Markt-Order. Stop am M1-Sweep-Extrem,            |
//|       Ziel InpRMult x Risiko. Ein Trade je H1-FVG.               |
//|    Handelszeit 3:00-16:00 New York, danach wird geschlossen.    |
//|                                                                  |
//|  BEFUND VOR DEM BAU (Python, M1 11/2020-10/2026, nach Kosten):   |
//|    US100 -0,009R (931 Trades), US30 +0,038R (954), US500 -0,010R |
//|    Kein nachweisbarer Vorteil. Gebaut auf ausdruecklichen Wunsch,|
//|    erst Tick-Test im MT5-Tester, dann Entscheidung.              |
//+------------------------------------------------------------------+
#property copyright "BB-Fade Projekt"
#property version   "1.00"

#include <Trade\Trade.mqh>
#include <Exposure.mqh>

input double InpRiskEUR      = 1.00;       // Festes Risiko je Trade in Kontowaehrung
input double InpMaxRiskPct   = 20.0;       // Harte Obergrenze in % der Balance
input double InpRMult        = 3.0;        // Ziel = x mal Risiko
input int    InpNYOffsetHours= 7;          // Serverzeit minus New York (Fusion: immer 7)
input int    InpStartNY      = 3;          // Ab Stunde (New York)
input int    InpEndNY        = 16;         // Bis Stunde (New York), dann schliessen
input int    InpMaxSpreadPts = 0;          // Max. Spread in Points (0 = aus)
input double InpMarginBuffer = 0.50;       // Anteil des Eigenkapitals als Margin-Obergrenze
input ulong  InpMagic        = 20261008;   // Magic Number
input string InpComment      = "TWIN1M";   // Order-Kommentar
input string InpAllowedSymbols = "US30,NAS100,US500"; // Erlaubte Symbole (leer = alle)
input string InpCorrGroup      = "NAS100,US500,US30"; // Eng korrelierte Maerkte
input int    InpMaxCorrPos     = 2;        // Max. gleichgerichtete Positionen

CTrade trade;

//--- H1-Luecken
struct Zone { datetime ready; datetime inv; int dir; double top; double bot; bool touched; };
Zone     zones[];
int      bias       = 0;
datetime lastH1     = 0;
datetime usedReady[];          // H1-FVGs, auf die schon gehandelt wurde
int      usedDir[];

//--- M5/M1-Kandidaten
struct Cand
{
   int      dir;
   datetime zoneReady;
   datetime sweepTime;     // Zeit der M5-Sweep-Kerze
   double   ref;           // BOS-Niveau
   int      barsLeft;      // verbleibende M5-Kerzen fuer den BOS
   bool     bos;
   int      fvgWait;       // nach BOS: noch so viele M5-Kerzen auf eine FVG warten
   bool     fvgOk;
   double   top, bot;      // M5-FVG
   double   ext5;          // M5-Sweep-Extrem: wird es ueberschritten, ist das Setup tot
   datetime fvgReady;
   int      m1Left;        // verbleibende M1-Kerzen (2 Stunden)
   bool     entered;
   int      swAge;         // M1-Kerzen seit dem M1-Sweep (-1 = kein Sweep)
   double   swRef;         // M1-BOS-Niveau
   double   swExt;         // M1-Sweep-Extrem = Stop
};
Cand     cands[];
datetime lastM5 = 0, lastM1 = 0;

//+------------------------------------------------------------------+
bool SymbolAllowed()
{
   string list = InpAllowedSymbols;
   StringTrimLeft(list); StringTrimRight(list);
   if(StringLen(list) == 0) return(true);
   string parts[];
   int k = StringSplit(list, StringGetCharacter(",", 0), parts);
   for(int i = 0; i < k; i++)
   {
      string s = parts[i];
      StringTrimLeft(s); StringTrimRight(s);
      if(s == _Symbol) return(true);
   }
   return(false);
}

int NYHour(datetime t)
{
   MqlDateTime d;
   TimeToStruct(t - InpNYOffsetHours * 3600, d);
   return(d.hour);
}

bool InSession(datetime t)
{
   int h = NYHour(t);
   return(h >= InpStartNY && h < InpEndNY);
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(!SymbolAllowed())
   {
      PrintFormat("FEHLER: %s steht nicht in InpAllowedSymbols (\"%s\").", _Symbol, InpAllowedSymbols);
      return(INIT_FAILED);
   }
   if(Period() != PERIOD_M1)
   {
      Print("FEHLER: Der EA gehoert auf einen M1-Chart.");
      return(INIT_FAILED);
   }
   if(InpRiskEUR <= 0.0 || InpRMult <= 0.0) return(INIT_PARAMETERS_INCORRECT);
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(30);
   PrintFormat("TwinScalp v1.00 gestartet: %s M1, Risiko %.2f %s, Ziel %.1fR, %02d-%02d Uhr New York.",
               _Symbol, InpRiskEUR, AccountInfoString(ACCOUNT_CURRENCY), InpRMult, InpStartNY, InpEndNY);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//  H1-Luecken und Marktrichtung aus den fertigen Stundenkerzen       |
//+------------------------------------------------------------------+
void RebuildH1()
{
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_H1, 1, 400, r);   // ab Index 1: nur fertige Kerzen
   if(n < 10) return;
   ArrayResize(zones, 0);
   bias = 0;
   for(int i = 2; i < n; i++)
   {
      datetime endI = r[i].time + 3600;
      for(int z = 0; z < ArraySize(zones); z++)
      {
         if(zones[z].inv != 0) continue;
         if(zones[z].dir == 1)
         {
            if(r[i].close < zones[z].bot) { zones[z].inv = endI; bias = -1; }
            else if(r[i].low <= zones[z].top) zones[z].touched = true;
            if(zones[z].inv == 0 && zones[z].touched && r[i].close > zones[z].top) { bias = 1; zones[z].touched = false; }
         }
         else
         {
            if(r[i].close > zones[z].top) { zones[z].inv = endI; bias = 1; }
            else if(r[i].high >= zones[z].bot) zones[z].touched = true;
            if(zones[z].inv == 0 && zones[z].touched && r[i].close < zones[z].bot) { bias = -1; zones[z].touched = false; }
         }
      }
      Zone nz;
      nz.ready = endI; nz.inv = 0; nz.touched = false;
      if(r[i - 2].high < r[i].low)      { nz.dir = 1;  nz.top = r[i].low;      nz.bot = r[i - 2].high; }
      else if(r[i - 2].low > r[i].high) { nz.dir = -1; nz.top = r[i - 2].low;  nz.bot = r[i].high; }
      else continue;
      int s = ArraySize(zones);
      ArrayResize(zones, s + 1);
      zones[s] = nz;
   }
}

bool ZoneUsed(datetime ready, int dir)
{
   for(int i = 0; i < ArraySize(usedReady); i++)
      if(usedReady[i] == ready && usedDir[i] == dir) return(true);
   return(false);
}

void MarkUsed(datetime ready, int dir)
{
   int s = ArraySize(usedReady);
   ArrayResize(usedReady, s + 1); ArrayResize(usedDir, s + 1);
   usedReady[s] = ready; usedDir[s] = dir;
}

// juengste nicht entwertete Luecke in Richtung dir (oder -1)
int CurrentZone(int dir)
{
   for(int z = ArraySize(zones) - 1; z >= 0; z--)
      if(zones[z].dir == dir && zones[z].inv == 0) return(z);
   return(-1);
}

//+------------------------------------------------------------------+
//  Fertige M5-Kerze: BOS/FVG der Kandidaten, neue Sweeps             |
//+------------------------------------------------------------------+
void OnM5Bar()
{
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, PERIOD_M5, 1, 20, r) < 20) return;   // r[0] = gerade fertige Kerze

   for(int c = ArraySize(cands) - 1; c >= 0; c--)
   {
      if(cands[c].fvgOk) continue;
      int d = cands[c].dir;
      if(!cands[c].bos)
      {
         cands[c].barsLeft--;
         if((r[0].close - cands[c].ref) * d > 0)
         {
            cands[c].bos = true;
            cands[c].fvgWait = 3;
            // juengste FVG im Bein: von der BOS-Kerze zurueck bis zwei Kerzen nach dem Sweep
            for(int i = 0; i + 2 < 20 && r[i + 2].time >= cands[c].sweepTime; i++)
               if(CheckFvg(r, i, c)) break;
         }
         else if(cands[c].barsLeft <= 0) { RemoveCand(c); continue; }
      }
      else
      {
         cands[c].fvgWait--;
         CheckFvg(r, 0, c);
      }
      if(cands[c].bos && !cands[c].fvgOk && cands[c].fvgWait <= 0) RemoveCand(c);
   }

   // neuer Sweep in der H1-Luecke?
   if(bias == 0 || !InSession(r[0].time)) return;
   int z = CurrentZone(bias);
   if(z < 0 || ZoneUsed(zones[z].ready, bias)) return;
   if(!(r[0].low <= zones[z].top && r[0].high >= zones[z].bot)) return;
   double hi6 = r[1].high, lo6 = r[1].low;
   for(int i = 2; i <= 6; i++) { hi6 = MathMax(hi6, r[i].high); lo6 = MathMin(lo6, r[i].low); }
   bool swept = bias == 1 ? r[0].low < lo6 : r[0].high > hi6;
   if(!swept) return;
   Cand k;
   ZeroMemory(k);
   k.dir = bias; k.zoneReady = zones[z].ready; k.sweepTime = r[0].time;
   k.ref = bias == 1 ? MathMax(hi6, r[0].high) : MathMin(lo6, r[0].low);
   k.barsLeft = 12; k.swAge = -1;
   int s = ArraySize(cands);
   if(s >= 20) return;
   ArrayResize(cands, s + 1);
   cands[s] = k;
}

// FVG an Kerze r[i] (dritte Kerze), r[i+2] erste Kerze. Ausserdem M5-Extrem seit dem Sweep.
bool CheckFvg(const MqlRates &r[], int i, int c)
{
   int d = cands[c].dir;
   bool ok = d == 1 ? r[i + 2].high < r[i].low : r[i + 2].low > r[i].high;
   if(!ok) return(false);
   cands[c].top = d == 1 ? r[i].low : r[i + 2].low;
   cands[c].bot = d == 1 ? r[i + 2].high : r[i].high;
   double ext = d == 1 ? DBL_MAX : -DBL_MAX;
   for(int j = 0; j < ArraySize(r) && r[j].time >= cands[c].sweepTime; j++)
      if(r[j].time <= r[i].time) ext = d == 1 ? MathMin(ext, r[j].low) : MathMax(ext, r[j].high);
   cands[c].ext5 = ext;
   cands[c].fvgOk = true;
   cands[c].fvgReady = r[i].time + 300;
   cands[c].m1Left = 120;
   return(true);
}

void RemoveCand(int c)
{
   int s = ArraySize(cands);
   for(int i = c; i < s - 1; i++) cands[i] = cands[i + 1];
   ArrayResize(cands, s - 1);
}

//+------------------------------------------------------------------+
//  Fertige M1-Kerze: Einstiegsmodell in der M5-Luecke                 |
//+------------------------------------------------------------------+
void OnM1Bar()
{
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, PERIOD_M1, 1, 20, r) < 20) return;   // r[0] = gerade fertige Kerze
   if(HasOpenPosition()) return;

   for(int c = ArraySize(cands) - 1; c >= 0; c--)
   {
      if(!cands[c].fvgOk || r[0].time < cands[c].fvgReady) continue;
      int d = cands[c].dir;
      cands[c].m1Left--;
      bool dead = cands[c].m1Left < 0 || !InSession(r[0].time)
               || (d == 1 ? r[0].low < cands[c].ext5 : r[0].high > cands[c].ext5);
      if(dead) { RemoveCand(c); continue; }
      if(!cands[c].entered)
      {
         cands[c].entered = d == 1 ? r[0].low <= cands[c].top : r[0].high >= cands[c].bot;
         if(!cands[c].entered) continue;
      }
      if(cands[c].swAge >= 0) { cands[c].swAge++; if(cands[c].swAge > 10) cands[c].swAge = -1; }
      double hi5 = r[1].high, lo5 = r[1].low;
      for(int i = 2; i <= 5; i++) { hi5 = MathMax(hi5, r[i].high); lo5 = MathMin(lo5, r[i].low); }
      bool swept = d == 1 ? r[0].low < lo5 : r[0].high > hi5;
      if(swept)
      {
         if(cands[c].swAge < 0)
         {
            cands[c].swAge = 0;
            cands[c].swRef = d == 1 ? MathMax(hi5, r[0].high) : MathMin(lo5, r[0].low);
            cands[c].swExt = d == 1 ? r[0].low : r[0].high;
         }
         else cands[c].swExt = d == 1 ? MathMin(cands[c].swExt, r[0].low) : MathMax(cands[c].swExt, r[0].high);
         continue;
      }
      if(cands[c].swAge >= 0)
      {
         cands[c].swExt = d == 1 ? MathMin(cands[c].swExt, r[0].low) : MathMax(cands[c].swExt, r[0].high);
         if((r[0].close - cands[c].swRef) * d > 0)
         {
            datetime zr = cands[c].zoneReady;
            if(Enter(d, cands[c].swExt))
            {
               MarkUsed(zr, d);
               ArrayResize(cands, 0);
               return;
            }
            RemoveCand(c);
         }
      }
   }
}

//+------------------------------------------------------------------+
bool Enter(int d, double stop)
{
   if(InpMaxSpreadPts > 0 && SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
   { Print("Kein Einstieg: Spread zu hoch."); return(false); }
   string detail;
   if(CountCorrelated(InpCorrGroup, d, detail) >= InpMaxCorrPos)
   { PrintFormat("Kein Einstieg: schon %d gleichgerichtete Positionen (%s).", InpMaxCorrPos, detail); return(false); }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = d == 1 ? ask : bid;
   double dist  = (entry - stop) * d;
   double spread = ask - bid;
   if(dist <= 3 * spread) { PrintFormat("Kein Einstieg: Stop %.2f naeher als 3x Spread.", dist); return(false); }
   double tp = entry + d * InpRMult * dist;
   double lots = Lots(dist, entry, d == 1);
   if(lots <= 0.0) return(false);
   int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   bool ok = d == 1 ? trade.Buy(lots, _Symbol, 0.0, NormalizeDouble(stop, dg), NormalizeDouble(tp, dg), InpComment)
                    : trade.Sell(lots, _Symbol, 0.0, NormalizeDouble(stop, dg), NormalizeDouble(tp, dg), InpComment);
   PrintFormat("%s %s %.2f Lot @ %.2f, Stop %.2f, Ziel %.2f -> %s", d == 1 ? "LONG" : "SHORT", _Symbol,
               lots, entry, stop, tp, ok ? "ok" : trade.ResultRetcodeDescription());
   return(ok);
}

double Lots(double dist, double entry, bool isLong)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double p = 0.0;
   ENUM_ORDER_TYPE ot = isLong ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcProfit(ot, _Symbol, 1.0, entry, isLong ? entry - dist : entry + dist, p) || p == 0.0) return(0.0);
   double perLot = MathAbs(p);
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) step = 0.01;
   double lots = MathFloor(InpRiskEUR / perLot / step) * step;
   if(lots < minL) lots = minL;
   if(lots > maxL) lots = maxL;
   lots = NormalizeDouble(lots, 2);
   if(perLot * lots > balance * InpMaxRiskPct / 100.0 + 1e-8)
   {
      PrintFormat("Kein Einstieg: %.2f Lot riskieren %.2f und reissen %.1f %%.", lots, perLot * lots, InpMaxRiskPct);
      return(0.0);
   }
   double budget = AccountInfoDouble(ACCOUNT_EQUITY) * InpMarginBuffer - AccountInfoDouble(ACCOUNT_MARGIN);
   double need = 0.0;
   while(lots >= minL - 1e-8)
   {
      if(!OrderCalcMargin(ot, _Symbol, lots, entry, need)) return(0.0);
      if(need <= budget) return(lots);
      lots = NormalizeDouble(lots - step, 2);
   }
   PrintFormat("Kein Einstieg: Margin-Budget %.2f reicht nicht.", budget);
   return(0.0);
}

bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t != 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return(true);
   }
   return(false);
}

void CloseAtSessionEnd()
{
   if(InSession(TimeCurrent())) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t != 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         if(trade.PositionClose(t)) Print("Handelsende 16:00 New York: Position geschlossen.");
   }
}

//+------------------------------------------------------------------+
void OnTick()
{
   CloseAtSessionEnd();
   datetime h1 = iTime(_Symbol, PERIOD_H1, 0);
   if(h1 != lastH1) { lastH1 = h1; RebuildH1(); }
   datetime m5 = iTime(_Symbol, PERIOD_M5, 0);
   if(m5 != lastM5) { lastM5 = m5; OnM5Bar(); }
   datetime m1 = iTime(_Symbol, PERIOD_M1, 0);
   if(m1 != lastM1) { lastM1 = m1; OnM1Bar(); }
}
//+------------------------------------------------------------------+
