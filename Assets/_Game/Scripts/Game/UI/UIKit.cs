using System;
using System.Collections.Generic;
using Aether.Core;
using UnityEngine;
using UnityEngine.UI;

namespace Aether.Game
{
    /// <summary>Farben im Anime-Gacha-Look: dunkles Nachtblau mit Neon-Akzenten.</summary>
    public static class Theme
    {
        public static readonly Color Background = Hex("#0E1024");
        public static readonly Color Panel = Hex("#1A1D3AEE");
        public static readonly Color PanelLight = Hex("#2A2F5E");
        public static readonly Color PanelDark = Hex("#0B0D1ECC");
        public static readonly Color Accent = Hex("#FF4F8B");
        public static readonly Color Accent2 = Hex("#4FD1FF");
        public static readonly Color Gold = Hex("#FFC83C");
        public static readonly Color Text = Color.white;
        public static readonly Color TextDim = Hex("#A9ADD6");
        public static readonly Color Success = Hex("#46E08A");
        public static readonly Color Danger = Hex("#FF5A5A");
        public static readonly Color Disabled = Hex("#4A4D6A");
        public static readonly Color Buff = Hex("#7CFFB2");
        public static readonly Color Debuff = Hex("#C58CFF");

        public static Color Of(Element e)
        {
            switch (e)
            {
                case Element.Fire: return Hex("#FF5A3C");
                case Element.Water: return Hex("#3CA0FF");
                case Element.Wind: return Hex("#3CDC8C");
                case Element.Earth: return Hex("#C89646");
                case Element.Light: return Hex("#FFE066");
                default: return Hex("#A05AFF");
            }
        }

        public static Color Of(Rarity r)
        {
            switch (r)
            {
                case Rarity.SSR: return Gold;
                case Rarity.SR: return Hex("#B266FF");
                default: return Hex("#6FA8DC");
            }
        }

        public static Color Hex(string hex)
        {
            Color c;
            return ColorUtility.TryParseHtmlString(hex, out c) ? c : Color.magenta;
        }

        public static Color WithAlpha(this Color c, float a)
        {
            c.a = a;
            return c;
        }
    }

    /// <summary>Registrierte UI-Elemente, die das Tutorial hervorheben kann.</summary>
    public static class UIAnchors
    {
        static readonly Dictionary<string, RectTransform> map = new Dictionary<string, RectTransform>();

        public static void Register(string key, RectTransform rt)
        {
            if (!string.IsNullOrEmpty(key)) map[key] = rt;
        }

        public static RectTransform Find(string key)
        {
            RectTransform rt;
            if (key == null || !map.TryGetValue(key, out rt)) return null;
            return rt != null && rt.gameObject.activeInHierarchy ? rt : null;
        }
    }

    /// <summary>Baut die komplette Oberfläche per Code – dadurch braucht das Projekt keine Prefabs.</summary>
    public static class UIKit
    {
        static Font font;
        static Sprite rounded;
        static Sprite frame;
        static Sprite circle;

        public static Font Font
        {
            get
            {
                if (font == null) font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                return font;
            }
        }

        public static Sprite Rounded
        {
            get { return rounded != null ? rounded : (rounded = MakeRounded(64, 22, false)); }
        }

        public static Sprite Frame
        {
            get { return frame != null ? frame : (frame = MakeRounded(64, 22, true)); }
        }

        public static Sprite Circle
        {
            get { return circle != null ? circle : (circle = MakeRounded(128, 64, false, false)); }
        }

        // ------------------------------------------------------------------ Grundbausteine

        public static RectTransform Rect(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = 5; // UI
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            return rt;
        }

        public static RectTransform Stretch(this RectTransform rt, float left = 0, float top = 0, float right = 0, float bottom = 0)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.offsetMin = new Vector2(left, bottom);
            rt.offsetMax = new Vector2(-right, -top);
            return rt;
        }

        /// <summary>Positioniert relativ zu einem Anker (0..1). Pivot = Anker.</summary>
        public static RectTransform Place(this RectTransform rt, float anchorX, float anchorY, float x, float y, float width, float height)
        {
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(anchorX, anchorY);
            rt.anchoredPosition = new Vector2(x, y);
            rt.sizeDelta = new Vector2(width, height);
            return rt;
        }

        public static Image Panel(Transform parent, string name, Color color, Sprite sprite = null, bool raycast = true)
        {
            var rt = Rect(name, parent);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sprite != null ? sprite : Rounded;
            img.type = Image.Type.Sliced;
            img.color = color;
            img.raycastTarget = raycast;
            return img;
        }

        public static Image Flat(Transform parent, string name, Color color, bool raycast = false)
        {
            var rt = Rect(name, parent);
            var img = rt.gameObject.AddComponent<Image>();
            img.color = color;
            img.raycastTarget = raycast;
            return img;
        }

        public static Text Label(Transform parent, string text, int size, Color color,
            TextAnchor align = TextAnchor.MiddleCenter, FontStyle style = FontStyle.Normal)
        {
            var rt = Rect("Text", parent);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = Font;
            t.text = text;
            t.fontSize = size;
            t.color = color;
            t.alignment = align;
            t.fontStyle = style;
            t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.supportRichText = true;
            return t;
        }

        public static Outline Outlined(this Text text, Color color, float distance = 2f)
        {
            var o = text.gameObject.AddComponent<Outline>();
            o.effectColor = color;
            o.effectDistance = new Vector2(distance, -distance);
            return o;
        }

        /// <summary>
        /// Button mit Tutorial-Sperre: Ist ein Schlüssel gesetzt, darf er nur gedrückt werden,
        /// wenn das Tutorial es gerade erlaubt. Der Schlüssel dient auch als Hervorhebungs-Anker.
        /// </summary>
        public static Button Button(Transform parent, string label, Color color, Action onClick, int fontSize = 34, string key = null)
        {
            var img = Panel(parent, "Button " + label, color);
            var button = img.gameObject.AddComponent<Button>();
            var colors = button.colors;
            colors.highlightedColor = new Color(1.08f, 1.08f, 1.08f, 1f);
            colors.pressedColor = new Color(0.8f, 0.8f, 0.8f, 1f);
            colors.disabledColor = new Color(0.45f, 0.45f, 0.5f, 0.8f);
            colors.fadeDuration = 0.08f;
            button.colors = colors;

            var text = Label(img.transform, label, fontSize, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
            text.rectTransform.Stretch(8, 4, 8, 4);
            text.Outlined(new Color(0, 0, 0, 0.35f), 1.5f);

            if (key != null) UIAnchors.Register(key, img.rectTransform);
            button.onClick.AddListener(() =>
            {
                var app = GameApp.Instance;
                if (key != null && app != null && !app.Tutorial.CanPress(key))
                {
                    app.UI.Toast("Folge zuerst dem Tutorial.");
                    return;
                }
                if (onClick != null) onClick();
            });
            return button;
        }

        public static void SetLabel(this Button button, string label)
        {
            var t = button.GetComponentInChildren<Text>();
            if (t != null) t.text = label;
        }

        public static LayoutElement Size(this Component c, float width, float height)
        {
            var le = c.GetComponent<LayoutElement>();
            if (le == null) le = c.gameObject.AddComponent<LayoutElement>();
            if (width >= 0) le.preferredWidth = le.minWidth = width;
            if (height >= 0) le.preferredHeight = le.minHeight = height;
            return le;
        }

        public static LayoutElement Flexible(this Component c, float flexWidth, float flexHeight)
        {
            var le = c.GetComponent<LayoutElement>();
            if (le == null) le = c.gameObject.AddComponent<LayoutElement>();
            le.flexibleWidth = flexWidth;
            le.flexibleHeight = flexHeight;
            return le;
        }

        public static VerticalLayoutGroup VList(this RectTransform rt, float spacing, int padding = 0,
            TextAnchor align = TextAnchor.UpperCenter, bool expandWidth = true)
        {
            var g = rt.gameObject.AddComponent<VerticalLayoutGroup>();
            g.spacing = spacing;
            g.padding = new RectOffset(padding, padding, padding, padding);
            g.childAlignment = align;
            g.childControlWidth = true;
            g.childControlHeight = true;
            g.childForceExpandWidth = expandWidth;
            g.childForceExpandHeight = false;
            return g;
        }

        public static HorizontalLayoutGroup HList(this RectTransform rt, float spacing, int padding = 0,
            TextAnchor align = TextAnchor.MiddleCenter, bool expandHeight = true)
        {
            var g = rt.gameObject.AddComponent<HorizontalLayoutGroup>();
            g.spacing = spacing;
            g.padding = new RectOffset(padding, padding, padding, padding);
            g.childAlignment = align;
            g.childControlWidth = true;
            g.childControlHeight = true;
            g.childForceExpandWidth = false;
            g.childForceExpandHeight = expandHeight;
            return g;
        }

        /// <summary>Scrollbare Liste. Kinder kommen in <paramref name="content"/>.</summary>
        public static ScrollRect Scroll(Transform parent, bool vertical, out RectTransform content)
        {
            var view = Panel(parent, "Scroll", new Color(0, 0, 0, 0.001f));
            view.gameObject.AddComponent<RectMask2D>();
            var scroll = view.gameObject.AddComponent<ScrollRect>();
            scroll.horizontal = !vertical;
            scroll.vertical = vertical;
            scroll.movementType = ScrollRect.MovementType.Elastic;
            scroll.scrollSensitivity = 30f;

            content = Rect("Content", view.transform);
            if (vertical)
            {
                content.anchorMin = new Vector2(0, 1);
                content.anchorMax = new Vector2(1, 1);
                content.pivot = new Vector2(0.5f, 1);
            }
            else
            {
                content.anchorMin = new Vector2(0, 0);
                content.anchorMax = new Vector2(0, 1);
                content.pivot = new Vector2(0, 0.5f);
            }
            content.offsetMin = content.offsetMax = Vector2.zero;
            var fitter = content.gameObject.AddComponent<ContentSizeFitter>();
            fitter.verticalFit = vertical ? ContentSizeFitter.FitMode.PreferredSize : ContentSizeFitter.FitMode.Unconstrained;
            fitter.horizontalFit = vertical ? ContentSizeFitter.FitMode.Unconstrained : ContentSizeFitter.FitMode.PreferredSize;
            scroll.content = content;
            scroll.viewport = view.rectTransform;
            return scroll;
        }

        /// <summary>Balken, dessen Füllung über den Anker skaliert (funktioniert ohne Sprite).</summary>
        public static RectTransform Bar(Transform parent, Color background, Color fillColor, out Image fill)
        {
            var bg = Panel(parent, "Bar", background, null, false);
            fill = Panel(bg.transform, "Fill", fillColor, null, false);
            fill.rectTransform.anchorMin = Vector2.zero;
            fill.rectTransform.anchorMax = Vector2.one;
            fill.rectTransform.offsetMin = new Vector2(2, 2);
            fill.rectTransform.offsetMax = new Vector2(-2, -2);
            return bg.rectTransform;
        }

        public static void SetFill(this Image fill, float ratio)
        {
            ratio = Mathf.Clamp01(ratio);
            fill.rectTransform.anchorMax = new Vector2(ratio, 1);
            fill.enabled = ratio > 0.001f;
        }

        public static void ClearChildren(this Transform t)
        {
            for (int i = t.childCount - 1; i >= 0; i--) UnityEngine.Object.Destroy(t.GetChild(i).gameObject);
        }

        // ------------------------------------------------------------------ Sprites

        static Sprite MakeRounded(int size, int radius, bool hollow, bool sliced = true)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false);
            tex.wrapMode = TextureWrapMode.Clamp;
            tex.filterMode = FilterMode.Bilinear;
            var pixels = new Color32[size * size];
            float r = radius;
            float border = 5f;
            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    float px = x + 0.5f, py = y + 0.5f;
                    float cx = Mathf.Clamp(px, r, size - r);
                    float cy = Mathf.Clamp(py, r, size - r);
                    float d = Vector2.Distance(new Vector2(px, py), new Vector2(cx, cy));
                    float alpha = Mathf.Clamp01(r - d + 0.5f);
                    if (hollow) alpha *= Mathf.Clamp01(d - (r - border) + 0.5f);
                    pixels[y * size + x] = new Color32(255, 255, 255, (byte)(alpha * 255));
                }
            }
            tex.SetPixels32(pixels);
            tex.Apply();
            var b = sliced ? radius + 2 : 0;
            return Sprite.Create(tex, new UnityEngine.Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f, 0,
                SpriteMeshType.FullRect, new Vector4(b, b, b, b));
        }
    }

    /// <summary>Hält Inhalte aus dem Bereich von Notch und abgerundeten Ecken heraus.</summary>
    public sealed class SafeArea : MonoBehaviour
    {
        UnityEngine.Rect applied;
        Vector2Int screen;

        void Update()
        {
            var safe = Screen.safeArea;
            if (safe == applied && screen.x == Screen.width && screen.y == Screen.height) return;
            applied = safe;
            screen = new Vector2Int(Screen.width, Screen.height);
            if (Screen.width <= 0 || Screen.height <= 0) return;

            var rt = (RectTransform)transform;
            rt.anchorMin = new Vector2(safe.xMin / Screen.width, safe.yMin / Screen.height);
            rt.anchorMax = new Vector2(safe.xMax / Screen.width, safe.yMax / Screen.height);
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }
    }
}
