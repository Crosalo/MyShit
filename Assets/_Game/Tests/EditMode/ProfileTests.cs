using System.Linq;
using Aether.Core;
using NUnit.Framework;

namespace Aether.Tests
{
    public class ProfileTests
    {
        [Test]
        public void NeuerSpielstand()
        {
            var p = ProfileService.CreateNew();
            Assert.AreEqual(3, p.Characters.Count);
            CollectionAssert.AreEqual(ProfileService.StarterIds, p.Team);
            Assert.AreEqual(TutorialPhase.Battle, p.Tutorial);
            Assert.AreEqual(Balance.StartGold, p.Gold);
        }

        [Test]
        public void ErfahrungUndLevelaufstieg()
        {
            var c = new OwnedCharacter { Id = "haru" };
            ProfileService.GrantExp(c, Balance.ExpToNext(1));
            Assert.AreEqual(2, c.Level);
            Assert.AreEqual(0, c.Exp);

            ProfileService.GrantExp(c, Balance.ExpToNext(2) + Balance.ExpToNext(3) + 5);
            Assert.AreEqual(4, c.Level);
            Assert.AreEqual(5, c.Exp);
        }

        [Test]
        public void LevelUpMitGold()
        {
            var p = ProfileService.CreateNew();
            int gold = p.Gold;
            Assert.IsTrue(ProfileService.TryLevelUpWithGold(p, "haru"));
            Assert.AreEqual(2, ProfileService.Find(p, "haru").Level);
            Assert.AreEqual(gold - Balance.LevelUpGoldCost(1), p.Gold);

            p.Gold = 0;
            Assert.IsFalse(ProfileService.TryLevelUpWithGold(p, "haru"));
        }

        [Test]
        public void EtappeAbschliessenErstUndWiederholung()
        {
            var p = ProfileService.CreateNew();
            var stage = GameDatabase.Chapters[0].Stages[0];

            var first = ProfileService.CompleteStage(p, stage, p.Team);
            Assert.IsTrue(first.FirstClear);
            Assert.AreEqual(stage.FirstClear.Crystals, p.Crystals);
            Assert.IsTrue(first.LevelUps.Count > 0);

            var again = ProfileService.CompleteStage(p, stage, p.Team);
            Assert.IsFalse(again.FirstClear);
            Assert.AreEqual(stage.Repeat.Gold, again.Gold);
            Assert.AreEqual(stage.FirstClear.Crystals, p.Crystals, "Wiederholung gibt keine Kristalle");
        }

        [Test]
        public void EtappenWerdenNacheinanderFreigeschaltet()
        {
            var p = ProfileService.CreateNew();
            var order = GameDatabase.StoryOrder;
            Assert.IsTrue(ProfileService.IsUnlocked(p, order[0]));
            Assert.IsFalse(ProfileService.IsUnlocked(p, order[1]));

            p.ClearedStages.Add(order[0].Id);
            Assert.IsTrue(ProfileService.IsUnlocked(p, order[1]));
            Assert.IsFalse(ProfileService.IsUnlocked(p, order[2]));
        }

        [Test]
        public void TeamplatzTauschen()
        {
            var p = ProfileService.CreateNew();
            ProfileService.AddCharacter(p, GameDatabase.FindCharacter("kaito"));

            Assert.IsTrue(ProfileService.SetTeamSlot(p, 2, "kaito"));
            CollectionAssert.AreEqual(new[] { "haru", "nami", "kaito" }, p.Team);

            Assert.IsTrue(ProfileService.SetTeamSlot(p, 0, "kaito"));
            CollectionAssert.AreEqual(new[] { "kaito", "nami", "haru" }, p.Team);

            Assert.IsFalse(ProfileService.SetTeamSlot(p, 0, "yuki"), "Nicht besessene Helden gehen nicht");
        }

        [Test]
        public void TaeglicheBelohnung()
        {
            var p = ProfileService.CreateNew();
            Assert.IsFalse(ProfileService.CanClaimDaily(p, 5), "Erst nach dem Tutorial");

            ProfileService.CompleteTutorial(p);
            Assert.AreEqual(Balance.TutorialRewardCrystals, p.Crystals);
            Assert.IsTrue(ProfileService.ClaimDaily(p, 5));
            Assert.IsFalse(ProfileService.ClaimDaily(p, 5));
            Assert.IsTrue(ProfileService.ClaimDaily(p, 6));
        }

        [Test]
        public void KaputtenSpielstandReparieren()
        {
            var p = new PlayerProfile
            {
                Characters = { new OwnedCharacter { Id = "gibtsnicht" }, new OwnedCharacter { Id = "haru", Level = 999 } },
                Team = { "gibtsnicht", "haru", "haru" },
                Crystals = -5
            };
            p.Pity = null;
            ProfileService.Sanitize(p);

            Assert.AreEqual(1, p.Characters.Count);
            Assert.AreEqual(Balance.MaxLevel, p.Characters[0].Level);
            CollectionAssert.AreEqual(new[] { "haru" }, p.Team);
            Assert.AreEqual(0, p.Crystals);
            Assert.IsNotNull(p.Pity);
        }

        [Test]
        public void TeamKampfkraft()
        {
            var p = ProfileService.CreateNew();
            int power = ProfileService.TeamPower(p);
            ProfileService.TryLevelUpWithGold(p, "haru");
            Assert.Greater(ProfileService.TeamPower(p), power);
            Assert.IsTrue(p.Team.All(id => GameDatabase.FindCharacter(id) != null));
        }
    }
}
