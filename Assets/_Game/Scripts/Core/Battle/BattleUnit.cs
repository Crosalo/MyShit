using System;
using System.Collections.Generic;

namespace Aether.Core
{
    public sealed class StatusEffect
    {
        public StatusType Type;
        public float Value;

        /// <summary>Feste Menge für Schild (verbleibende Absorption) und Brand (Schaden pro Tick).</summary>
        public int Amount;

        public int Remaining;
    }

    public sealed class BattleUnit
    {
        public readonly string Id;
        public readonly string Name;
        public readonly Element Element;
        public readonly bool IsPlayer;
        public readonly int Level;
        public readonly SkillDefinition[] Skills;
        public readonly SkillDefinition Ultimate;
        public readonly int SkillRank;

        /// <summary>Gesetzt bei Spielerhelden.</summary>
        public readonly CharacterDefinition Character;

        /// <summary>Gesetzt bei Gegnern.</summary>
        public readonly EnemyDefinition Enemy;

        public int Index;
        public int MaxHp;
        public int Hp;
        public int Atk;
        public int Def;
        public int Gauge;

        readonly List<StatusEffect> statuses = new List<StatusEffect>();

        public BattleUnit(CharacterDefinition c, int level, int limitBreak, int index)
        {
            Character = c;
            Id = c.Id;
            Name = c.Name;
            Element = c.Element;
            IsPlayer = true;
            Level = level;
            Skills = c.Skills;
            Ultimate = c.Ultimate;
            SkillRank = 1;
            Index = index;
            MaxHp = Hp = Balance.ScaleStat(c.BaseHp, level, limitBreak);
            Atk = Balance.ScaleStat(c.BaseAtk, level, limitBreak);
            Def = Balance.ScaleStat(c.BaseDef, level, limitBreak);
        }

        public BattleUnit(EnemyDefinition e, int level, int index)
        {
            Enemy = e;
            Id = e.Id;
            Name = e.Name;
            Element = e.Element;
            IsPlayer = false;
            Level = level;
            Skills = e.Skills;
            Ultimate = e.Ultimate;
            SkillRank = e.SkillRank;
            Index = index;
            float m = Balance.EnemyLevelMultiplier(level);
            MaxHp = Hp = (int)Math.Round(e.Hp * m);
            Atk = (int)Math.Round(e.Atk * m);
            Def = (int)Math.Round(e.Def * m);
        }

        public bool IsAlive { get { return Hp > 0; } }
        public bool IsStunned { get { return Has(StatusType.Stun); } }
        public bool UltimateReady { get { return Ultimate != null && Gauge >= Balance.MaxGauge; } }
        public float HpRatio { get { return MaxHp <= 0 ? 0f : (float)Hp / MaxHp; } }
        public IReadOnlyList<StatusEffect> Statuses { get { return statuses; } }

        public int ShieldAmount
        {
            get
            {
                var s = Find(StatusType.Shield);
                return s == null ? 0 : s.Amount;
            }
        }

        public float EffectiveAtk
        {
            get { return Atk * Modifier(StatusType.AttackUp, StatusType.AttackDown); }
        }

        public float EffectiveDef
        {
            get { return Def * Modifier(StatusType.DefenseUp, StatusType.DefenseDown); }
        }

        public bool Has(StatusType type) { return Find(type) != null; }

        public StatusEffect Find(StatusType type)
        {
            for (int i = 0; i < statuses.Count; i++)
                if (statuses[i].Type == type) return statuses[i];
            return null;
        }

        /// <summary>Gleiche Effekte stapeln nicht: der stärkere Wert und die längere Dauer gewinnen.</summary>
        public void AddStatus(StatusEffect effect)
        {
            var existing = Find(effect.Type);
            if (existing == null)
            {
                statuses.Add(effect);
                return;
            }
            existing.Value = Math.Max(existing.Value, effect.Value);
            existing.Amount = Math.Max(existing.Amount, effect.Amount);
            existing.Remaining = Math.Max(existing.Remaining, effect.Remaining);
        }

        public void RemoveStatus(StatusEffect effect) { statuses.Remove(effect); }

        public void ClearStatuses() { statuses.Clear(); }

        /// <summary>Zieht Schaden zuerst vom Schild ab. Gibt den absorbierten Anteil zurück.</summary>
        public int AbsorbWithShield(int damage)
        {
            var shield = Find(StatusType.Shield);
            if (shield == null) return 0;
            int absorbed = Math.Min(shield.Amount, damage);
            shield.Amount -= absorbed;
            if (shield.Amount <= 0) statuses.Remove(shield);
            return absorbed;
        }

        float Modifier(StatusType up, StatusType down)
        {
            float m = 1f;
            var u = Find(up);
            if (u != null) m += u.Value;
            var d = Find(down);
            if (d != null) m -= d.Value;
            return Math.Max(Balance.MinStatMultiplier, m);
        }

        public override string ToString() { return Name + " (" + Hp + "/" + MaxHp + ")"; }
    }
}
