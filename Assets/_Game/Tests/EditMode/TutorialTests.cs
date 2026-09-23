using System.Linq;
using Aether.Core;
using NUnit.Framework;

namespace Aether.Tests
{
    public class TutorialTests
    {
        static BattleEngine PrologueBattle(int seed)
        {
            var stage = GameDatabase.Prologue;
            var setup = BattleFactory.Create(stage, ProfileService.CreateNew(), null);
            if (seed != 0) setup.Random = new SystemRandom(seed);
            return new BattleEngine(setup);
        }

        /// <summary>Spielt die geskripteten Tutorialschritte genau so, wie das UI sie erlaubt.</summary>
        static void PlayScriptedSteps(BattleEngine engine)
        {
            var steps = TutorialScript.Battle();
            var use = steps.First(s => s.Id == "battle_use");
            var move = steps.First(s => s.Id == "battle_move");
            var useRank2 = steps.First(s => s.Id == "battle_use_rank2");

            var r1 = engine.UseCard(use.HandIndex, null);
            Assert.IsTrue(r1.Success);
            Assert.AreEqual(1, r1.Merges.Count, "Schritt 'Karte einsetzen' muss eine Verschmelzung auslösen");
            Assert.AreEqual("haru", engine.Hand[0].Owner.Id);
            Assert.AreEqual(2, engine.Hand[0].Rank);

            foreach (var target in move.MoveTargets)
                Assert.IsTrue(TutorialScript.Allows(move, TutorialAction.MoveCard, move.HandIndex, target));

            var r2 = engine.MoveCard(move.HandIndex, move.MoveTargets[0]);
            Assert.IsTrue(r2.Success);
            Assert.AreEqual(1, r2.Merges.Count, "Schritt 'Verschieben' muss eine Verschmelzung auslösen");
            Assert.AreEqual(SlotState.Locked, engine.Slots[1].State);

            var r3 = engine.UseCard(useRank2.HandIndex, null);
            Assert.IsTrue(r3.Success);
            Assert.AreEqual(2, engine.Slots[2].Card.Rank);
            Assert.AreEqual(0, engine.FreeSlotCount);

            var haru = engine.Players[0];
            Assert.AreEqual(Balance.MaxGauge, haru.Gauge, "Harus Ultimativ-Leiste muss nach Schritt 'Rang-2 einsetzen' voll sein");

            engine.ExecuteTurn();
            Assert.AreEqual(BattlePhase.Planning, engine.Phase, "Der Kampf darf in Runde 1 noch nicht vorbei sein");
            Assert.IsTrue(engine.CanUseUltimate(haru));
            Assert.IsTrue(engine.UseUltimate(haru, null).Success);
        }

        [Test]
        public void PrologFunktioniertMitFestemSeed()
        {
            var engine = PrologueBattle(0);
            PlayScriptedSteps(engine);
            Assert.AreEqual(BattlePhase.Victory, TestFactory.AutoPlay(engine));
            Assert.IsTrue(engine.Players.All(p => p.IsAlive), "Im Tutorial soll niemand sterben");
        }

        [Test]
        public void PrologFunktioniertAuchMitAnderenSeeds([Range(1, 40)] int seed)
        {
            var engine = PrologueBattle(seed);
            PlayScriptedSteps(engine);
            Assert.AreEqual(BattlePhase.Victory, TestFactory.AutoPlay(engine));
        }

        [Test]
        public void GesperrteAktionenImTutorial()
        {
            var steps = TutorialScript.Battle();
            var use = steps.First(s => s.Id == "battle_use");
            Assert.IsTrue(TutorialScript.Allows(use, TutorialAction.UseCard, 1));
            Assert.IsFalse(TutorialScript.Allows(use, TutorialAction.UseCard, 0));
            Assert.IsFalse(TutorialScript.Allows(use, TutorialAction.MoveCard, 1, 2));
            Assert.IsFalse(TutorialScript.Allows(use, TutorialAction.Execute));

            var move = steps.First(s => s.Id == "battle_move");
            Assert.IsFalse(TutorialScript.Allows(move, TutorialAction.MoveCard, 4, 5));

            var free = steps.Last();
            Assert.IsTrue(TutorialScript.Allows(free, TutorialAction.MoveCard, 3, 0));
            Assert.IsTrue(TutorialScript.AllowsButton(null, "egal"));
        }

        [Test]
        public void ButtonsImBeschwoerungsTutorial()
        {
            var open = TutorialScript.Summon().First();
            Assert.IsTrue(TutorialScript.AllowsButton(open, "home.gacha"));
            Assert.IsFalse(TutorialScript.AllowsButton(open, "home.story"));
            Assert.IsFalse(TutorialScript.AllowsButton(open, null));
        }

        [Test]
        public void EinsteigerBannerGarantiertDenTutorialHelden()
        {
            var profile = ProfileService.CreateNew();
            var banner = GameDatabase.Banners.First(b => b.IsBeginner);
            var gacha = new GachaSystem(GameDatabase.Characters, new SystemRandom(7));
            var result = ProfileService.Summon(profile, banner, 10, gacha);

            Assert.IsTrue(result.Success);
            Assert.IsTrue(result.Pulls.Any(p => p.Character.Id == "kaito"));
            Assert.IsNotNull(ProfileService.Find(profile, "kaito"));
        }
    }
}
