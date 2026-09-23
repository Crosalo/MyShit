using System.Collections.Generic;

namespace Aether.Core
{
    /// <summary>Zentraler Zugriff auf alle Spielinhalte.</summary>
    public static class GameDatabase
    {
        static List<CharacterDefinition> characters;
        static List<EnemyDefinition> enemies;
        static List<ChapterDefinition> chapters;
        static List<BannerDefinition> banners;
        static List<StageDefinition> storyOrder;
        static StageDefinition prologue;
        static Dictionary<string, CharacterDefinition> characterById;
        static Dictionary<string, EnemyDefinition> enemyById;
        static Dictionary<string, StageDefinition> stageById;

        public static IReadOnlyList<CharacterDefinition> Characters { get { Init(); return characters; } }
        public static IReadOnlyList<EnemyDefinition> Enemies { get { Init(); return enemies; } }
        public static IReadOnlyList<ChapterDefinition> Chapters { get { Init(); return chapters; } }
        public static IReadOnlyList<BannerDefinition> Banners { get { Init(); return banners; } }
        public static StageDefinition Prologue { get { Init(); return prologue; } }

        /// <summary>Alle Etappen in Spielreihenfolge, beginnend mit dem Prolog.</summary>
        public static List<StageDefinition> StoryOrder { get { Init(); return storyOrder; } }

        public static CharacterDefinition FindCharacter(string id)
        {
            Init();
            CharacterDefinition c;
            return id != null && characterById.TryGetValue(id, out c) ? c : null;
        }

        public static EnemyDefinition FindEnemy(string id)
        {
            Init();
            EnemyDefinition e;
            return id != null && enemyById.TryGetValue(id, out e) ? e : null;
        }

        public static StageDefinition FindStage(string id)
        {
            Init();
            StageDefinition s;
            return id != null && stageById.TryGetValue(id, out s) ? s : null;
        }

        public static ChapterDefinition FindChapter(string id)
        {
            Init();
            foreach (var c in chapters) if (c.Id == id) return c;
            return null;
        }

        static void Init()
        {
            if (characters != null) return;

            characters = CharacterContent.All();
            enemies = EnemyContent.All();
            chapters = StoryContent.Chapters();
            prologue = StoryContent.Prologue();
            banners = BannerContent.All();

            characterById = new Dictionary<string, CharacterDefinition>();
            foreach (var c in characters) characterById.Add(c.Id, c);
            enemyById = new Dictionary<string, EnemyDefinition>();
            foreach (var e in enemies) enemyById.Add(e.Id, e);

            storyOrder = new List<StageDefinition> { prologue };
            foreach (var ch in chapters) storyOrder.AddRange(ch.Stages);
            stageById = new Dictionary<string, StageDefinition>();
            foreach (var s in storyOrder) stageById.Add(s.Id, s);
        }
    }

    public static class BannerContent
    {
        public const string BeginnerId = "beginner";

        public static List<BannerDefinition> All()
        {
            return new List<BannerDefinition>
            {
                new BannerDefinition
                {
                    Id = BeginnerId, Name = "Einsteiger-Beschwörung",
                    Subtitle = "Einmalig & kostenlos: 10 Helden, darunter garantiert Kaito (SSR)!",
                    IsBeginner = true, GuaranteedId = "kaito", GuaranteedAtPull = 10,
                    PityGroup = "beginner", Color = "#FF9F43"
                },
                new BannerDefinition
                {
                    Id = "dawn", Name = "Flammen der Morgenröte",
                    Subtitle = "Erhöhte Rate: Kaito Hayabusa & Ren Kurogane",
                    FeaturedIds = new[] { "kaito", "ren" }, PityGroup = "event", Color = "#FF5A3C"
                },
                new BannerDefinition
                {
                    Id = "frost", Name = "Gesang von Eis und Sternen",
                    Subtitle = "Erhöhte Rate: Yuki Shirogane & Aiko Hoshino",
                    FeaturedIds = new[] { "yuki", "aiko" }, PityGroup = "event", Color = "#3CA0FF"
                },
                new BannerDefinition
                {
                    Id = "standard", Name = "Sternenruf",
                    Subtitle = "Standard-Beschwörung mit allen Helden",
                    PityGroup = "standard", Color = "#7B5CFF"
                }
            };
        }
    }
}
