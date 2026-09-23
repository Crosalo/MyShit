using System;
using System.Collections.Generic;

namespace Aether.Core
{
    [Serializable]
    public class PityState
    {
        public string Group;
        public int SinceSsr;
        public int SinceSr;
        public bool FeaturedGuaranteed;
        public int TotalPulls;
    }

    public sealed class GachaPull
    {
        public CharacterDefinition Character;
        public bool IsNew;
        public bool WasFeatured;
        public int LimitBreak;
        public int BonusCrystals;
    }

    /// <summary>
    /// Raten: SSR 3 %, SR 15 %, R 82 %.
    /// Soft-Pity ab Zug 74 (+6 % pro Zug), Hard-Pity bei Zug 90.
    /// Spätestens jeder 10. Zug ist mindestens SR.
    /// Auf Rate-Up-Bannern ist ein SSR zu 50 % der Featured-Held; verliert man das 50/50, ist der nächste SSR garantiert Featured.
    /// </summary>
    public sealed class GachaSystem
    {
        readonly IReadOnlyList<CharacterDefinition> pool;
        readonly IRandom rng;

        public GachaSystem(IReadOnlyList<CharacterDefinition> pool, IRandom rng)
        {
            this.pool = pool;
            this.rng = rng;
        }

        public static float SsrChance(int sinceSsr)
        {
            int n = sinceSsr + 1;
            if (n >= Balance.HardPity) return 1f;
            if (n >= Balance.SoftPityStart)
                return Math.Min(1f, Balance.SsrRate + Balance.SoftPityStep * (n - Balance.SoftPityStart + 1));
            return Balance.SsrRate;
        }

        public CharacterDefinition Roll(BannerDefinition banner, PityState pity, out bool featured)
        {
            featured = false;
            pity.TotalPulls++;

            if (!string.IsNullOrEmpty(banner.GuaranteedId) && pity.TotalPulls == banner.GuaranteedAtPull)
            {
                var guaranteed = Find(banner.GuaranteedId);
                if (guaranteed != null)
                {
                    Track(pity, guaranteed.Rarity);
                    featured = true;
                    return guaranteed;
                }
            }

            float roll = rng.NextFloat();
            float ssr = SsrChance(pity.SinceSsr);
            Rarity rarity;
            if (roll < ssr) rarity = Rarity.SSR;
            else if (pity.SinceSr + 1 >= Balance.SrPity || roll < ssr + Balance.SrRate) rarity = Rarity.SR;
            else rarity = Rarity.R;

            Track(pity, rarity);

            if (rarity == Rarity.SSR && banner.FeaturedIds.Length > 0)
            {
                if (pity.FeaturedGuaranteed || rng.NextFloat() < Balance.FeaturedChance)
                {
                    pity.FeaturedGuaranteed = false;
                    featured = true;
                    return Find(banner.FeaturedIds[rng.Next(banner.FeaturedIds.Length)]);
                }
                pity.FeaturedGuaranteed = true;
                return PickFrom(rarity, banner.FeaturedIds);
            }

            return PickFrom(rarity, null);
        }

        static void Track(PityState pity, Rarity rarity)
        {
            if (rarity == Rarity.SSR)
            {
                pity.SinceSsr = 0;
                pity.SinceSr = 0;
            }
            else if (rarity == Rarity.SR)
            {
                pity.SinceSsr++;
                pity.SinceSr = 0;
            }
            else
            {
                pity.SinceSsr++;
                pity.SinceSr++;
            }
        }

        CharacterDefinition PickFrom(Rarity rarity, string[] exclude)
        {
            var candidates = new List<CharacterDefinition>();
            foreach (var c in pool)
            {
                if (c.Rarity != rarity) continue;
                if (exclude != null && Array.IndexOf(exclude, c.Id) >= 0) continue;
                candidates.Add(c);
            }
            if (candidates.Count == 0)
                foreach (var c in pool) if (c.Rarity == rarity) candidates.Add(c);
            return candidates[rng.Next(candidates.Count)];
        }

        CharacterDefinition Find(string id)
        {
            foreach (var c in pool) if (c.Id == id) return c;
            return null;
        }
    }
}
