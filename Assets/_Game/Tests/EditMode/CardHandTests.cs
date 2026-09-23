using Aether.Core;
using NUnit.Framework;

namespace Aether.Tests
{
    public class CardHandTests
    {
        BattleUnit unitA;
        BattleUnit unitB;

        [SetUp]
        public void SetUp()
        {
            unitA = new BattleUnit(TestFactory.Hero("a"), 1, 0, 0);
            unitB = new BattleUnit(TestFactory.Hero("b"), 1, 0, 1);
        }

        CardHand Hand(params SkillCard[] cards)
        {
            var hand = new CardHand(7);
            foreach (var c in cards) hand.Add(c);
            return hand;
        }

        SkillCard A(int rank = 1) { return new SkillCard(unitA, unitA.Skills[0], rank); }
        SkillCard A2(int rank = 1) { return new SkillCard(unitA, unitA.Skills[1], rank); }
        SkillCard B(int rank = 1) { return new SkillCard(unitB, unitB.Skills[0], rank); }

        [Test]
        public void GleicheNachbarnVerschmelzenZuRang2()
        {
            var hand = Hand(A(), A(), B());
            var merges = hand.ResolveMerges();

            Assert.AreEqual(1, merges.Count);
            Assert.AreEqual(2, hand.Count);
            Assert.AreEqual(2, hand[0].Rank);
            Assert.AreEqual(unitB, hand[1].Owner);
        }

        [Test]
        public void UnterschiedlicheFaehigkeitVerschmilztNicht()
        {
            var hand = Hand(A(), A2(), B());
            Assert.AreEqual(0, hand.ResolveMerges().Count);
            Assert.AreEqual(3, hand.Count);
        }

        [Test]
        public void UnterschiedlicherRangVerschmilztNicht()
        {
            var hand = Hand(A(1), A(2));
            Assert.AreEqual(0, hand.ResolveMerges().Count);
        }

        [Test]
        public void KettenVerschmelzungBisRang3()
        {
            // R1 + R1 → R2, direkt daneben liegt ein R2 → R3
            var hand = Hand(A(1), A(1), A(2));
            var merges = hand.ResolveMerges();

            Assert.AreEqual(2, merges.Count);
            Assert.AreEqual(1, hand.Count);
            Assert.AreEqual(3, hand[0].Rank);
        }

        [Test]
        public void Rang3VerschmilztNichtWeiter()
        {
            var hand = Hand(A(3), A(3));
            Assert.AreEqual(0, hand.ResolveMerges().Count);
            Assert.AreEqual(2, hand.Count);
        }

        [Test]
        public void VerschiebenErmoeglichtVerschmelzen()
        {
            var hand = Hand(A(), B(), A());
            hand.Move(2, 1);
            var merges = hand.ResolveMerges();

            Assert.AreEqual(1, merges.Count);
            Assert.AreEqual(2, hand[0].Rank);
            Assert.AreEqual(unitB, hand[1].Owner);
        }

        [Test]
        public void EntfernenDerMittlerenKarteVerschmilztNachbarn()
        {
            var hand = Hand(A(), B(), A());
            hand.RemoveAt(1);
            hand.ResolveMerges();

            Assert.AreEqual(1, hand.Count);
            Assert.AreEqual(2, hand[0].Rank);
        }

        [Test]
        public void SnapshotUndRestore()
        {
            var hand = Hand(A(), B());
            var snap = hand.Snapshot();
            hand.RemoveAt(0);
            hand.Restore(snap);

            Assert.AreEqual(2, hand.Count);
            Assert.AreEqual(unitA, hand[0].Owner);
        }
    }
}
