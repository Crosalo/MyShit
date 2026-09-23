using System.Linq;
using Aether.Core;
using NUnit.Framework;

namespace Aether.Tests
{
    /// <summary>Gibt die Werte der Reihe nach zurück und beginnt dann von vorn.</summary>
    public sealed class SequenceRandom : IRandom
    {
        readonly float[] values;
        int index;
        public SequenceRandom(params float[] values) { this.values = values; }
        public float NextFloat() { return values[index++ % values.Length]; }
        public int Next(int maxExclusive) { return 0; }
    }

    public class GachaTests
    {
        static BannerDefinition Standard { get { return GameDatabase.Banners.First(b => b.Id == "standard"); } }
        static BannerDefinition Dawn { get { return GameDatabase.Banners.First(b => b.Id == "dawn"); } }

        [Test]
        public void Raten()
        {
            Assert.AreEqual(0.03f, GachaSystem.SsrChance(0), 0.0001f);
            Assert.AreEqual(0.03f, GachaSystem.SsrChance(72), 0.0001f);
            Assert.AreEqual(0.09f, GachaSystem.SsrChance(73), 0.0001f, "Soft-Pity beginnt bei Zug 74");
            Assert.AreEqual(1f, GachaSystem.SsrChance(89), 0.0001f, "Zug 90 ist garantiert");
        }

        [Test]
        public void HardPityBeiZug90UndSrAlle10Zuege()
        {
            var gacha = new GachaSystem(GameDatabase.Characters, new FixedRandom(0.995f));
            var pity = new PityState();
            bool featured;
            for (int i = 1; i <= 90; i++)
            {
                var c = gacha.Roll(Standard, pity, out featured);
                if (i == 90) Assert.AreEqual(Rarity.SSR, c.Rarity);
                else if (i >= Balance.SoftPityStart) Assert.AreNotEqual(Rarity.SSR, c.Rarity, "Zug " + i);
                else if (i % 10 == 0) Assert.AreEqual(Rarity.SR, c.Rarity, "Zug " + i);
                else Assert.AreEqual(Rarity.R, c.Rarity, "Zug " + i);
            }
            Assert.AreEqual(0, pity.SinceSsr);
        }

        [Test]
        public void FiftyFiftyVerlorenDannGarantie()
        {
            // 0.01 → SSR, 0.9 → 50/50 verloren
            var gacha = new GachaSystem(GameDatabase.Characters, new SequenceRandom(0.01f, 0.9f));
            var pity = new PityState();
            bool featured;
            var first = gacha.Roll(Dawn, pity, out featured);

            Assert.AreEqual(Rarity.SSR, first.Rarity);
            Assert.IsFalse(featured);
            CollectionAssert.DoesNotContain(Dawn.FeaturedIds, first.Id);
            Assert.IsTrue(pity.FeaturedGuaranteed);

            gacha = new GachaSystem(GameDatabase.Characters, new FixedRandom(0.01f));
            var second = gacha.Roll(Dawn, pity, out featured);
            Assert.IsTrue(featured);
            CollectionAssert.Contains(Dawn.FeaturedIds, second.Id);
            Assert.IsFalse(pity.FeaturedGuaranteed);
        }

        [Test]
        public void KostenUndKristalle()
        {
            var profile = ProfileService.CreateNew();
            profile.Crystals = 1600;
            var gacha = new GachaSystem(GameDatabase.Characters, new SystemRandom(3));

            Assert.IsTrue(ProfileService.Summon(profile, Standard, 10, gacha).Success);
            Assert.AreEqual(0, profile.Crystals);
            Assert.AreEqual("Nicht genug Kristalle", ProfileService.Summon(profile, Standard, 1, gacha).Error);
        }

        [Test]
        public void EinsteigerBannerNurEinmal()
        {
            var profile = ProfileService.CreateNew();
            var beginner = GameDatabase.Banners.First(b => b.IsBeginner);
            var gacha = new GachaSystem(GameDatabase.Characters, new SystemRandom(3));

            Assert.IsNotNull(ProfileService.CheckSummon(profile, beginner, 1));
            Assert.IsTrue(ProfileService.Summon(profile, beginner, 10, gacha).Success);
            Assert.AreEqual(0, profile.Crystals);
            Assert.IsFalse(ProfileService.Summon(profile, beginner, 10, gacha).Success);
        }

        [Test]
        public void DuplikateGebenDurchbruchDannKristalle()
        {
            var profile = ProfileService.CreateNew();
            var kaito = GameDatabase.FindCharacter("kaito");

            Assert.IsTrue(ProfileService.AddCharacter(profile, kaito).IsNew);
            for (int i = 1; i <= Balance.MaxLimitBreak; i++)
                Assert.AreEqual(i, ProfileService.AddCharacter(profile, kaito).LimitBreak);

            var extra = ProfileService.AddCharacter(profile, kaito);
            Assert.AreEqual(Balance.DuplicateCrystals(Rarity.SSR), extra.BonusCrystals);
            Assert.AreEqual(extra.BonusCrystals, profile.Crystals);
        }

        [Test]
        public void VerteilungUngefaehrWieAngegeben()
        {
            var gacha = new GachaSystem(GameDatabase.Characters, new SystemRandom(42));
            var pity = new PityState();
            int ssr = 0, sr = 0;
            const int n = 20000;
            bool featured;
            for (int i = 0; i < n; i++)
            {
                var r = gacha.Roll(Standard, pity, out featured).Rarity;
                if (r == Rarity.SSR) ssr++;
                else if (r == Rarity.SR) sr++;
            }
            // Effektive Raten inkl. Pity liegen etwas über den Basisraten.
            Assert.That(ssr / (float)n, Is.InRange(0.03f, 0.08f));
            Assert.That(sr / (float)n, Is.InRange(0.14f, 0.25f));
        }
    }
}
