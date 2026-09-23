using System;

namespace Aether.Core
{
    /// <summary>Alle Zahlen zum Feintuning an einem Ort.</summary>
    public static class Balance
    {
        // Kampf
        public const int HandSize = 7;
        public const int ActionsPerTurn = 3;
        public const int MaxCardRank = 3;
        public const int MaxGauge = 5;
        public const int EnemyUltimateEvery = 3;
        public const float DefenseConstant = 200f;
        public const float CritChance = 0.1f;
        public const float CritMultiplier = 1.5f;
        public const float MinStatMultiplier = 0.3f;

        // Fortschritt
        public const int MaxLevel = 50;
        public const int MaxLimitBreak = 5;

        // Gacha
        public const int PullCost = 160;
        public const float SsrRate = 0.03f;
        public const float SrRate = 0.15f;
        public const int SoftPityStart = 74;
        public const float SoftPityStep = 0.06f;
        public const int HardPity = 90;
        public const int SrPity = 10;
        public const float FeaturedChance = 0.5f;

        // Belohnungen
        public const int TutorialRewardCrystals = 1600;
        public const int DailyCrystals = 100;
        public const int DailyGold = 2000;
        public const int StartGold = 5000;

        public static float LevelMultiplier(int level)
        {
            return 1f + 0.06f * (Math.Max(1, level) - 1);
        }

        public static float LimitBreakMultiplier(int limitBreak)
        {
            return 1f + 0.08f * Math.Max(0, limitBreak);
        }

        public static int ScaleStat(int baseValue, int level, int limitBreak)
        {
            return (int)Math.Round(baseValue * LevelMultiplier(level) * LimitBreakMultiplier(limitBreak));
        }

        public static float EnemyLevelMultiplier(int level)
        {
            return 1f + 0.07f * (Math.Max(1, level) - 1);
        }

        public static int ExpToNext(int level)
        {
            return 100 + 40 * (Math.Max(1, level) - 1);
        }

        public static int LevelUpGoldCost(int level)
        {
            return 150 * Math.Max(1, level);
        }

        /// <summary>Kampfkraft eines Helden, nur als Orientierung für die UI.</summary>
        public static int Power(CharacterDefinition c, int level, int limitBreak)
        {
            int hp = ScaleStat(c.BaseHp, level, limitBreak);
            int atk = ScaleStat(c.BaseAtk, level, limitBreak);
            int def = ScaleStat(c.BaseDef, level, limitBreak);
            return hp / 5 + atk * 3 + def * 2;
        }

        /// <summary>Kristalle für Duplikate, wenn der Held schon voll durchgebrochen ist.</summary>
        public static int DuplicateCrystals(Rarity rarity)
        {
            switch (rarity)
            {
                case Rarity.SSR: return 80;
                case Rarity.SR: return 20;
                default: return 5;
            }
        }
    }
}
