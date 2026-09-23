using System;
using System.Collections.Generic;

namespace Aether.Core
{
    public sealed class StatusEffectSpec
    {
        public StatusType Type;
        public EffectTarget Target = EffectTarget.SkillTargets;

        /// <summary>
        /// Stärke je Rang (Index 0 = Rang 1). Bedeutung je Typ:
        /// ANG/VER +/-: Anteil (0.2 = 20 %), Brand: Anteil vom ANG des Verursachers pro Runde,
        /// Schild: Anteil von den max. LP des Verursachers, Betäubung: ohne Bedeutung.
        /// </summary>
        public float[] ValuePerRank = { 0f, 0f, 0f };

        public float[] ChancePerRank = { 1f, 1f, 1f };

        /// <summary>Dauer in eigenen Aktionsphasen des Ziels.</summary>
        public int Duration = 2;

        public float ValueAt(int rank) { return AtRank(ValuePerRank, rank); }
        public float ChanceAt(int rank) { return AtRank(ChancePerRank, rank); }

        internal static float AtRank(float[] values, int rank)
        {
            if (values == null || values.Length == 0) return 0f;
            int i = Math.Max(0, Math.Min(values.Length - 1, rank - 1));
            return values[i];
        }
    }

    public sealed class SkillDefinition
    {
        public string Id;
        public string Name;
        public string Description;
        public TargetType Target;

        /// <summary>Multiplikator auf ANG je Rang, für Schaden oder Heilung. 0 = kein Schaden/keine Heilung.</summary>
        public float[] PowerPerRank = { 1f, 1f, 1f };

        public bool IsHeal;
        public StatusEffectSpec[] Effects = new StatusEffectSpec[0];

        public float PowerAt(int rank) { return StatusEffectSpec.AtRank(PowerPerRank, rank); }

        public bool TargetsEnemies
        {
            get { return Target == TargetType.SingleEnemy || Target == TargetType.AllEnemies; }
        }
    }

    public sealed class CharacterDefinition
    {
        public string Id;
        public string Name;
        public string Title;
        public string Lore;
        public Rarity Rarity;
        public Element Element;
        public Role Role;
        public int BaseHp;
        public int BaseAtk;
        public int BaseDef;

        /// <summary>Genau zwei Fähigkeiten – daraus werden die Kampfkarten gezogen.</summary>
        public SkillDefinition[] Skills;

        public SkillDefinition Ultimate;

        /// <summary>Haarfarbe (Hex), wird für das Platzhalter-Modell und die UI benutzt.</summary>
        public string HairColor = "#FFFFFF";

        /// <summary>Outfitfarbe (Hex).</summary>
        public string OutfitColor = "#333344";

        public string EyeColor = "#4466AA";
    }

    public sealed class EnemyDefinition
    {
        public string Id;
        public string Name;
        public Element Element;
        public int Hp;
        public int Atk;
        public int Def;
        public SkillDefinition[] Skills;

        /// <summary>Optional. Bosse setzen sie alle <see cref="Balance.EnemyUltimateEvery"/> Aktionen ein.</summary>
        public SkillDefinition Ultimate;

        /// <summary>Rang, mit dem der Gegner seine Fähigkeiten einsetzt.</summary>
        public int SkillRank = 1;

        public bool IsBoss;
        public BodyShape Shape = BodyShape.Humanoid;
        public string Color = "#888888";
        public float Scale = 1f;
    }

    public sealed class DialogueLine
    {
        public string Speaker;
        public string Text;

        public DialogueLine(string speaker, string text)
        {
            Speaker = speaker;
            Text = text;
        }
    }

    public sealed class EnemySpawn
    {
        public string EnemyId;
        public int Level;

        public EnemySpawn(string enemyId, int level)
        {
            EnemyId = enemyId;
            Level = level;
        }
    }

    public sealed class Reward
    {
        public int Crystals;
        public int Gold;
        public int Exp;
    }

    public sealed class StageDefinition
    {
        public string Id;
        public string ChapterId;
        public string Code;
        public string Name;
        public string Description;
        public int RecommendedPower;
        public bool IsBoss;
        public List<DialogueLine> Intro = new List<DialogueLine>();
        public List<DialogueLine> Outro = new List<DialogueLine>();
        public List<List<EnemySpawn>> Waves = new List<List<EnemySpawn>>();
        public Reward FirstClear = new Reward();
        public Reward Repeat = new Reward();

        /// <summary>Wenn gesetzt, kämpft genau dieses Team (z. B. im Prolog).</summary>
        public string[] FixedTeam;

        /// <summary>Feste Starthand (Tutorial). Leer = zufällig.</summary>
        public List<CardSeed> InitialHand;

        /// <summary>Start-Ultimativ-Leiste je Teamplatz (Tutorial).</summary>
        public int[] InitialGauge;

        /// <summary>Fester Zufalls-Seed für reproduzierbare Kämpfe. 0 = zufällig.</summary>
        public int Seed;
    }

    public sealed class ChapterDefinition
    {
        public string Id;
        public int Number;
        public string Title;
        public string Summary;
        public List<StageDefinition> Stages = new List<StageDefinition>();
    }

    public sealed class BannerDefinition
    {
        public string Id;
        public string Name;
        public string Subtitle;

        /// <summary>SSR-Helden mit erhöhter Rate (50/50 mit Garantie). Leer = Standard-Banner.</summary>
        public string[] FeaturedIds = new string[0];

        public int CostSingle = Balance.PullCost;
        public int CostMulti = Balance.PullCost * 10;

        /// <summary>Gemeinsamer Pity-Zähler; Banner mit gleicher Gruppe teilen ihn.</summary>
        public string PityGroup;

        /// <summary>Einsteiger-Banner: nur eine Zehnfach-Beschwörung, kostenlos.</summary>
        public bool IsBeginner;

        /// <summary>Dieser Held kommt garantiert beim n-ten Zug des Banners (1-basiert).</summary>
        public string GuaranteedId;
        public int GuaranteedAtPull;

        public string Color = "#7B5CFF";
    }
}
