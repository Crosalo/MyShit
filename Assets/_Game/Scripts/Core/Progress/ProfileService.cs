using System;
using System.Collections.Generic;

namespace Aether.Core
{
    public sealed class LevelUpInfo
    {
        public string CharacterId;
        public int From;
        public int To;
    }

    public sealed class StageResult
    {
        public bool FirstClear;
        public int Crystals;
        public int Gold;
        public int Exp;
        public List<LevelUpInfo> LevelUps = new List<LevelUpInfo>();
    }

    public sealed class SummonResult
    {
        public string Error;
        public List<GachaPull> Pulls = new List<GachaPull>();
        public bool Success { get { return Error == null; } }
    }

    /// <summary>Alle Regeln, die den Spielstand verändern.</summary>
    public static class ProfileService
    {
        public const int TeamSize = 3;

        public static readonly string[] StarterIds = { "haru", "nami", "kenta" };

        public static PlayerProfile CreateNew()
        {
            var p = new PlayerProfile { Gold = Balance.StartGold };
            foreach (var id in StarterIds)
            {
                p.Characters.Add(new OwnedCharacter { Id = id });
                p.Team.Add(id);
            }
            return p;
        }

        /// <summary>Repariert geladene Spielstände (fehlende Listen, unbekannte Helden, kaputtes Team).</summary>
        public static void Sanitize(PlayerProfile p)
        {
            if (p.Characters == null) p.Characters = new List<OwnedCharacter>();
            if (p.Team == null) p.Team = new List<string>();
            if (p.ClearedStages == null) p.ClearedStages = new List<string>();
            if (p.Pity == null) p.Pity = new List<PityState>();

            p.Characters.RemoveAll(c => c == null || GameDatabase.FindCharacter(c.Id) == null);
            foreach (var c in p.Characters)
            {
                c.Level = Math.Max(1, Math.Min(Balance.MaxLevel, c.Level));
                c.LimitBreak = Math.Max(0, Math.Min(Balance.MaxLimitBreak, c.LimitBreak));
                c.Exp = Math.Max(0, c.Exp);
            }
            if (p.Characters.Count == 0)
                foreach (var id in StarterIds) p.Characters.Add(new OwnedCharacter { Id = id });

            var team = new List<string>();
            foreach (var id in p.Team)
                if (Find(p, id) != null && !team.Contains(id) && team.Count < TeamSize) team.Add(id);
            for (int i = 0; team.Count < Math.Min(TeamSize, p.Characters.Count) && i < p.Characters.Count; i++)
                if (!team.Contains(p.Characters[i].Id)) team.Add(p.Characters[i].Id);
            p.Team = team;

            p.Crystals = Math.Max(0, p.Crystals);
            p.Gold = Math.Max(0, p.Gold);
        }

        public static OwnedCharacter Find(PlayerProfile p, string id)
        {
            foreach (var c in p.Characters) if (c.Id == id) return c;
            return null;
        }

        public static GachaPull AddCharacter(PlayerProfile p, CharacterDefinition def)
        {
            var owned = Find(p, def.Id);
            var pull = new GachaPull { Character = def };
            if (owned == null)
            {
                p.Characters.Add(new OwnedCharacter { Id = def.Id });
                pull.IsNew = true;
            }
            else if (owned.LimitBreak < Balance.MaxLimitBreak)
            {
                owned.LimitBreak++;
                pull.LimitBreak = owned.LimitBreak;
            }
            else
            {
                pull.LimitBreak = owned.LimitBreak;
                pull.BonusCrystals = Balance.DuplicateCrystals(def.Rarity);
                p.Crystals += pull.BonusCrystals;
            }
            return pull;
        }

        // ------------------------------------------------------------------ Gacha

        public static PityState GetPity(PlayerProfile p, BannerDefinition banner)
        {
            string group = string.IsNullOrEmpty(banner.PityGroup) ? banner.Id : banner.PityGroup;
            foreach (var s in p.Pity) if (s.Group == group) return s;
            var state = new PityState { Group = group };
            p.Pity.Add(state);
            return state;
        }

        public static bool BeginnerUsed(PlayerProfile p, BannerDefinition banner)
        {
            return banner.IsBeginner && GetPity(p, banner).TotalPulls > 0;
        }

        public static int Cost(BannerDefinition banner, int count)
        {
            if (banner.IsBeginner) return 0;
            return count >= 10 ? banner.CostMulti : banner.CostSingle * count;
        }

        public static string CheckSummon(PlayerProfile p, BannerDefinition banner, int count)
        {
            if (count != 1 && count != 10) return "Ungültige Anzahl";
            if (banner.IsBeginner)
            {
                if (count != 10) return "Nur Zehnfach-Beschwörung möglich";
                if (BeginnerUsed(p, banner)) return "Bereits eingelöst";
                return null;
            }
            if (p.Crystals < Cost(banner, count)) return "Nicht genug Kristalle";
            return null;
        }

        public static SummonResult Summon(PlayerProfile p, BannerDefinition banner, int count, GachaSystem gacha)
        {
            var result = new SummonResult { Error = CheckSummon(p, banner, count) };
            if (!result.Success) return result;

            p.Crystals -= Cost(banner, count);
            var pity = GetPity(p, banner);
            for (int i = 0; i < count; i++)
            {
                bool featured;
                var def = gacha.Roll(banner, pity, out featured);
                var pull = AddCharacter(p, def);
                pull.WasFeatured = featured;
                result.Pulls.Add(pull);
            }
            return result;
        }

        // ------------------------------------------------------------------ Story

        public static bool IsCleared(PlayerProfile p, string stageId)
        {
            return p.ClearedStages.Contains(stageId);
        }

        public static bool IsUnlocked(PlayerProfile p, StageDefinition stage)
        {
            var order = GameDatabase.StoryOrder;
            int index = order.IndexOf(stage);
            if (index <= 0) return true;
            return IsCleared(p, order[index - 1].Id);
        }

        public static StageResult CompleteStage(PlayerProfile p, StageDefinition stage, IList<string> teamIds)
        {
            var result = new StageResult { FirstClear = !IsCleared(p, stage.Id) };
            var reward = result.FirstClear ? stage.FirstClear : stage.Repeat;
            result.Crystals = reward.Crystals;
            result.Gold = reward.Gold;
            result.Exp = reward.Exp;

            p.Crystals += reward.Crystals;
            p.Gold += reward.Gold;
            p.BattlesWon++;
            if (result.FirstClear) p.ClearedStages.Add(stage.Id);

            foreach (var id in teamIds)
            {
                var owned = Find(p, id);
                if (owned == null) continue;
                int before = owned.Level;
                GrantExp(owned, reward.Exp);
                if (owned.Level > before)
                    result.LevelUps.Add(new LevelUpInfo { CharacterId = id, From = before, To = owned.Level });
            }
            return result;
        }

        public static void GrantExp(OwnedCharacter c, int exp)
        {
            if (c.Level >= Balance.MaxLevel) return;
            c.Exp += exp;
            while (c.Level < Balance.MaxLevel && c.Exp >= Balance.ExpToNext(c.Level))
            {
                c.Exp -= Balance.ExpToNext(c.Level);
                c.Level++;
            }
            if (c.Level >= Balance.MaxLevel) c.Exp = 0;
        }

        public static bool TryLevelUpWithGold(PlayerProfile p, string id)
        {
            var c = Find(p, id);
            if (c == null || c.Level >= Balance.MaxLevel) return false;
            int cost = Balance.LevelUpGoldCost(c.Level);
            if (p.Gold < cost) return false;
            p.Gold -= cost;
            c.Level++;
            c.Exp = 0;
            return true;
        }

        // ------------------------------------------------------------------ Team

        /// <summary>Setzt einen Helden in einen Teamslot. Ist er schon im Team, tauschen die beiden die Plätze.</summary>
        public static bool SetTeamSlot(PlayerProfile p, int slot, string id)
        {
            if (slot < 0 || slot >= TeamSize || Find(p, id) == null) return false;
            while (p.Team.Count <= slot) p.Team.Add(null);

            int existing = p.Team.IndexOf(id);
            if (existing == slot) return false;
            if (existing >= 0) p.Team[existing] = p.Team[slot];
            p.Team[slot] = id;
            p.Team.RemoveAll(t => t == null);
            return true;
        }

        public static int TeamPower(PlayerProfile p)
        {
            int power = 0;
            foreach (var id in p.Team)
            {
                var owned = Find(p, id);
                var def = GameDatabase.FindCharacter(id);
                if (owned != null && def != null) power += Balance.Power(def, owned.Level, owned.LimitBreak);
            }
            return power;
        }

        // ------------------------------------------------------------------ Belohnungen

        public static bool CanClaimDaily(PlayerProfile p, int day)
        {
            return p.Tutorial == TutorialPhase.Done && day > p.LastDailyClaimDay;
        }

        public static bool ClaimDaily(PlayerProfile p, int day)
        {
            if (!CanClaimDaily(p, day)) return false;
            p.LastDailyClaimDay = day;
            p.Crystals += Balance.DailyCrystals;
            p.Gold += Balance.DailyGold;
            return true;
        }

        public static void CompleteTutorial(PlayerProfile p)
        {
            if (p.Tutorial == TutorialPhase.Done) return;
            p.Tutorial = TutorialPhase.Done;
            p.Crystals += Balance.TutorialRewardCrystals;
        }
    }
}
