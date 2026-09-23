namespace Aether.Core
{
    /// <summary>Elemente. Kreislauf: Wasser &gt; Feuer &gt; Wind &gt; Erde &gt; Wasser. Licht und Dunkel sind gegenseitig effektiv.</summary>
    public enum Element { Fire, Water, Wind, Earth, Light, Dark }

    public enum Rarity { R = 1, SR = 2, SSR = 3 }

    public enum Role { Attacker, Defender, Support, Healer }

    public enum TargetType
    {
        SingleEnemy,
        AllEnemies,
        Self,
        LowestHpAlly,
        AllAllies
    }

    public enum StatusType { AttackUp, DefenseUp, AttackDown, DefenseDown, Burn, Stun, Shield }

    /// <summary>Wen ein Statuseffekt trifft.</summary>
    public enum EffectTarget
    {
        /// <summary>Dieselben Ziele wie der Angriff/die Heilung der Fähigkeit.</summary>
        SkillTargets,
        Self,
        AllAllies,
        AllEnemies
    }

    /// <summary>Form des Platzhalter-Modells, solange kein echtes 3D-Modell hinterlegt ist.</summary>
    public enum BodyShape { Humanoid, Slime, Beast, Golem, Wisp }

    public static class ElementChart
    {
        public const float Advantage = 1.5f;
        public const float Disadvantage = 0.75f;

        public static bool Beats(Element attacker, Element defender)
        {
            switch (attacker)
            {
                case Element.Water: return defender == Element.Fire;
                case Element.Fire: return defender == Element.Wind;
                case Element.Wind: return defender == Element.Earth;
                case Element.Earth: return defender == Element.Water;
                case Element.Light: return defender == Element.Dark;
                case Element.Dark: return defender == Element.Light;
                default: return false;
            }
        }

        public static float Multiplier(Element attacker, Element defender)
        {
            if (Beats(attacker, defender)) return Advantage;
            if (Beats(defender, attacker)) return Disadvantage;
            return 1f;
        }
    }

    public static class Names
    {
        public static string Of(Element e)
        {
            switch (e)
            {
                case Element.Fire: return "Feuer";
                case Element.Water: return "Wasser";
                case Element.Wind: return "Wind";
                case Element.Earth: return "Erde";
                case Element.Light: return "Licht";
                default: return "Dunkel";
            }
        }

        public static string Of(Role r)
        {
            switch (r)
            {
                case Role.Attacker: return "Angreifer";
                case Role.Defender: return "Verteidiger";
                case Role.Support: return "Unterstützer";
                default: return "Heiler";
            }
        }

        public static string Short(StatusType s)
        {
            switch (s)
            {
                case StatusType.AttackUp: return "ANG+";
                case StatusType.DefenseUp: return "VER+";
                case StatusType.AttackDown: return "ANG-";
                case StatusType.DefenseDown: return "VER-";
                case StatusType.Burn: return "BRAND";
                case StatusType.Stun: return "BETÄUBT";
                default: return "SCHILD";
            }
        }

        public static string RankLabel(int rank)
        {
            return rank >= 3 ? "★★★" : rank == 2 ? "★★" : "★";
        }
    }
}
