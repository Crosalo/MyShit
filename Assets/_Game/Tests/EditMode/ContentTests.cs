using System.Collections.Generic;
using System.Linq;
using Aether.Core;
using NUnit.Framework;

namespace Aether.Tests
{
    public class ContentTests
    {
        [Test]
        public void HeldenSindVollstaendig()
        {
            var ids = new HashSet<string>();
            foreach (var c in GameDatabase.Characters)
            {
                Assert.IsTrue(ids.Add(c.Id), "Doppelte Id " + c.Id);
                Assert.AreEqual(2, c.Skills.Length, c.Id + " braucht genau 2 Fähigkeiten");
                Assert.IsNotNull(c.Ultimate, c.Id + " braucht eine Ultimative");
                foreach (var s in c.Skills)
                    Assert.AreEqual(Balance.MaxCardRank, s.PowerPerRank.Length, s.Id);
            }
            foreach (Rarity r in new[] { Rarity.R, Rarity.SR, Rarity.SSR })
                Assert.IsTrue(GameDatabase.Characters.Any(c => c.Rarity == r), "Keine Helden mit Seltenheit " + r);
        }

        [Test]
        public void FaehigkeitsIdsSindEindeutig()
        {
            var ids = new HashSet<string>();
            foreach (var c in GameDatabase.Characters)
                foreach (var s in c.Skills.Concat(new[] { c.Ultimate }))
                    Assert.IsTrue(ids.Add(s.Id), "Doppelte Fähigkeits-Id " + s.Id);
        }

        [Test]
        public void EtappenVerweisenAufExistierendeGegner()
        {
            Assert.AreEqual(13, GameDatabase.StoryOrder.Count);
            foreach (var stage in GameDatabase.StoryOrder)
            {
                Assert.IsNotEmpty(stage.Waves, stage.Id);
                Assert.IsNotEmpty(stage.Intro, stage.Id + " braucht einen Intro-Dialog");
                foreach (var wave in stage.Waves)
                    foreach (var spawn in wave)
                        Assert.IsNotNull(GameDatabase.FindEnemy(spawn.EnemyId), stage.Id + ": " + spawn.EnemyId);
            }
        }

        [Test]
        public void BannerVerweisenAufExistierendeHelden()
        {
            foreach (var b in GameDatabase.Banners)
            {
                foreach (var id in b.FeaturedIds)
                    Assert.AreEqual(Rarity.SSR, GameDatabase.FindCharacter(id).Rarity, b.Id);
                if (b.GuaranteedId != null) Assert.IsNotNull(GameDatabase.FindCharacter(b.GuaranteedId));
            }
        }

        [Test]
        public void JedesKapitelEndetMitBoss()
        {
            foreach (var ch in GameDatabase.Chapters)
                Assert.IsTrue(ch.Stages.Last().IsBoss, ch.Id);
        }

        /// <summary>
        /// Grober Balance-Check: Ein Team auf passendem Level mit dem SSR aus dem Tutorial
        /// soll jede Etappe mit einer simplen KI meistens schaffen.
        /// </summary>
        [Test]
        public void EtappenSindMitPassendemLevelSchaffbar()
        {
            var report = new List<string>();
            foreach (var stage in GameDatabase.StoryOrder.Skip(1))
            {
                int enemyLevel = stage.Waves.SelectMany(w => w).Max(s => s.Level);
                int level = enemyLevel + 2;
                int wins = 0;
                const int runs = 30;
                for (int seed = 1; seed <= runs; seed++)
                {
                    var profile = ProfileService.CreateNew();
                    ProfileService.AddCharacter(profile, GameDatabase.FindCharacter("kaito"));
                    profile.Team = new List<string> { "kaito", "haru", "nami" };
                    foreach (var c in profile.Characters) c.Level = level;

                    var engine = new BattleEngine(BattleFactory.Create(stage, profile, new SystemRandom(seed)));
                    if (TestFactory.AutoPlay(engine) == BattlePhase.Victory) wins++;
                }
                float rate = wins / (float)runs;
                report.Add(stage.Code + " (Lv " + level + "): " + (int)(rate * 100) + " %");
                Assert.GreaterOrEqual(rate, 0.6f, stage.Code + " ist zu schwer: " + string.Join(", ", report));
            }
            TestContext.WriteLine(string.Join("\n", report));
        }
    }
}
