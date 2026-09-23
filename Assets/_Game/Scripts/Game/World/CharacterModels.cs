using System.Collections.Generic;
using Aether.Core;
using UnityEngine;

namespace Aether.Game
{
    /// <summary>Materialien mit dem Anime-Toon-Shader (Cel-Shading + Outline), nach Farbe zwischengespeichert.</summary>
    public static class ToonMaterials
    {
        static readonly Dictionary<string, Material> cache = new Dictionary<string, Material>();
        static Shader toon;
        static Shader sky;

        public static readonly int FlashId = Shader.PropertyToID("_Flash");

        public static Shader Toon
        {
            get
            {
                if (toon == null) toon = Shader.Find("Aether/AnimeToon");
                if (toon == null) toon = Shader.Find("Standard");
                return toon;
            }
        }

        public static Material Get(Color color, float outline = 0.004f, float emission = 0f)
        {
            string key = ColorUtility.ToHtmlStringRGBA(color) + "_" + outline + "_" + emission;
            Material m;
            if (cache.TryGetValue(key, out m) && m != null) return m;

            m = new Material(Toon);
            m.color = color;
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", color);
            if (m.HasProperty("_OutlineWidth")) m.SetFloat("_OutlineWidth", outline);
            if (m.HasProperty("_Emission")) m.SetFloat("_Emission", emission);
            if (m.HasProperty("_ShadeColor"))
            {
                Color.RGBToHSV(color, out float h, out float s, out float v);
                var shade = Color.HSVToRGB((h + 0.03f) % 1f, Mathf.Clamp01(s * 1.15f + 0.05f), v * 0.62f);
                m.SetColor("_ShadeColor", shade);
            }
            cache[key] = m;
            return m;
        }

        public static Material Sky(Color top, Color horizon, Color bottom)
        {
            if (sky == null) sky = Shader.Find("Aether/SkyGradient");
            if (sky == null) return null;
            var m = new Material(sky);
            m.SetColor("_TopColor", top);
            m.SetColor("_HorizonColor", horizon);
            m.SetColor("_BottomColor", bottom);
            return m;
        }
    }

    /// <summary>
    /// Erzeugt 3D-Figuren. Liegt unter Resources/Characters/&lt;id&gt; ein Prefab
    /// (z. B. ein VRoid-Modell), wird dieses verwendet – sonst ein Chibi-Platzhalter aus Grundformen.
    /// </summary>
    public static class CharacterModels
    {
        static readonly Color Skin = Theme.Hex("#FFE3D0");
        static readonly Color Dark = Theme.Hex("#1B1B28");

        public static GameObject CreateHero(CharacterDefinition c)
        {
            var custom = TryLoad(c.Id);
            if (custom != null) return custom;

            var hair = Theme.Hex(c.HairColor);
            var outfit = Theme.Hex(c.OutfitColor);
            var eyes = Theme.Hex(c.EyeColor);
            var root = Humanoid(c.Name, hair, outfit, eyes, Skin, false);
            AddWeapon(root.transform, c.Role, Theme.Of(c.Element));
            return root;
        }

        public static GameObject CreateEnemy(EnemyDefinition e)
        {
            var custom = TryLoad(e.Id);
            if (custom != null) return custom;

            var color = Theme.Hex(e.Color);
            var glow = Theme.Of(e.Element);
            GameObject root;
            switch (e.Shape)
            {
                case BodyShape.Slime: root = Slime(e.Name, color); break;
                case BodyShape.Beast: root = Beast(e.Name, color, glow); break;
                case BodyShape.Golem: root = Golem(e.Name, color, glow); break;
                case BodyShape.Wisp: root = Wisp(e.Name, color, glow); break;
                default:
                    root = Humanoid(e.Name, Dark, color, Theme.Danger, Theme.Hex("#9A8FB0"), true);
                    AddWeapon(root.transform, Role.Attacker, glow);
                    if (e.IsBoss) Horns(root.transform, glow);
                    break;
            }
            root.transform.localScale = Vector3.one * e.Scale;
            return root;
        }

        static GameObject TryLoad(string id)
        {
            var prefab = Resources.Load<GameObject>("Characters/" + id);
            if (prefab == null) return null;
            var go = Object.Instantiate(prefab);
            go.name = id;
            var controller = Resources.Load<RuntimeAnimatorController>("Animations/BattleIdle");
            var animator = go.GetComponentInChildren<Animator>();
            if (controller != null && animator != null && animator.runtimeAnimatorController == null)
                animator.runtimeAnimatorController = controller;
            return go;
        }

        // ------------------------------------------------------------------ Platzhalter-Formen (Blick nach +Z)

        static GameObject Humanoid(string name, Color hair, Color outfit, Color eyes, Color skin, bool menacing)
        {
            var root = new GameObject(name);
            var t = root.transform;
            var outfitDark = outfit * 0.7f;
            outfitDark.a = 1;

            Part(t, PrimitiveType.Capsule, "Bein L", new Vector3(-0.12f, 0.28f, 0), new Vector3(0.17f, 0.28f, 0.17f), outfitDark);
            Part(t, PrimitiveType.Capsule, "Bein R", new Vector3(0.12f, 0.28f, 0), new Vector3(0.17f, 0.28f, 0.17f), outfitDark);
            Part(t, PrimitiveType.Capsule, "Körper", new Vector3(0, 0.78f, 0), new Vector3(0.5f, 0.4f, 0.36f), outfit);
            Part(t, PrimitiveType.Cylinder, "Rock", new Vector3(0, 0.58f, 0), new Vector3(0.56f, 0.1f, 0.44f), outfitDark);
            Part(t, PrimitiveType.Capsule, "Arm L", new Vector3(-0.33f, 0.82f, 0), new Vector3(0.13f, 0.27f, 0.13f), outfit, new Vector3(0, 0, -12));
            Part(t, PrimitiveType.Capsule, "Arm R", new Vector3(0.33f, 0.82f, 0), new Vector3(0.13f, 0.27f, 0.13f), outfit, new Vector3(0, 0, 12));

            // Großer Kopf = Anime-Chibi-Proportionen
            Part(t, PrimitiveType.Sphere, "Kopf", new Vector3(0, 1.42f, 0), new Vector3(0.6f, 0.58f, 0.56f), skin);
            Part(t, PrimitiveType.Sphere, "Haar", new Vector3(0, 1.55f, -0.04f), new Vector3(0.68f, 0.5f, 0.64f), hair);
            Part(t, PrimitiveType.Sphere, "Haar hinten", new Vector3(0, 1.32f, -0.17f), new Vector3(0.62f, 0.66f, 0.34f), hair);
            Part(t, PrimitiveType.Sphere, "Pony L", new Vector3(-0.15f, 1.6f, 0.2f), new Vector3(0.24f, 0.16f, 0.18f), hair, new Vector3(0, 0, 25));
            Part(t, PrimitiveType.Sphere, "Pony R", new Vector3(0.15f, 1.6f, 0.2f), new Vector3(0.24f, 0.16f, 0.18f), hair, new Vector3(0, 0, -25));

            // Große Anime-Augen mit Glanzpunkt
            float eyeY = menacing ? 1.42f : 1.39f;
            Part(t, PrimitiveType.Sphere, "Auge L", new Vector3(-0.12f, eyeY, 0.255f), new Vector3(0.11f, menacing ? 0.07f : 0.15f, 0.05f), eyes, null, 0f, menacing ? 1f : 0f);
            Part(t, PrimitiveType.Sphere, "Auge R", new Vector3(0.12f, eyeY, 0.255f), new Vector3(0.11f, menacing ? 0.07f : 0.15f, 0.05f), eyes, null, 0f, menacing ? 1f : 0f);
            if (!menacing)
            {
                Part(t, PrimitiveType.Sphere, "Glanz L", new Vector3(-0.1f, 1.42f, 0.28f), Vector3.one * 0.04f, Color.white, null, 0f, 1f);
                Part(t, PrimitiveType.Sphere, "Glanz R", new Vector3(0.14f, 1.42f, 0.28f), Vector3.one * 0.04f, Color.white, null, 0f, 1f);
            }
            return root;
        }

        static void AddWeapon(Transform root, Role role, Color accent)
        {
            switch (role)
            {
                case Role.Attacker:
                    Part(root, PrimitiveType.Cube, "Klinge", new Vector3(0.45f, 1.05f, 0.22f), new Vector3(0.05f, 0.85f, 0.12f), Theme.Hex("#E8ECF5"), new Vector3(35, 0, -10));
                    Part(root, PrimitiveType.Cube, "Griff", new Vector3(0.42f, 0.7f, 0.02f), new Vector3(0.18f, 0.05f, 0.08f), accent, new Vector3(35, 0, -10));
                    break;
                case Role.Defender:
                    Part(root, PrimitiveType.Cylinder, "Schild", new Vector3(-0.45f, 0.85f, 0.15f), new Vector3(0.5f, 0.03f, 0.5f), accent, new Vector3(90, 0, 70));
                    break;
                default:
                    Part(root, PrimitiveType.Cylinder, "Stab", new Vector3(0.42f, 0.95f, 0.1f), new Vector3(0.05f, 0.6f, 0.05f), Theme.Hex("#8B6B4A"));
                    Part(root, PrimitiveType.Sphere, "Kristall", new Vector3(0.42f, 1.6f, 0.1f), Vector3.one * 0.2f, accent, null, 0.002f, 0.8f);
                    break;
            }
        }

        static void Horns(Transform root, Color glow)
        {
            Part(root, PrimitiveType.Cube, "Horn L", new Vector3(-0.2f, 1.85f, 0), new Vector3(0.07f, 0.3f, 0.07f), glow, new Vector3(0, 0, 20), 0.003f, 0.6f);
            Part(root, PrimitiveType.Cube, "Horn R", new Vector3(0.2f, 1.85f, 0), new Vector3(0.07f, 0.3f, 0.07f), glow, new Vector3(0, 0, -20), 0.003f, 0.6f);
        }

        static GameObject Slime(string name, Color color)
        {
            var root = new GameObject(name);
            Part(root.transform, PrimitiveType.Sphere, "Körper", new Vector3(0, 0.38f, 0), new Vector3(1f, 0.75f, 0.95f), color);
            Part(root.transform, PrimitiveType.Sphere, "Auge L", new Vector3(-0.17f, 0.5f, 0.42f), new Vector3(0.12f, 0.18f, 0.06f), Dark);
            Part(root.transform, PrimitiveType.Sphere, "Auge R", new Vector3(0.17f, 0.5f, 0.42f), new Vector3(0.12f, 0.18f, 0.06f), Dark);
            Part(root.transform, PrimitiveType.Sphere, "Glanz", new Vector3(-0.25f, 0.62f, 0.3f), new Vector3(0.14f, 0.1f, 0.06f), Color.white, null, 0f, 1f);
            return root;
        }

        static GameObject Beast(string name, Color color, Color glow)
        {
            var root = new GameObject(name);
            var t = root.transform;
            Part(t, PrimitiveType.Capsule, "Körper", new Vector3(0, 0.6f, 0), new Vector3(0.5f, 0.55f, 0.5f), color, new Vector3(90, 0, 0));
            Part(t, PrimitiveType.Sphere, "Kopf", new Vector3(0, 0.85f, 0.55f), new Vector3(0.45f, 0.4f, 0.5f), color);
            Part(t, PrimitiveType.Cube, "Ohr L", new Vector3(-0.14f, 1.1f, 0.5f), new Vector3(0.08f, 0.2f, 0.08f), color, new Vector3(0, 0, 15));
            Part(t, PrimitiveType.Cube, "Ohr R", new Vector3(0.14f, 1.1f, 0.5f), new Vector3(0.08f, 0.2f, 0.08f), color, new Vector3(0, 0, -15));
            Part(t, PrimitiveType.Sphere, "Auge L", new Vector3(-0.1f, 0.9f, 0.78f), new Vector3(0.08f, 0.05f, 0.04f), glow, null, 0f, 1f);
            Part(t, PrimitiveType.Sphere, "Auge R", new Vector3(0.1f, 0.9f, 0.78f), new Vector3(0.08f, 0.05f, 0.04f), glow, null, 0f, 1f);
            for (int i = 0; i < 4; i++)
            {
                float x = i % 2 == 0 ? -0.17f : 0.17f;
                float z = i < 2 ? 0.3f : -0.3f;
                Part(t, PrimitiveType.Cylinder, "Bein", new Vector3(x, 0.2f, z), new Vector3(0.12f, 0.2f, 0.12f), color * 0.8f);
            }
            Part(t, PrimitiveType.Capsule, "Schwanz", new Vector3(0, 0.75f, -0.6f), new Vector3(0.1f, 0.25f, 0.1f), glow, new Vector3(-50, 0, 0), 0.003f, 0.5f);
            return root;
        }

        static GameObject Golem(string name, Color color, Color glow)
        {
            var root = new GameObject(name);
            var t = root.transform;
            var stone = Theme.Hex("#5B6475");
            Part(t, PrimitiveType.Cube, "Bein L", new Vector3(-0.25f, 0.3f, 0), new Vector3(0.3f, 0.6f, 0.3f), stone);
            Part(t, PrimitiveType.Cube, "Bein R", new Vector3(0.25f, 0.3f, 0), new Vector3(0.3f, 0.6f, 0.3f), stone);
            Part(t, PrimitiveType.Cube, "Rumpf", new Vector3(0, 1f, 0), new Vector3(0.95f, 0.8f, 0.6f), stone);
            Part(t, PrimitiveType.Cube, "Kopf", new Vector3(0, 1.58f, 0.05f), new Vector3(0.4f, 0.35f, 0.4f), stone);
            Part(t, PrimitiveType.Cube, "Arm L", new Vector3(-0.65f, 0.9f, 0.05f), new Vector3(0.3f, 0.85f, 0.3f), stone, new Vector3(0, 0, -8));
            Part(t, PrimitiveType.Cube, "Arm R", new Vector3(0.65f, 0.9f, 0.05f), new Vector3(0.3f, 0.85f, 0.3f), stone, new Vector3(0, 0, 8));
            Part(t, PrimitiveType.Sphere, "Kern", new Vector3(0, 1.05f, 0.3f), Vector3.one * 0.25f, color, null, 0.002f, 1f);
            Part(t, PrimitiveType.Cube, "Auge", new Vector3(0, 1.6f, 0.26f), new Vector3(0.25f, 0.06f, 0.02f), glow, null, 0f, 1f);
            Part(t, PrimitiveType.Cube, "Kristall 1", new Vector3(-0.3f, 1.5f, -0.1f), new Vector3(0.15f, 0.45f, 0.15f), color, new Vector3(10, 0, 25), 0.003f, 0.6f);
            Part(t, PrimitiveType.Cube, "Kristall 2", new Vector3(0.35f, 1.55f, -0.15f), new Vector3(0.12f, 0.35f, 0.12f), color, new Vector3(-10, 0, -30), 0.003f, 0.6f);
            return root;
        }

        static GameObject Wisp(string name, Color color, Color glow)
        {
            var root = new GameObject(name);
            var t = root.transform;
            Part(t, PrimitiveType.Sphere, "Kern", new Vector3(0, 1.1f, 0), Vector3.one * 0.55f, color, null, 0.004f, 0.7f);
            Part(t, PrimitiveType.Sphere, "Flügel L", new Vector3(-0.45f, 1.2f, -0.05f), new Vector3(0.55f, 0.12f, 0.3f), glow, new Vector3(0, 0, 20));
            Part(t, PrimitiveType.Sphere, "Flügel R", new Vector3(0.45f, 1.2f, -0.05f), new Vector3(0.55f, 0.12f, 0.3f), glow, new Vector3(0, 0, -20));
            Part(t, PrimitiveType.Sphere, "Auge L", new Vector3(-0.1f, 1.15f, 0.25f), new Vector3(0.08f, 0.12f, 0.04f), Dark);
            Part(t, PrimitiveType.Sphere, "Auge R", new Vector3(0.1f, 1.15f, 0.25f), new Vector3(0.08f, 0.12f, 0.04f), Dark);
            return root;
        }

        public static GameObject Part(Transform parent, PrimitiveType type, string name, Vector3 position, Vector3 scale,
            Color color, Vector3? euler = null, float outline = 0.004f, float emission = 0f)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name;
            Object.Destroy(go.GetComponent<Collider>());
            var t = go.transform;
            t.SetParent(parent, false);
            t.localPosition = position;
            t.localScale = scale;
            if (euler.HasValue) t.localEulerAngles = euler.Value;
            var r = go.GetComponent<Renderer>();
            r.sharedMaterial = ToonMaterials.Get(color, outline, emission);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            return go;
        }
    }

    public sealed class Spin : MonoBehaviour
    {
        public float Speed = 30f;
        public Vector3 Axis = Vector3.up;

        void Update()
        {
            if (Speed != 0f) transform.Rotate(Axis, Speed * Time.deltaTime, Space.Self);
        }
    }
}
