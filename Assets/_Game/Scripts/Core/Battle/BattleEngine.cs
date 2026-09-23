using System;
using System.Collections.Generic;

namespace Aether.Core
{
    public enum BattlePhase { Planning, Victory, Defeat }

    public enum SlotState { Free, Card, Locked }

    public sealed class ActionSlot
    {
        public SlotState State;
        public SkillCard Card;
        public BattleUnit Target;

        public void Clear()
        {
            State = SlotState.Free;
            Card = null;
            Target = null;
        }
    }

    public enum PlanError
    {
        None,
        NotPlanning,
        NoFreeSlot,
        InvalidIndex,
        OwnerCannotAct,
        UltimateNotReady,
        SamePosition
    }

    public sealed class PlanResult
    {
        public PlanError Error;
        public int SlotIndex = -1;
        public List<MergeInfo> Merges = new List<MergeInfo>();

        public bool Success { get { return Error == PlanError.None; } }

        public static PlanResult Fail(PlanError error) { return new PlanResult { Error = error }; }
    }

    /// <summary>Feste Startkarte, z. B. für das Tutorial.</summary>
    public struct CardSeed
    {
        public int UnitIndex;
        public int SkillIndex;
        public int Rank;

        public CardSeed(int unitIndex, int skillIndex, int rank = 1)
        {
            UnitIndex = unitIndex;
            SkillIndex = skillIndex;
            Rank = rank;
        }
    }

    public sealed class BattleSetup
    {
        public List<BattleUnit> Players = new List<BattleUnit>();
        public List<List<BattleUnit>> Waves = new List<List<BattleUnit>>();
        public IRandom Random;
        public List<CardSeed> InitialHand;
        public int[] InitialGauge;
        public int HandSize = Balance.HandSize;
        public int ActionsPerTurn = Balance.ActionsPerTurn;
    }

    /// <summary>
    /// Rundenbasierter Kartenkampf.
    /// Planungsphase: Pro Runde gibt es <see cref="Balance.ActionsPerTurn"/> Aktionsslots.
    /// Karte einsetzen = Slot mit der Karte belegen. Karte verschieben = Slot wird gesperrt.
    /// Gleiche Nachbarkarten verschmelzen sofort zu einem höheren Rang.
    /// Danach <see cref="ExecuteTurn"/>: Spieleraktionen, Gegnerzug, neue Karten.
    /// </summary>
    public sealed class BattleEngine
    {
        readonly List<BattleUnit> players;
        readonly List<List<BattleUnit>> waves;
        readonly IRandom rng;
        readonly ActionSlot[] slots;

        List<SkillCard> handSnapshot;
        int[] gaugeSnapshot;

        public BattleEngine(BattleSetup setup)
        {
            if (setup.Players.Count == 0) throw new ArgumentException("Keine Spielerhelden");
            if (setup.Waves.Count == 0) throw new ArgumentException("Keine Gegnerwellen");

            players = setup.Players;
            waves = setup.Waves;
            rng = setup.Random ?? new SystemRandom();
            Hand = new CardHand(setup.HandSize);
            slots = new ActionSlot[setup.ActionsPerTurn];
            for (int i = 0; i < slots.Length; i++) slots[i] = new ActionSlot();

            for (int i = 0; i < players.Count; i++) players[i].Index = i;
            foreach (var wave in waves)
                for (int i = 0; i < wave.Count; i++) wave[i].Index = i;

            if (setup.InitialGauge != null)
                for (int i = 0; i < players.Count && i < setup.InitialGauge.Length; i++)
                    players[i].Gauge = Math.Min(Balance.MaxGauge, setup.InitialGauge[i]);

            if (setup.InitialHand != null)
            {
                foreach (var seed in setup.InitialHand)
                {
                    var owner = players[seed.UnitIndex];
                    Hand.Add(new SkillCard(owner, owner.Skills[seed.SkillIndex], seed.Rank));
                }
            }

            Turn = 1;
            Phase = BattlePhase.Planning;
            Refill();
            TakeSnapshot();
        }

        public BattlePhase Phase { get; private set; }
        public int Turn { get; private set; }
        public int WaveIndex { get; private set; }
        public int WaveCount { get { return waves.Count; } }
        public CardHand Hand { get; private set; }
        public IReadOnlyList<BattleUnit> Players { get { return players; } }
        public IReadOnlyList<BattleUnit> Enemies { get { return waves[WaveIndex]; } }
        public IReadOnlyList<ActionSlot> Slots { get { return slots; } }

        public IReadOnlyList<BattleUnit> Wave(int index) { return waves[index]; }

        public int FreeSlotCount
        {
            get
            {
                int n = 0;
                foreach (var s in slots) if (s.State == SlotState.Free) n++;
                return n;
            }
        }

        public bool HasPlannedActions { get { return FreeSlotCount < slots.Length; } }

        public bool CanAct(BattleUnit unit)
        {
            return unit != null && unit.IsAlive && !unit.IsStunned;
        }

        public bool CanUseCard(int handIndex)
        {
            return Phase == BattlePhase.Planning && FreeSlotCount > 0
                && handIndex >= 0 && handIndex < Hand.Count && CanAct(Hand[handIndex].Owner);
        }

        public bool CanUseUltimate(BattleUnit unit)
        {
            return Phase == BattlePhase.Planning && FreeSlotCount > 0 && players.Contains(unit)
                && CanAct(unit) && unit.UltimateReady;
        }

        // ------------------------------------------------------------------ Planung

        public PlanResult UseCard(int handIndex, BattleUnit preferredTarget)
        {
            if (Phase != BattlePhase.Planning) return PlanResult.Fail(PlanError.NotPlanning);
            int slotIndex = NextFreeSlot();
            if (slotIndex < 0) return PlanResult.Fail(PlanError.NoFreeSlot);
            if (handIndex < 0 || handIndex >= Hand.Count) return PlanResult.Fail(PlanError.InvalidIndex);

            var card = Hand[handIndex];
            if (!CanAct(card.Owner)) return PlanResult.Fail(PlanError.OwnerCannotAct);

            Hand.RemoveAt(handIndex);
            var slot = slots[slotIndex];
            slot.State = SlotState.Card;
            slot.Card = card;
            slot.Target = preferredTarget;

            if (card.Owner.Ultimate != null)
                card.Owner.Gauge = Math.Min(Balance.MaxGauge, card.Owner.Gauge + card.Rank);

            return new PlanResult { SlotIndex = slotIndex, Merges = Hand.ResolveMerges() };
        }

        public PlanResult UseUltimate(BattleUnit unit, BattleUnit preferredTarget)
        {
            if (Phase != BattlePhase.Planning) return PlanResult.Fail(PlanError.NotPlanning);
            int slotIndex = NextFreeSlot();
            if (slotIndex < 0) return PlanResult.Fail(PlanError.NoFreeSlot);
            if (!players.Contains(unit) || !CanAct(unit)) return PlanResult.Fail(PlanError.OwnerCannotAct);
            if (!unit.UltimateReady) return PlanResult.Fail(PlanError.UltimateNotReady);

            unit.Gauge = 0;
            var slot = slots[slotIndex];
            slot.State = SlotState.Card;
            slot.Card = new SkillCard(unit, unit.Ultimate, 1, true);
            slot.Target = preferredTarget;
            return new PlanResult { SlotIndex = slotIndex };
        }

        /// <summary>Verschiebt eine Karte. Kostet eine Aktion: Der Slot wird gesperrt.</summary>
        public PlanResult MoveCard(int from, int to)
        {
            if (Phase != BattlePhase.Planning) return PlanResult.Fail(PlanError.NotPlanning);
            int slotIndex = NextFreeSlot();
            if (slotIndex < 0) return PlanResult.Fail(PlanError.NoFreeSlot);
            if (from < 0 || from >= Hand.Count || to < 0 || to >= Hand.Count) return PlanResult.Fail(PlanError.InvalidIndex);
            if (from == to) return PlanResult.Fail(PlanError.SamePosition);

            Hand.Move(from, to);
            slots[slotIndex].State = SlotState.Locked;
            return new PlanResult { SlotIndex = slotIndex, Merges = Hand.ResolveMerges() };
        }

        /// <summary>Macht alle geplanten Aktionen dieser Runde rückgängig.</summary>
        public void ResetPlanning()
        {
            if (Phase != BattlePhase.Planning) return;
            Hand.Restore(handSnapshot);
            for (int i = 0; i < players.Count; i++) players[i].Gauge = gaugeSnapshot[i];
            foreach (var s in slots) s.Clear();
        }

        // ------------------------------------------------------------------ Ausführung

        public List<BattleEvent> ExecuteTurn()
        {
            var ev = new List<BattleEvent>();
            if (Phase != BattlePhase.Planning) return ev;

            foreach (var slot in slots)
            {
                if (slot.State != SlotState.Card) continue;
                var card = slot.Card;
                if (!card.Owner.IsAlive) continue;
                Perform(card.Owner, card.Skill, card.IsUltimate ? 1 : card.Rank, card.IsUltimate, slot.Target, ev);
                if (CheckOutcome(ev)) return ev;
            }

            TickStatuses(players, ev);
            if (Phase != BattlePhase.Planning) return ev;

            EnemyPhase(ev);
            if (Phase != BattlePhase.Planning) return ev;

            TickStatuses(new List<BattleUnit>(Enemies), ev);
            if (Phase != BattlePhase.Planning) return ev;

            Turn++;
            foreach (var s in slots) s.Clear();
            Refill();
            TakeSnapshot();
            ev.Add(new BattleEvent(BattleEventType.TurnStarted) { Turn = Turn });
            return ev;
        }

        /// <summary>Kampf abbrechen (Aufgeben).</summary>
        public void Surrender()
        {
            Phase = BattlePhase.Defeat;
        }

        void EnemyPhase(List<BattleEvent> ev)
        {
            foreach (var enemy in new List<BattleUnit>(Enemies))
            {
                if (Phase != BattlePhase.Planning) return;
                if (!enemy.IsAlive) continue;
                if (enemy.IsStunned)
                {
                    ev.Add(new BattleEvent(BattleEventType.Stunned) { Source = enemy, Target = enemy });
                    continue;
                }

                SkillDefinition skill;
                bool ultimate = false;
                enemy.Gauge++;
                if (enemy.Ultimate != null && enemy.Gauge >= Balance.EnemyUltimateEvery)
                {
                    skill = enemy.Ultimate;
                    ultimate = true;
                    enemy.Gauge = 0;
                }
                else
                {
                    skill = enemy.Skills[rng.Next(enemy.Skills.Length)];
                }

                Perform(enemy, skill, ultimate ? 1 : enemy.SkillRank, ultimate, PickEnemyTarget(), ev);
                CheckOutcome(ev);
            }
        }

        BattleUnit PickEnemyTarget()
        {
            var alive = Alive(players);
            if (alive.Count == 0) return null;
            if (rng.NextFloat() < 0.35f)
            {
                var lowest = alive[0];
                foreach (var p in alive) if (p.HpRatio < lowest.HpRatio) lowest = p;
                return lowest;
            }
            return alive[rng.Next(alive.Count)];
        }

        void Perform(BattleUnit actor, SkillDefinition skill, int rank, bool ultimate, BattleUnit preferred, List<BattleEvent> ev)
        {
            IReadOnlyList<BattleUnit> allies = actor.IsPlayer ? players : Enemies;
            IReadOnlyList<BattleUnit> foes = actor.IsPlayer ? Enemies : players;

            ev.Add(new BattleEvent(BattleEventType.ActionStarted) { Source = actor, Skill = skill, Rank = rank, IsUltimate = ultimate });

            var targets = ResolveTargets(actor, skill.Target, preferred, allies, foes);
            float power = skill.PowerAt(rank);
            if (power > 0f)
            {
                foreach (var t in targets)
                {
                    if (!t.IsAlive) continue;
                    if (skill.IsHeal) Heal(actor, t, power, skill, ev);
                    else DealDamage(actor, t, power, skill, ev);
                }
            }

            foreach (var spec in skill.Effects)
            {
                List<BattleUnit> recipients;
                switch (spec.Target)
                {
                    case EffectTarget.Self: recipients = new List<BattleUnit> { actor }; break;
                    case EffectTarget.AllAllies: recipients = Alive(allies); break;
                    case EffectTarget.AllEnemies: recipients = Alive(foes); break;
                    default: recipients = targets; break;
                }
                foreach (var r in recipients)
                {
                    if (!r.IsAlive) continue;
                    ApplyEffect(actor, spec, rank, r, ev);
                }
            }
        }

        List<BattleUnit> ResolveTargets(BattleUnit actor, TargetType type, BattleUnit preferred,
            IReadOnlyList<BattleUnit> allies, IReadOnlyList<BattleUnit> foes)
        {
            var result = new List<BattleUnit>();
            switch (type)
            {
                case TargetType.SingleEnemy:
                {
                    bool valid = preferred != null && preferred.IsAlive && Contains(foes, preferred);
                    var t = valid ? preferred : FirstAlive(foes);
                    if (t != null) result.Add(t);
                    break;
                }
                case TargetType.AllEnemies:
                    result.AddRange(Alive(foes));
                    break;
                case TargetType.Self:
                    result.Add(actor);
                    break;
                case TargetType.LowestHpAlly:
                {
                    BattleUnit lowest = null;
                    foreach (var a in allies)
                        if (a.IsAlive && (lowest == null || a.HpRatio < lowest.HpRatio)) lowest = a;
                    if (lowest != null) result.Add(lowest);
                    break;
                }
                case TargetType.AllAllies:
                    result.AddRange(Alive(allies));
                    break;
            }
            return result;
        }

        void DealDamage(BattleUnit actor, BattleUnit target, float power, SkillDefinition skill, List<BattleEvent> ev)
        {
            float element = ElementChart.Multiplier(actor.Element, target.Element);
            bool crit = rng.NextFloat() < Balance.CritChance;
            float variance = 0.95f + 0.1f * rng.NextFloat();
            float defense = Balance.DefenseConstant / (Balance.DefenseConstant + target.EffectiveDef);
            float raw = actor.EffectiveAtk * power * defense * element * (crit ? Balance.CritMultiplier : 1f) * variance;
            int damage = Math.Max(1, (int)Math.Round(raw));

            int absorbed = target.AbsorbWithShield(damage);
            int hpLoss = Math.Min(target.Hp, damage - absorbed);
            target.Hp -= hpLoss;

            ev.Add(new BattleEvent(BattleEventType.Damage)
            {
                Source = actor, Target = target, Skill = skill, Amount = hpLoss, Absorbed = absorbed,
                Critical = crit, ElementMultiplier = element
            });

            if (!target.IsAlive) HandleDeath(target, ev);
        }

        void Heal(BattleUnit actor, BattleUnit target, float power, SkillDefinition skill, List<BattleEvent> ev)
        {
            int amount = (int)Math.Round(actor.EffectiveAtk * power);
            int actual = Math.Max(0, Math.Min(amount, target.MaxHp - target.Hp));
            target.Hp += actual;
            ev.Add(new BattleEvent(BattleEventType.Heal) { Source = actor, Target = target, Skill = skill, Amount = actual });
        }

        void ApplyEffect(BattleUnit actor, StatusEffectSpec spec, int rank, BattleUnit target, List<BattleEvent> ev)
        {
            if (rng.NextFloat() >= spec.ChanceAt(rank)) return;

            var effect = new StatusEffect { Type = spec.Type, Value = spec.ValueAt(rank), Remaining = spec.Duration };
            if (spec.Type == StatusType.Burn)
                effect.Amount = Math.Max(1, (int)Math.Round(actor.EffectiveAtk * effect.Value));
            else if (spec.Type == StatusType.Shield)
                effect.Amount = Math.Max(1, (int)Math.Round(actor.MaxHp * effect.Value));

            target.AddStatus(effect);
            ev.Add(new BattleEvent(BattleEventType.StatusApplied)
            {
                Source = actor, Target = target, Status = spec.Type, Amount = effect.Amount
            });
        }

        /// <summary>Statuseffekte laufen am Ende der eigenen Aktionsphase ab; Brand verursacht dann Schaden.</summary>
        void TickStatuses(IReadOnlyList<BattleUnit> units, List<BattleEvent> ev)
        {
            foreach (var unit in units)
            {
                if (!unit.IsAlive) continue;
                foreach (var status in new List<StatusEffect>(unit.Statuses))
                {
                    if (status.Type == StatusType.Burn)
                    {
                        int dmg = Math.Min(unit.Hp, status.Amount);
                        unit.Hp -= dmg;
                        ev.Add(new BattleEvent(BattleEventType.Damage) { Target = unit, Amount = dmg, IsBurn = true, Status = StatusType.Burn });
                        if (!unit.IsAlive)
                        {
                            HandleDeath(unit, ev);
                            break;
                        }
                    }

                    status.Remaining--;
                    if (status.Remaining <= 0)
                    {
                        unit.RemoveStatus(status);
                        ev.Add(new BattleEvent(BattleEventType.StatusExpired) { Target = unit, Status = status.Type });
                    }
                }
            }
            CheckOutcome(ev);
        }

        void HandleDeath(BattleUnit unit, List<BattleEvent> ev)
        {
            unit.ClearStatuses();
            unit.Gauge = 0;
            ev.Add(new BattleEvent(BattleEventType.Death) { Target = unit });
            if (unit.IsPlayer && Hand.RemoveCardsOf(unit) > 0)
                Hand.ResolveMerges();
        }

        /// <summary>Prüft Sieg, Niederlage und Wellenwechsel. true = Kampf vorbei.</summary>
        bool CheckOutcome(List<BattleEvent> ev)
        {
            if (Phase != BattlePhase.Planning) return true;

            if (FirstAlive(players) == null)
            {
                Phase = BattlePhase.Defeat;
                ev.Add(new BattleEvent(BattleEventType.Defeat));
                return true;
            }

            if (FirstAlive(Enemies) == null)
            {
                if (WaveIndex < waves.Count - 1)
                {
                    ev.Add(new BattleEvent(BattleEventType.WaveCleared) { Wave = WaveIndex });
                    WaveIndex++;
                    ev.Add(new BattleEvent(BattleEventType.WaveStarted) { Wave = WaveIndex });
                    return false;
                }
                Phase = BattlePhase.Victory;
                ev.Add(new BattleEvent(BattleEventType.Victory));
                return true;
            }
            return false;
        }

        // ------------------------------------------------------------------ Karten

        void Refill()
        {
            // Mehrere Durchgänge, weil beim Nachziehen Karten verschmelzen und Lücken entstehen können.
            for (int pass = 0; pass < 3 && !Hand.IsFull; pass++)
            {
                while (!Hand.IsFull)
                {
                    var card = Draw();
                    if (card == null) return;
                    Hand.Add(card);
                }
                Hand.ResolveMerges();
            }
        }

        SkillCard Draw()
        {
            var alive = Alive(players);
            if (alive.Count == 0) return null;
            var owner = alive[rng.Next(alive.Count)];
            return new SkillCard(owner, owner.Skills[rng.Next(owner.Skills.Length)], 1);
        }

        void TakeSnapshot()
        {
            handSnapshot = Hand.Snapshot();
            gaugeSnapshot = new int[players.Count];
            for (int i = 0; i < players.Count; i++) gaugeSnapshot[i] = players[i].Gauge;
        }

        int NextFreeSlot()
        {
            for (int i = 0; i < slots.Length; i++)
                if (slots[i].State == SlotState.Free) return i;
            return -1;
        }

        static List<BattleUnit> Alive(IReadOnlyList<BattleUnit> units)
        {
            var list = new List<BattleUnit>();
            foreach (var u in units) if (u.IsAlive) list.Add(u);
            return list;
        }

        static BattleUnit FirstAlive(IReadOnlyList<BattleUnit> units)
        {
            foreach (var u in units) if (u.IsAlive) return u;
            return null;
        }

        static bool Contains(IReadOnlyList<BattleUnit> units, BattleUnit unit)
        {
            foreach (var u in units) if (u == unit) return true;
            return false;
        }
    }
}
