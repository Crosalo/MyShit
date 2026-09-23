namespace Aether.Core
{
    public enum BattleEventType
    {
        TurnStarted,
        ActionStarted,
        Damage,
        Heal,
        StatusApplied,
        StatusExpired,
        Stunned,
        Death,
        WaveCleared,
        WaveStarted,
        Victory,
        Defeat
    }

    /// <summary>
    /// Was in einer Runde passiert ist, in Reihenfolge. Die Engine rechnet alles sofort aus;
    /// die Darstellung spielt die Ereignisse danach mit Animationen ab.
    /// </summary>
    public sealed class BattleEvent
    {
        public BattleEventType Type;
        public BattleUnit Source;
        public BattleUnit Target;
        public SkillDefinition Skill;
        public int Rank;
        public bool IsUltimate;

        /// <summary>Tatsächlicher LP-Verlust bzw. -Gewinn.</summary>
        public int Amount;

        /// <summary>Vom Schild abgefangener Schaden.</summary>
        public int Absorbed;

        public bool Critical;
        public float ElementMultiplier = 1f;
        public bool IsBurn;
        public StatusType Status;
        public int Wave;
        public int Turn;

        public BattleEvent(BattleEventType type)
        {
            Type = type;
        }

        public override string ToString()
        {
            return Type + " " + (Source != null ? Source.Name : "-") + " -> " + (Target != null ? Target.Name : "-") + " " + Amount;
        }
    }
}
