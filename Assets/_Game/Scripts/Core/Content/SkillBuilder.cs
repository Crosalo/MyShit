namespace Aether.Core
{
    /// <summary>Kurzschreibweise für Fähigkeiten in den Inhaltsdateien.</summary>
    public static class Sk
    {
        public static SkillDefinition Attack(string id, string name, TargetType target, float r1, float r2, float r3,
            string description, params StatusEffectSpec[] effects)
        {
            return new SkillDefinition
            {
                Id = id, Name = name, Target = target, Description = description,
                PowerPerRank = new[] { r1, r2, r3 }, Effects = effects
            };
        }

        public static SkillDefinition Heal(string id, string name, TargetType target, float r1, float r2, float r3,
            string description, params StatusEffectSpec[] effects)
        {
            var s = Attack(id, name, target, r1, r2, r3, description, effects);
            s.IsHeal = true;
            return s;
        }

        /// <summary>Fähigkeit ohne Schaden/Heilung, nur mit Effekten.</summary>
        public static SkillDefinition Support(string id, string name, TargetType target, string description,
            params StatusEffectSpec[] effects)
        {
            return Attack(id, name, target, 0f, 0f, 0f, description, effects);
        }

        public static SkillDefinition Ultimate(string id, string name, TargetType target, float power,
            string description, params StatusEffectSpec[] effects)
        {
            return Attack(id, name, target, power, power, power, description, effects);
        }

        public static SkillDefinition UltimateHeal(string id, string name, TargetType target, float power,
            string description, params StatusEffectSpec[] effects)
        {
            var s = Ultimate(id, name, target, power, description, effects);
            s.IsHeal = true;
            return s;
        }

        public static StatusEffectSpec Fx(StatusType type, EffectTarget target, float r1, float r2, float r3, int duration = 2)
        {
            return new StatusEffectSpec
            {
                Type = type, Target = target, Duration = duration,
                ValuePerRank = new[] { r1, r2, r3 }
            };
        }

        public static StatusEffectSpec Fx(StatusType type, EffectTarget target, float value, int duration = 2)
        {
            return Fx(type, target, value, value, value, duration);
        }

        public static StatusEffectSpec Chance(this StatusEffectSpec spec, float r1, float r2, float r3)
        {
            spec.ChancePerRank = new[] { r1, r2, r3 };
            return spec;
        }

        public static StatusEffectSpec Chance(this StatusEffectSpec spec, float chance)
        {
            return spec.Chance(chance, chance, chance);
        }
    }
}
