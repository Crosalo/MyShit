using System;
using System.Collections;
using System.Collections.Generic;
using Aether.Core;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Aether.Game
{
    /// <summary>Farbstimmung je Kapitel.</summary>
    public struct ArenaTheme
    {
        public Color SkyTop, SkyHorizon, SkyBottom, Ground, GroundEdge, Accent, Light;
        public int Props; // 0 Schrein, 1 Wald, 2 Hafen, 3 Feuer

        public static ArenaTheme For(string chapterId)
        {
            switch (chapterId)
            {
                case "ch1":
                    return new ArenaTheme { SkyTop = Theme.Hex("#3A7BD5"), SkyHorizon = Theme.Hex("#B8F0D8"), SkyBottom = Theme.Hex("#2E4A3A"),
                        Ground = Theme.Hex("#6DBB6A"), GroundEdge = Theme.Hex("#4B8A4C"), Accent = Theme.Hex("#9CFFB0"), Light = Theme.Hex("#FFF4DC"), Props = 1 };
                case "ch2":
                    return new ArenaTheme { SkyTop = Theme.Hex("#2B3A67"), SkyHorizon = Theme.Hex("#A9B8D6"), SkyBottom = Theme.Hex("#1C2440"),
                        Ground = Theme.Hex("#7B8BA8"), GroundEdge = Theme.Hex("#56637D"), Accent = Theme.Hex("#8FD3FF"), Light = Theme.Hex("#DDE8FF"), Props = 2 };
                case "ch3":
                    return new ArenaTheme { SkyTop = Theme.Hex("#2A0E1E"), SkyHorizon = Theme.Hex("#FF7A45"), SkyBottom = Theme.Hex("#1A0A0A"),
                        Ground = Theme.Hex("#5A3A36"), GroundEdge = Theme.Hex("#3A2422"), Accent = Theme.Hex("#FF9F43"), Light = Theme.Hex("#FFD2B0"), Props = 3 };
                default:
                    return new ArenaTheme { SkyTop = Theme.Hex("#5B4BB7"), SkyHorizon = Theme.Hex("#FFB6C8"), SkyBottom = Theme.Hex("#3A2E5A"),
                        Ground = Theme.Hex("#E8D6C0"), GroundEdge = Theme.Hex("#B89E86"), Accent = Theme.Hex("#FF4F8B"), Light = Theme.Hex("#FFE9E0"), Props = 0 };
            }
        }
    }

    /// <summary>Kamera, Licht, Himmel und die beiden 3D-Szenen: Präsentation im Hauptmenü und Kampfarena.</summary>
    public sealed class StageRig : MonoBehaviour
    {
        Camera cam;
        Light sun;
        Transform showcaseRoot;
        Transform arenaRoot;
        Transform environment;
        string showcaseId;
        Coroutine shake;

        public Camera Camera { get { return cam; } }
        public BattleArena Arena { get; private set; }

        public static StageRig Create(Transform parent)
        {
            var go = new GameObject("Stage");
            go.transform.SetParent(parent, false);
            var rig = go.AddComponent<StageRig>();

            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            camGo.transform.SetParent(go.transform, false);
            rig.cam = camGo.AddComponent<Camera>();
            rig.cam.clearFlags = CameraClearFlags.Skybox;
            rig.cam.backgroundColor = Theme.Background;
            rig.cam.nearClipPlane = 0.1f;
            rig.cam.farClipPlane = 200f;
            rig.cam.allowHDR = false;
            camGo.AddComponent<PhysicsRaycaster>();

            var sunGo = new GameObject("Sonne");
            sunGo.transform.SetParent(go.transform, false);
            sunGo.transform.rotation = Quaternion.Euler(42f, -35f, 0f);
            rig.sun = sunGo.AddComponent<Light>();
            rig.sun.type = LightType.Directional;
            rig.sun.shadows = LightShadows.Hard;
            rig.sun.shadowStrength = 0.55f;
            rig.sun.intensity = 1.05f;

            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.65f);
            QualitySettings.shadowDistance = 30f;

            rig.showcaseRoot = new GameObject("Showcase").transform;
            rig.showcaseRoot.SetParent(go.transform, false);
            rig.arenaRoot = new GameObject("Arena").transform;
            rig.arenaRoot.SetParent(go.transform, false);
            rig.Arena = rig.arenaRoot.gameObject.AddComponent<BattleArena>();
            rig.Arena.Init(rig);
            rig.ApplyTheme(ArenaTheme.For("ch0"));
            return rig;
        }

        // ------------------------------------------------------------------ Hauptmenü

        /// <summary>Zeigt einen Helden auf einer Plattform. null = nur Hintergrund.</summary>
        public void ShowShowcase(string characterId)
        {
            Arena.Clear();
            arenaRoot.gameObject.SetActive(false);
            showcaseRoot.gameObject.SetActive(true);
            ApplyTheme(ArenaTheme.For("ch0"));
            BuildEnvironment(ArenaTheme.For("ch0"), false);

            cam.fieldOfView = 30f;
            cam.transform.position = new Vector3(0.6f, 1.55f, -5.4f);
            cam.transform.LookAt(new Vector3(0.6f, 1.05f, 0f));

            if (characterId == showcaseId && showcaseRoot.childCount > 0) return;
            showcaseId = characterId;
            showcaseRoot.ClearChildren();

            var def = GameDatabase.FindCharacter(characterId);
            if (def == null) return;

            var platform = CharacterModels.Part(showcaseRoot, PrimitiveType.Cylinder, "Plattform",
                new Vector3(-0.9f, 0.05f, 0), new Vector3(2.2f, 0.05f, 2.2f), Theme.Of(def.Element), null, 0.002f, 0.35f);
            platform.transform.SetParent(showcaseRoot, true);

            var model = CharacterModels.CreateHero(def);
            model.transform.SetParent(showcaseRoot, false);
            model.transform.localPosition = new Vector3(-0.9f, 0.1f, 0);
            model.transform.localRotation = Quaternion.Euler(0, 160f, 0);
            model.AddComponent<IdleSway>();

            var sparkles = new GameObject("Funkeln").transform;
            sparkles.SetParent(showcaseRoot, false);
            sparkles.localPosition = new Vector3(-0.9f, 0, 0);
            for (int i = 0; i < 8; i++)
            {
                float a = i * Mathf.PI * 2f / 8f;
                var s = CharacterModels.Part(sparkles, PrimitiveType.Cube, "Funke",
                    new Vector3(Mathf.Cos(a) * 1.3f, 0.6f + (i % 3) * 0.5f, Mathf.Sin(a) * 1.3f),
                    Vector3.one * 0.08f, Theme.Of(def.Element), new Vector3(45, 45, 0), 0f, 1f);
                s.AddComponent<Spin>().Speed = 90f;
            }
            sparkles.gameObject.AddComponent<Spin>().Speed = 12f;
        }

        // ------------------------------------------------------------------ Kampf

        public void ShowArena(StageDefinition stage)
        {
            showcaseRoot.gameObject.SetActive(false);
            showcaseId = null;
            showcaseRoot.ClearChildren();
            arenaRoot.gameObject.SetActive(true);

            var theme = ArenaTheme.For(stage.ChapterId);
            ApplyTheme(theme);
            BuildEnvironment(theme, true);
            ResetBattleCamera();
        }

        public void ResetBattleCamera()
        {
            cam.fieldOfView = 34f;
            cam.transform.position = new Vector3(0f, 3.6f, -9.8f);
            cam.transform.LookAt(new Vector3(0f, 0.9f, 0.4f));
        }

        public void Shake(float strength = 0.15f, float duration = 0.25f)
        {
            if (shake != null) StopCoroutine(shake);
            shake = StartCoroutine(DoShake(strength, duration));
        }

        IEnumerator DoShake(float strength, float duration)
        {
            ResetBattleCamera();
            var basePos = cam.transform.position;
            float t = 0;
            while (t < duration)
            {
                t += Time.deltaTime;
                float s = strength * (1f - t / duration);
                cam.transform.position = basePos + new Vector3(UnityEngine.Random.Range(-s, s), UnityEngine.Random.Range(-s, s), 0);
                yield return null;
            }
            cam.transform.position = basePos;
        }

        void ApplyTheme(ArenaTheme theme)
        {
            var sky = ToonMaterials.Sky(theme.SkyTop, theme.SkyHorizon, theme.SkyBottom);
            if (sky != null) RenderSettings.skybox = sky;
            else cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = theme.SkyHorizon;
            sun.color = theme.Light;
            RenderSettings.ambientLight = Color.Lerp(theme.SkyHorizon, Color.gray, 0.5f);
        }

        void BuildEnvironment(ArenaTheme theme, bool battle)
        {
            if (environment != null) Destroy(environment.gameObject);
            environment = new GameObject("Umgebung").transform;
            environment.SetParent(transform, false);

            CharacterModels.Part(environment, PrimitiveType.Cylinder, "Boden", new Vector3(0, -0.05f, 2f), new Vector3(26f, 0.05f, 18f), theme.Ground, null, 0f);
            CharacterModels.Part(environment, PrimitiveType.Cylinder, "Kampffeld", new Vector3(0, -0.02f, 0.3f), new Vector3(10f, 0.03f, 5.2f), theme.GroundEdge, null, 0f);
            if (battle)
                CharacterModels.Part(environment, PrimitiveType.Cylinder, "Feldring", new Vector3(0, -0.01f, 0.3f), new Vector3(9.4f, 0.03f, 4.7f), theme.Ground, null, 0f);

            var rnd = new System.Random(theme.Props * 97 + 5);
            for (int i = 0; i < 14; i++)
            {
                float x = (float)(rnd.NextDouble() * 22 - 11);
                float z = (float)(rnd.NextDouble() * 8 + 4.5);
                if (!battle && x < 1.5f && x > -3.5f && z < 6f) continue;
                Prop(theme, new Vector3(x, 0, z), (float)rnd.NextDouble());
            }

            // Schwebende Aether-Kristalle
            for (int i = 0; i < 6; i++)
            {
                float x = -8f + i * 3.2f;
                var c = CharacterModels.Part(environment, PrimitiveType.Cube, "Aether-Kristall",
                    new Vector3(x, 3.5f + (i % 2) * 1.2f, 9f + (i % 3)), new Vector3(0.35f, 0.7f, 0.35f), theme.Accent, new Vector3(0, 0, 45), 0.002f, 0.9f);
                c.AddComponent<Spin>().Speed = 20f + i * 5f;
                c.AddComponent<Float>().Amplitude = 0.25f;
            }
        }

        void Prop(ArenaTheme theme, Vector3 pos, float r)
        {
            var t = environment;
            switch (theme.Props)
            {
                case 0: // Schrein: Torii und Kirschbäume
                    if (r < 0.25f)
                    {
                        var red = Theme.Hex("#E0352B");
                        CharacterModels.Part(t, PrimitiveType.Cylinder, "Torii", pos + new Vector3(-0.8f, 1.2f, 0), new Vector3(0.18f, 1.2f, 0.18f), red);
                        CharacterModels.Part(t, PrimitiveType.Cylinder, "Torii", pos + new Vector3(0.8f, 1.2f, 0), new Vector3(0.18f, 1.2f, 0.18f), red);
                        CharacterModels.Part(t, PrimitiveType.Cube, "Torii", pos + new Vector3(0, 2.4f, 0), new Vector3(2.3f, 0.18f, 0.25f), Theme.Hex("#2B1B1B"));
                        CharacterModels.Part(t, PrimitiveType.Cube, "Torii", pos + new Vector3(0, 2.05f, 0), new Vector3(1.8f, 0.12f, 0.18f), red);
                    }
                    else Tree(pos, Theme.Hex("#6B4A3A"), Theme.Hex("#FFB7D0"), 0.8f + r);
                    break;
                case 1: // Wald
                    Tree(pos, Theme.Hex("#5A3E2B"), Color.Lerp(Theme.Hex("#3E9E4F"), Theme.Hex("#8BD66B"), r), 1f + r);
                    break;
                case 2: // Hafen: Laternen und Pfähle
                    CharacterModels.Part(t, PrimitiveType.Cylinder, "Pfahl", pos + new Vector3(0, 1f, 0), new Vector3(0.2f, 1f + r, 0.2f), Theme.Hex("#4B3A2E"));
                    CharacterModels.Part(t, PrimitiveType.Cube, "Laterne", pos + new Vector3(0, 2.2f + r * 2f, 0), new Vector3(0.35f, 0.45f, 0.35f), Theme.Hex("#FFD27A"), null, 0.003f, 0.9f);
                    break;
                default: // Brennende Ebene: Felsen und Feuerkristalle
                    CharacterModels.Part(t, PrimitiveType.Sphere, "Fels", pos + new Vector3(0, 0.3f, 0), new Vector3(1.2f + r, 0.7f + r * 0.5f, 1f), Theme.Hex("#3A2A2A"));
                    if (r > 0.5f)
                        CharacterModels.Part(t, PrimitiveType.Cube, "Feuerkristall", pos + new Vector3(0.2f, 1f, 0), new Vector3(0.25f, 0.9f, 0.25f), Theme.Hex("#FF7A2F"), new Vector3(0, 30, 15), 0.003f, 1f);
                    break;
            }
        }

        void Tree(Vector3 pos, Color trunk, Color leaves, float size)
        {
            CharacterModels.Part(environment, PrimitiveType.Cylinder, "Stamm", pos + new Vector3(0, 0.9f * size, 0), new Vector3(0.25f, 0.9f * size, 0.25f), trunk);
            CharacterModels.Part(environment, PrimitiveType.Sphere, "Krone", pos + new Vector3(0, 2.1f * size, 0), new Vector3(1.6f, 1.3f, 1.6f) * size, leaves);
            CharacterModels.Part(environment, PrimitiveType.Sphere, "Krone", pos + new Vector3(0.4f, 2.6f * size, 0.1f), new Vector3(1.1f, 0.9f, 1.1f) * size, leaves);
        }
    }

    public sealed class Float : MonoBehaviour
    {
        public float Amplitude = 0.2f;
        public float Speed = 1.2f;
        Vector3 start;
        float phase;

        void Start()
        {
            start = transform.localPosition;
            phase = UnityEngine.Random.value * 10f;
        }

        void Update()
        {
            transform.localPosition = start + Vector3.up * Mathf.Sin(Time.time * Speed + phase) * Amplitude;
        }
    }

    /// <summary>Leichtes Wiegen für die Präsentation im Hauptmenü.</summary>
    public sealed class IdleSway : MonoBehaviour
    {
        Quaternion baseRot;

        void Start() { baseRot = transform.localRotation; }

        void Update()
        {
            transform.localRotation = baseRot * Quaternion.Euler(0, Mathf.Sin(Time.time * 0.6f) * 12f, 0);
        }
    }

    /// <summary>Die Figuren im Kampf und wo sie stehen.</summary>
    public sealed class BattleArena : MonoBehaviour
    {
        static readonly Vector3[] PlayerSlots = { new Vector3(-2.3f, 0, -0.4f), new Vector3(-3.3f, 0, 0.9f), new Vector3(-1.9f, 0, 1.9f) };
        static readonly Vector3[] EnemySlots = { new Vector3(2.3f, 0, -0.4f), new Vector3(3.3f, 0, 0.9f), new Vector3(2.1f, 0, 2.0f) };
        static readonly Vector3 BossSlot = new Vector3(2.9f, 0, 0.6f);

        readonly Dictionary<BattleUnit, UnitView> views = new Dictionary<BattleUnit, UnitView>();
        StageRig rig;
        GameObject targetRing;

        public event Action<BattleUnit> UnitClicked;

        public StageRig Rig { get { return rig; } }

        public void Init(StageRig stageRig)
        {
            rig = stageRig;
        }

        public void Clear()
        {
            foreach (var v in views.Values) if (v != null) Destroy(v.gameObject);
            views.Clear();
            if (targetRing != null) Destroy(targetRing);
        }

        public void SpawnPlayers(IReadOnlyList<BattleUnit> units)
        {
            for (int i = 0; i < units.Count; i++)
            {
                var model = CharacterModels.CreateHero(units[i].Character);
                Spawn(units[i], model, PlayerSlots[i % PlayerSlots.Length], 90f);
            }
        }

        public void SpawnEnemies(IReadOnlyList<BattleUnit> units)
        {
            var old = new List<BattleUnit>();
            foreach (var kv in views) if (!kv.Key.IsPlayer) old.Add(kv.Key);
            foreach (var u in old)
            {
                if (views[u] != null) Destroy(views[u].gameObject);
                views.Remove(u);
            }

            for (int i = 0; i < units.Count; i++)
            {
                var model = CharacterModels.CreateEnemy(units[i].Enemy);
                var pos = units.Count == 1 && units[i].Enemy.IsBoss ? BossSlot : EnemySlots[i % EnemySlots.Length];
                var view = Spawn(units[i], model, pos, -90f);
                view.PlayEntrance();
            }
        }

        UnitView Spawn(BattleUnit unit, GameObject model, Vector3 position, float yaw)
        {
            var holder = new GameObject(unit.Name);
            holder.transform.SetParent(transform, false);
            holder.transform.localPosition = position;
            holder.transform.localRotation = Quaternion.Euler(0, yaw, 0);
            model.transform.SetParent(holder.transform, false);
            model.transform.localPosition = Vector3.zero;
            model.transform.localRotation = Quaternion.identity;

            var collider = holder.AddComponent<BoxCollider>();
            float scale = model.transform.localScale.y;
            collider.center = new Vector3(0, 1f * scale, 0);
            collider.size = new Vector3(1.3f, 2.2f, 1.3f) * scale;

            var view = holder.AddComponent<UnitView>();
            view.Init(unit, model.transform, this);
            views[unit] = view;
            return view;
        }

        public UnitView ViewOf(BattleUnit unit)
        {
            UnitView v;
            return unit != null && views.TryGetValue(unit, out v) ? v : null;
        }

        internal void OnViewClicked(UnitView view)
        {
            if (UnitClicked != null) UnitClicked(view.Unit);
        }

        public void SetTarget(BattleUnit unit)
        {
            var view = ViewOf(unit);
            if (view == null || !unit.IsAlive)
            {
                if (targetRing != null) targetRing.SetActive(false);
                return;
            }
            if (targetRing == null)
            {
                targetRing = CharacterModels.Part(transform, PrimitiveType.Cylinder, "Ziel", Vector3.zero,
                    new Vector3(1.4f, 0.01f, 1.4f), Theme.Danger, null, 0f, 1f);
                targetRing.AddComponent<Pulse>();
            }
            targetRing.SetActive(true);
            targetRing.transform.SetParent(view.transform, false);
            float s = view.Model.localScale.x;
            targetRing.transform.localPosition = new Vector3(0, 0.03f, 0);
            targetRing.GetComponent<Pulse>().BaseScale = new Vector3(1.4f * s, 0.01f, 1.4f * s);
        }
    }

    public sealed class Pulse : MonoBehaviour
    {
        public Vector3 BaseScale;

        void Update()
        {
            if (BaseScale == Vector3.zero) BaseScale = transform.localScale;
            float s = 1f + Mathf.Sin(Time.time * 6f) * 0.08f;
            transform.localScale = new Vector3(BaseScale.x * s, BaseScale.y, BaseScale.z * s);
        }
    }

    /// <summary>Eine Figur im Kampf: Idle-Wippen, Angriff, Treffer-Blitz, Besiegt-Animation.</summary>
    public sealed class UnitView : MonoBehaviour, IPointerClickHandler
    {
        BattleArena arena;
        Renderer[] renderers;
        MaterialPropertyBlock block;
        Vector3 home;
        float phase;
        bool busy;

        public BattleUnit Unit { get; private set; }
        public Transform Model { get; private set; }

        public Vector3 HeadPosition
        {
            get { return transform.position + Vector3.up * (2.2f * Model.localScale.y + 0.2f); }
        }

        public Vector3 CenterPosition
        {
            get { return transform.position + Vector3.up * (1.0f * Model.localScale.y); }
        }

        public void Init(BattleUnit unit, Transform model, BattleArena owner)
        {
            Unit = unit;
            Model = model;
            arena = owner;
            home = transform.localPosition;
            renderers = model.GetComponentsInChildren<Renderer>();
            block = new MaterialPropertyBlock();
            phase = UnityEngine.Random.value * 10f;
        }

        void Update()
        {
            if (busy || Unit == null || !Unit.IsAlive) return;
            float bob = Mathf.Sin(Time.time * 2.4f + phase);
            Model.localPosition = new Vector3(0, Mathf.Max(0, bob) * 0.06f, 0);
            float squash = 1f + bob * 0.015f;
            var s = Model.localScale;
            float baseScale = s.x;
            Model.localScale = new Vector3(baseScale, baseScale * squash, baseScale);
        }

        public void OnPointerClick(PointerEventData eventData)
        {
            arena.OnViewClicked(this);
        }

        public void PlayEntrance()
        {
            StartCoroutine(Entrance());
        }

        IEnumerator Entrance()
        {
            busy = true;
            var target = transform.localPosition;
            var from = target + new Vector3(Unit.IsPlayer ? -3f : 3f, 0, 0);
            float t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime * 2.5f;
                transform.localPosition = Vector3.Lerp(from, target, Ease(t));
                yield return null;
            }
            home = target;
            busy = false;
        }

        /// <summary>Kurzer Sprung nach vorne und zurück.</summary>
        public IEnumerator Lunge(bool big)
        {
            busy = true;
            float dir = Unit.IsPlayer ? 1f : -1f;
            var forward = home + new Vector3(dir * (big ? 1.6f : 0.9f), 0, 0);
            float t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime * 7f;
                transform.localPosition = Vector3.Lerp(home, forward, Ease(t));
                Model.localPosition = Vector3.up * Mathf.Sin(t * Mathf.PI) * 0.35f;
                yield return null;
            }
            t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime * 5f;
                transform.localPosition = Vector3.Lerp(forward, home, Ease(t));
                yield return null;
            }
            transform.localPosition = home;
            busy = false;
        }

        public void Hit()
        {
            if (isActiveAndEnabled) StartCoroutine(HitRoutine());
        }

        IEnumerator HitRoutine()
        {
            float t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime * 5f;
                SetFlash(1f - t);
                float shake = (1f - t) * 0.12f;
                Model.localPosition = new Vector3(Mathf.Sin(t * 60f) * shake, Model.localPosition.y, 0);
                yield return null;
            }
            SetFlash(0);
        }

        public IEnumerator Die()
        {
            busy = true;
            float t = 0;
            var startScale = Model.localScale;
            while (t < 1f)
            {
                t += Time.deltaTime * 2f;
                SetFlash(Mathf.PingPong(t * 6f, 1f));
                Model.localScale = Vector3.Lerp(startScale, new Vector3(startScale.x * 1.3f, 0.01f, startScale.z * 1.3f), Ease(t));
                yield return null;
            }
            gameObject.SetActive(false);
        }

        void SetFlash(float amount)
        {
            if (renderers == null) return;
            block.SetFloat(ToonMaterials.FlashId, amount);
            foreach (var r in renderers) if (r != null) r.SetPropertyBlock(block);
        }

        static float Ease(float t)
        {
            t = Mathf.Clamp01(t);
            return 1f - (1f - t) * (1f - t);
        }
    }

    /// <summary>Einfache Partikel aus Grundformen – funktionieren ohne Partikel-Shader.</summary>
    public sealed class Vfx : MonoBehaviour
    {
        struct Bit
        {
            public Transform T;
            public Vector3 Velocity;
            public float Size;
        }

        readonly List<Bit> bits = new List<Bit>();
        float life;
        float age;
        float gravity;

        public static void Burst(Vector3 position, Color color, int count = 10, float speed = 3.5f, float size = 0.18f)
        {
            var fx = Create(position, 0.6f, 6f);
            for (int i = 0; i < count; i++)
            {
                var dir = UnityEngine.Random.onUnitSphere;
                dir.y = Mathf.Abs(dir.y) * 0.8f + 0.2f;
                fx.Add(PrimitiveType.Cube, color, dir * speed * UnityEngine.Random.Range(0.6f, 1.2f), size * UnityEngine.Random.Range(0.7f, 1.3f));
            }
        }

        public static void Rise(Vector3 position, Color color, int count = 12)
        {
            var fx = Create(position, 1f, -1.5f);
            for (int i = 0; i < count; i++)
            {
                var offset = new Vector3(UnityEngine.Random.Range(-0.5f, 0.5f), UnityEngine.Random.Range(-0.8f, 0.2f), UnityEngine.Random.Range(-0.5f, 0.5f));
                var bit = fx.Add(PrimitiveType.Sphere, color, Vector3.up * UnityEngine.Random.Range(1.5f, 3f), 0.12f);
                bit.localPosition = offset;
            }
        }

        static Vfx Create(Vector3 position, float lifetime, float gravity)
        {
            var go = new GameObject("VFX");
            go.transform.position = position;
            var fx = go.AddComponent<Vfx>();
            fx.life = lifetime;
            fx.gravity = gravity;
            return fx;
        }

        Transform Add(PrimitiveType type, Color color, Vector3 velocity, float size)
        {
            var p = CharacterModels.Part(transform, type, "Bit", Vector3.zero, Vector3.one * size, color, UnityEngine.Random.rotation.eulerAngles, 0f, 1f);
            p.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            bits.Add(new Bit { T = p.transform, Velocity = velocity, Size = size });
            return p.transform;
        }

        void Update()
        {
            age += Time.deltaTime;
            float k = 1f - age / life;
            if (k <= 0f)
            {
                Destroy(gameObject);
                return;
            }
            for (int i = 0; i < bits.Count; i++)
            {
                var b = bits[i];
                b.Velocity += Vector3.down * gravity * Time.deltaTime;
                b.T.localPosition += b.Velocity * Time.deltaTime;
                b.T.localScale = Vector3.one * b.Size * k;
                b.T.Rotate(360f * Time.deltaTime, 200f * Time.deltaTime, 0);
                bits[i] = b;
            }
        }
    }
}
