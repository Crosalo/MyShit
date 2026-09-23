using System;
using System.Collections;
using System.IO;
using Aether.Core;
using UnityEngine;

namespace Aether.Game
{
    /// <summary>
    /// Einstiegspunkt. Startet sich selbst in jeder Szene (kein Prefab nötig),
    /// lädt den Spielstand und steuert die Abläufe zwischen den Bildschirmen.
    /// </summary>
    public sealed class GameApp : MonoBehaviour
    {
        public static GameApp Instance { get; private set; }

        public PlayerProfile Profile { get; private set; }
        public SaveService Save { get; private set; }
        public UIRoot UI { get; private set; }
        public StageRig Stage { get; private set; }
        public TutorialDirector Tutorial { get; private set; }
        public IRandom Random { get; private set; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (Instance != null || FindFirstObjectByType<GameApp>() != null) return;
            new GameObject("GameApp").AddComponent<GameApp>();
        }

        void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            Application.targetFrameRate = 60;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;

            Random = new SystemRandom();
            Save = new SaveService();
            Profile = Save.Load();
            if (Profile == null)
            {
                Profile = ProfileService.CreateNew();
                Save.Store(Profile);
            }

            Stage = StageRig.Create(transform);
            UI = UIRoot.Create(transform);
            Tutorial = new TutorialDirector(this);
        }

        void Start()
        {
            if (Profile.Tutorial == TutorialPhase.Battle) PlayStage(GameDatabase.Prologue);
            else GoHome();
        }

        void OnApplicationPause(bool paused)
        {
            if (paused) SaveNow();
        }

        void OnApplicationQuit()
        {
            SaveNow();
        }

        public void SaveNow()
        {
            if (Profile != null) Save.Store(Profile);
        }

        /// <summary>Löscht den Spielstand und startet mit dem Prolog neu.</summary>
        public void ResetProfile()
        {
            Profile = ProfileService.CreateNew();
            SaveNow();
            Tutorial.Cancel();
            PlayStage(GameDatabase.Prologue);
        }

        // ------------------------------------------------------------------ Navigation

        public void GoHome()
        {
            Stage.ShowShowcase(Profile.Team.Count > 0 ? Profile.Team[0] : null);
            UI.Show<HomeScreen>();
            Tutorial.Notify(TutorialTrigger.OpenHome);
            Tutorial.OnHomeShown();
        }

        public void GoStory()
        {
            Stage.ShowShowcase(null);
            UI.Show<StoryScreen>();
        }

        public void GoGacha()
        {
            Stage.ShowShowcase(null);
            UI.Show<GachaScreen>();
            Tutorial.Notify(TutorialTrigger.OpenGacha);
        }

        public void GoTeam()
        {
            Stage.ShowShowcase(null);
            UI.Show<TeamScreen>();
            Tutorial.Notify(TutorialTrigger.OpenTeam);
        }

        // ------------------------------------------------------------------ Story-Ablauf

        /// <summary>Intro-Dialog → Kampf → Outro-Dialog → Ergebnis.</summary>
        public void PlayStage(StageDefinition stage)
        {
            StartCoroutine(StageFlow(stage));
        }

        IEnumerator StageFlow(StageDefinition stage)
        {
            Stage.ShowArena(stage);
            UI.Show<BattleScreen>().Prepare(stage);

            bool done = false;
            UI.Dialogue.Play(stage.Intro, () => done = true);
            while (!done) yield return null;

            UI.Get<BattleScreen>().Begin(stage, victory => StartCoroutine(AfterBattle(stage, victory)));
        }

        IEnumerator AfterBattle(StageDefinition stage, bool victory)
        {
            if (!victory)
            {
                Tutorial.Cancel();
                UI.Show<ResultScreen>().ShowDefeat(stage);
                yield break;
            }

            var result = ProfileService.CompleteStage(Profile, stage, BattleFactory.TeamFor(stage, Profile));
            if (stage == GameDatabase.Prologue && Profile.Tutorial == TutorialPhase.Battle)
                Profile.Tutorial = TutorialPhase.Summon;
            SaveNow();

            bool done = false;
            UI.Dialogue.Play(result.FirstClear ? stage.Outro : null, () => done = true);
            while (!done) yield return null;

            UI.Show<ResultScreen>().ShowVictory(stage, result);
        }

        public static int Today()
        {
            return (int)(DateTime.UtcNow - new DateTime(2024, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalDays;
        }
    }

    /// <summary>Speichert den Spielstand als JSON im persistenten Datenordner des Geräts.</summary>
    public sealed class SaveService
    {
        static string FilePath { get { return Path.Combine(Application.persistentDataPath, "profile.json"); } }

        public PlayerProfile Load()
        {
            try
            {
                if (!File.Exists(FilePath)) return null;
                var profile = JsonUtility.FromJson<PlayerProfile>(File.ReadAllText(FilePath));
                if (profile == null) return null;
                ProfileService.Sanitize(profile);
                return profile;
            }
            catch (Exception e)
            {
                Debug.LogWarning("Spielstand konnte nicht geladen werden: " + e.Message);
                return null;
            }
        }

        public void Store(PlayerProfile profile)
        {
            try
            {
                string tmp = FilePath + ".tmp";
                File.WriteAllText(tmp, JsonUtility.ToJson(profile));
                if (File.Exists(FilePath)) File.Delete(FilePath);
                File.Move(tmp, FilePath);
            }
            catch (Exception e)
            {
                Debug.LogError("Spielstand konnte nicht gespeichert werden: " + e.Message);
            }
        }

        public void Delete()
        {
            if (File.Exists(FilePath)) File.Delete(FilePath);
        }
    }
}
