using System.Collections.Generic;
using Aether.Core;

namespace Aether.Tests
{
    /// <summary>Liefert immer denselben Wert – für vorhersagbare Tests.</summary>
    public sealed class FixedRandom : IRandom
    {
        public float Value;
        public FixedRandom(float value) { Value = value; }
        public float NextFloat() { return Value; }
        public int Next(int maxExclusive) { return 0; }
    }

    public static class TestFactory
    {
        public static SkillDefinition Strike(string id = "strike", float power = 1f, TargetType target = TargetType.SingleEnemy)
        {
            return Sk.Attack(id, id, target, power, power * 1.5f, power * 2.3f, "");
        }

        public static CharacterDefinition Hero(string id, int atk = 100, Element element = Element.Fire)
        {
            return new CharacterDefinition
            {
                Id = id, Name = id, Rarity = Rarity.R, Element = element, Role = Role.Attacker,
                BaseHp = 1000, BaseAtk = atk, BaseDef = 50,
                Skills = new[] { Strike(id + "_a"), Strike(id + "_b", 0.5f, TargetType.AllEnemies) },
                Ultimate = Sk.Ultimate(id + "_u", id + " Ult", TargetType.AllEnemies, 3f, "")
            };
        }

        public static EnemyDefinition Dummy(string id = "dummy", int hp = 500, int atk = 10, Element element = Element.Fire)
        {
            return new EnemyDefinition
            {
                Id = id, Name = id, Element = element, Hp = hp, Atk = atk, Def = 0,
                Skills = new[] { Strike(id + "_hit") }
            };
        }

        /// <summary>Kampf mit drei Test-Helden und einer Welle.</summary>
        public static BattleEngine Battle(IRandom rng, List<CardSeed> hand = null, int enemyHp = 500, int waves = 1, int[] gauge = null)
        {
            var setup = new BattleSetup { Random = rng, InitialHand = hand, InitialGauge = gauge };
            setup.Players.Add(new BattleUnit(Hero("a"), 1, 0, 0));
            setup.Players.Add(new BattleUnit(Hero("b"), 1, 0, 1));
            setup.Players.Add(new BattleUnit(Hero("c"), 1, 0, 2));
            for (int w = 0; w < waves; w++)
                setup.Waves.Add(new List<BattleUnit> { new BattleUnit(Dummy("d" + w, enemyHp), 1, 0) });
            return new BattleEngine(setup);
        }

        /// <summary>Einfache KI: Ultimativ wenn bereit, sonst die Karten mit dem höchsten Rang.</summary>
        public static void AutoPlanTurn(BattleEngine engine)
        {
            while (engine.FreeSlotCount > 0 && engine.Phase == BattlePhase.Planning)
            {
                BattleUnit ultUnit = null;
                foreach (var p in engine.Players)
                    if (engine.CanUseUltimate(p)) { ultUnit = p; break; }
                if (ultUnit != null)
                {
                    engine.UseUltimate(ultUnit, null);
                    continue;
                }

                int best = -1;
                for (int i = 0; i < engine.Hand.Count; i++)
                {
                    if (!engine.CanUseCard(i)) continue;
                    if (best < 0 || engine.Hand[i].Rank > engine.Hand[best].Rank) best = i;
                }
                if (best < 0) break;
                engine.UseCard(best, null);
            }
        }

        public static BattlePhase AutoPlay(BattleEngine engine, int maxTurns = 60)
        {
            for (int t = 0; t < maxTurns && engine.Phase == BattlePhase.Planning; t++)
            {
                AutoPlanTurn(engine);
                engine.ExecuteTurn();
            }
            return engine.Phase;
        }
    }
}
