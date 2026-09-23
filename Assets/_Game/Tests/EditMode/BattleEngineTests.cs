using System.Collections.Generic;
using System.Linq;
using Aether.Core;
using NUnit.Framework;

namespace Aether.Tests
{
    public class BattleEngineTests
    {
        // a=0, b=1, c=2 | Fähigkeit 0 oder 1 – gleicher Aufbau wie im Prolog-Tutorial
        static List<CardSeed> TutorialLikeHand()
        {
            return new List<CardSeed>
            {
                new CardSeed(0, 0), new CardSeed(1, 0), new CardSeed(0, 0), new CardSeed(2, 0),
                new CardSeed(1, 1), new CardSeed(2, 1), new CardSeed(2, 0)
            };
        }

        [Test]
        public void KarteEinsetzenBelegtSlotLaedtLeisteUndVerschmilztNachbarn()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand());
            var result = engine.UseCard(1, null);

            Assert.IsTrue(result.Success);
            Assert.AreEqual(SlotState.Card, engine.Slots[0].State);
            Assert.AreEqual(1, result.Merges.Count, "Die beiden a-Karten müssen verschmelzen");
            Assert.AreEqual(2, engine.Hand[0].Rank);
            Assert.AreEqual(5, engine.Hand.Count);
            Assert.AreEqual(1, engine.Players[1].Gauge);
        }

        [Test]
        public void VerschiebenSperrtSlot()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand());
            var result = engine.MoveCard(6, 4);

            Assert.IsTrue(result.Success);
            Assert.AreEqual(SlotState.Locked, engine.Slots[0].State);
            Assert.AreEqual(1, result.Merges.Count);
            Assert.AreEqual(6, engine.Hand.Count);
            Assert.AreEqual(2, engine.FreeSlotCount);
        }

        [Test]
        public void VerschiebenAufGleichePositionIstUngueltig()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand());
            Assert.AreEqual(PlanError.SamePosition, engine.MoveCard(2, 2).Error);
            Assert.AreEqual(3, engine.FreeSlotCount);
        }

        [Test]
        public void NachDreiAktionenIstKeinSlotMehrFrei()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand());
            Assert.IsTrue(engine.UseCard(0, null).Success);
            Assert.IsTrue(engine.MoveCard(0, 2).Success);
            Assert.IsTrue(engine.UseCard(0, null).Success);

            Assert.AreEqual(0, engine.FreeSlotCount);
            Assert.AreEqual(PlanError.NoFreeSlot, engine.UseCard(0, null).Error);
            Assert.AreEqual(PlanError.NoFreeSlot, engine.MoveCard(0, 1).Error);
        }

        [Test]
        public void ZuruecksetzenStelltHandUndLeisteWiederHer()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand());
            engine.UseCard(1, null);
            engine.MoveCard(3, 1);
            engine.ResetPlanning();

            Assert.AreEqual(7, engine.Hand.Count);
            Assert.AreEqual(1, engine.Hand[0].Rank);
            Assert.AreEqual(0, engine.Players[1].Gauge);
            Assert.AreEqual(3, engine.FreeSlotCount);
        }

        [Test]
        public void RundeAusfuehrenMachtSchadenUndFuelltHandAuf()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand(), enemyHp: 5000);
            engine.UseCard(0, null);
            var events = engine.ExecuteTurn();

            Assert.IsTrue(events.Any(e => e.Type == BattleEventType.Damage && !e.Target.IsPlayer));
            Assert.IsTrue(events.Any(e => e.Type == BattleEventType.Damage && e.Target.IsPlayer), "Gegner greift an");
            Assert.AreEqual(BattleEventType.TurnStarted, events.Last().Type);
            Assert.AreEqual(2, engine.Turn);
            Assert.AreEqual(3, engine.FreeSlotCount);
            Assert.Less(engine.Enemies[0].Hp, 5000);
            Assert.Greater(engine.Hand.Count, 0);
        }

        [Test]
        public void SchadensformelOhneZufall()
        {
            // ANG 100 × Kraft 1 × (200 / (200 + 0 VER)) × Element 1 × Varianz 1.0 = 100
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand(), enemyHp: 5000);
            engine.UseCard(0, null);
            var events = engine.ExecuteTurn();
            var hit = events.First(e => e.Type == BattleEventType.Damage && !e.Target.IsPlayer);
            Assert.AreEqual(100, hit.Amount);
        }

        [Test]
        public void UltimativBrauchtVolleLeiste()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand(), gauge: new[] { Balance.MaxGauge, 0, 0 });

            Assert.IsTrue(engine.CanUseUltimate(engine.Players[0]));
            Assert.IsTrue(engine.UseUltimate(engine.Players[0], null).Success);
            Assert.AreEqual(0, engine.Players[0].Gauge);
            Assert.IsTrue(engine.Slots[0].Card.IsUltimate);
            Assert.AreEqual(PlanError.UltimateNotReady, engine.UseUltimate(engine.Players[1], null).Error);
        }

        [Test]
        public void SiegWennAlleGegnerBesiegt()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand(), enemyHp: 1);
            engine.UseCard(0, null);
            var events = engine.ExecuteTurn();

            Assert.AreEqual(BattlePhase.Victory, engine.Phase);
            Assert.AreEqual(BattleEventType.Victory, events.Last().Type);
        }

        [Test]
        public void NaechsteWelleNachBesiegterWelle()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand(), enemyHp: 1, waves: 2);
            engine.UseCard(0, null);
            engine.UseCard(0, null);
            var events = engine.ExecuteTurn();

            Assert.IsTrue(events.Any(e => e.Type == BattleEventType.WaveCleared));
            Assert.IsTrue(events.Any(e => e.Type == BattleEventType.WaveStarted && e.Wave == 1));
            Assert.AreEqual(BattlePhase.Victory, engine.Phase);
        }

        [Test]
        public void BetaeubterGegnerSetztAus()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand(), enemyHp: 5000);
            engine.Enemies[0].AddStatus(new StatusEffect { Type = StatusType.Stun, Remaining = 1 });
            var events = engine.ExecuteTurn();

            Assert.IsTrue(events.Any(e => e.Type == BattleEventType.Stunned));
            Assert.IsFalse(events.Any(e => e.Type == BattleEventType.Damage && e.Target.IsPlayer));
            Assert.IsFalse(engine.Enemies[0].IsStunned, "Betäubung läuft am Ende der Gegnerphase ab");
        }

        [Test]
        public void BrandVerursachtSchadenAmEndeDerPhase()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand(), enemyHp: 5000);
            var enemy = engine.Enemies[0];
            enemy.AddStatus(new StatusEffect { Type = StatusType.Burn, Amount = 50, Remaining = 2 });
            engine.ExecuteTurn();

            Assert.AreEqual(4950, enemy.Hp);
            Assert.AreEqual(1, enemy.Find(StatusType.Burn).Remaining);
        }

        [Test]
        public void SchildFaengtSchadenAb()
        {
            var unit = new BattleUnit(TestFactory.Hero("x"), 1, 0, 0);
            unit.AddStatus(new StatusEffect { Type = StatusType.Shield, Amount = 30, Remaining = 2 });

            Assert.AreEqual(30, unit.AbsorbWithShield(100));
            Assert.IsFalse(unit.Has(StatusType.Shield));
        }

        [Test]
        public void BetaeubterHeldKannKeineKartenNutzen()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand());
            engine.Players[0].AddStatus(new StatusEffect { Type = StatusType.Stun, Remaining = 1 });

            Assert.IsFalse(engine.CanUseCard(0));
            Assert.AreEqual(PlanError.OwnerCannotAct, engine.UseCard(0, null).Error);
            Assert.IsTrue(engine.MoveCard(0, 1).Success, "Verschieben geht trotzdem");
        }

        [Test]
        public void KartenBesiegterHeldenVerschwinden()
        {
            // 0.1 → Gegner zielt auf den Helden mit den wenigsten LP
            var setup = new BattleSetup { Random = new FixedRandom(0.1f), InitialHand = TutorialLikeHand() };
            setup.Players.Add(new BattleUnit(TestFactory.Hero("a"), 1, 0, 0));
            setup.Players.Add(new BattleUnit(TestFactory.Hero("b"), 1, 0, 1));
            setup.Players.Add(new BattleUnit(TestFactory.Hero("c"), 1, 0, 2));
            setup.Waves.Add(new List<BattleUnit> { new BattleUnit(TestFactory.Dummy("boss", 9999, 500), 1, 0) });
            var engine = new BattleEngine(setup);
            var b = engine.Players[1];
            b.Hp = 1;

            engine.ExecuteTurn();

            Assert.IsFalse(b.IsAlive);
            Assert.IsFalse(engine.Hand.Cards.Any(c => c.Owner == b));
            Assert.AreEqual(BattlePhase.Planning, engine.Phase);
        }

        [Test]
        public void NiederlageWennAlleHeldenFallen()
        {
            var engine = TestFactory.Battle(new FixedRandom(0.5f), TutorialLikeHand());
            foreach (var p in engine.Players) p.Hp = 1;
            engine.Enemies[0].Atk = 5000;
            for (int i = 0; i < 5 && engine.Phase == BattlePhase.Planning; i++) engine.ExecuteTurn();

            Assert.AreEqual(BattlePhase.Defeat, engine.Phase);
        }

        [Test]
        public void Elementvorteile()
        {
            Assert.AreEqual(1.5f, ElementChart.Multiplier(Element.Water, Element.Fire));
            Assert.AreEqual(1.5f, ElementChart.Multiplier(Element.Fire, Element.Wind));
            Assert.AreEqual(1.5f, ElementChart.Multiplier(Element.Wind, Element.Earth));
            Assert.AreEqual(1.5f, ElementChart.Multiplier(Element.Earth, Element.Water));
            Assert.AreEqual(1.5f, ElementChart.Multiplier(Element.Light, Element.Dark));
            Assert.AreEqual(1.5f, ElementChart.Multiplier(Element.Dark, Element.Light));
            Assert.AreEqual(0.75f, ElementChart.Multiplier(Element.Fire, Element.Water));
            Assert.AreEqual(1f, ElementChart.Multiplier(Element.Fire, Element.Earth));
        }

        [Test]
        public void StatusStapeltNichtSondernNimmtDenStaerkeren()
        {
            var unit = new BattleUnit(TestFactory.Hero("x"), 1, 0, 0);
            unit.AddStatus(new StatusEffect { Type = StatusType.AttackUp, Value = 0.2f, Remaining = 1 });
            unit.AddStatus(new StatusEffect { Type = StatusType.AttackUp, Value = 0.1f, Remaining = 3 });

            Assert.AreEqual(1, unit.Statuses.Count);
            Assert.AreEqual(0.2f, unit.Find(StatusType.AttackUp).Value, 0.0001f);
            Assert.AreEqual(3, unit.Find(StatusType.AttackUp).Remaining);
            Assert.AreEqual(120f, unit.EffectiveAtk, 0.01f);
        }
    }
}
