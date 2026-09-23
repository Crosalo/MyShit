using System;
using System.Collections;
using System.Collections.Generic;
using Aether.Core;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Aether.Game
{
    public abstract class UIScreen : MonoBehaviour
    {
        bool built;

        protected GameApp App { get { return GameApp.Instance; } }
        protected RectTransform Root { get { return (RectTransform)transform; } }

        public void EnsureBuilt()
        {
            if (built) return;
            built = true;
            Build();
        }

        protected abstract void Build();

        public virtual void OnShow() { }
        public virtual void OnHide() { }

        public void Show()
        {
            EnsureBuilt();
            gameObject.SetActive(true);
            OnShow();
        }

        public void Hide()
        {
            if (!gameObject.activeSelf) return;
            OnHide();
            gameObject.SetActive(false);
        }
    }

    /// <summary>Kopfzeile mit Titel, Zurück-Button und Währungen.</summary>
    public sealed class HeaderBar : MonoBehaviour
    {
        Text crystals;
        Text gold;

        public static HeaderBar Create(Transform parent, string title, Action back)
        {
            var bar = UIKit.Rect("Header", parent);
            bar.anchorMin = new Vector2(0, 1);
            bar.anchorMax = new Vector2(1, 1);
            bar.pivot = new Vector2(0.5f, 1);
            bar.sizeDelta = new Vector2(0, 110);
            bar.anchoredPosition = Vector2.zero;
            var header = bar.gameObject.AddComponent<HeaderBar>();

            float x = 30;
            if (back != null)
            {
                var b = UIKit.Button(bar, "‹ Zurück", Theme.PanelLight, back, 30, "nav.back");
                b.GetComponent<RectTransform>().Place(0, 0.5f, 30, 0, 200, 76);
                x += 230;
            }

            var t = UIKit.Label(bar, title, 46, Theme.Text, TextAnchor.MiddleLeft, FontStyle.Bold);
            t.rectTransform.Place(0, 0.5f, x, 0, 900, 90);
            t.Outlined(new Color(0, 0, 0, 0.5f));

            header.crystals = Chip(bar, Theme.Accent2, -330);
            header.gold = Chip(bar, Theme.Gold, -30);
            header.Refresh();
            return header;
        }

        static Text Chip(Transform parent, Color color, float x)
        {
            var chip = UIKit.Panel(parent, "Chip", Theme.PanelDark, null, false);
            chip.rectTransform.Place(1, 0.5f, x, 0, 280, 64);
            var dot = UIKit.Panel(chip.transform, "Icon", color, UIKit.Circle, false);
            dot.type = Image.Type.Simple;
            dot.rectTransform.Place(0, 0.5f, 12, 0, 40, 40);
            var t = UIKit.Label(chip.transform, "0", 32, Theme.Text, TextAnchor.MiddleRight, FontStyle.Bold);
            t.rectTransform.Stretch(60, 0, 18, 0);
            return t;
        }

        public void Refresh()
        {
            var app = GameApp.Instance;
            if (app == null) return;
            crystals.text = app.Profile.Crystals.ToString("N0") + " ✦";
            gold.text = app.Profile.Gold.ToString("N0") + " G";
        }
    }

    public sealed class UIRoot : MonoBehaviour
    {
        readonly Dictionary<Type, UIScreen> screens = new Dictionary<Type, UIScreen>();
        UIScreen current;
        RectTransform toastRoot;

        public Canvas Canvas { get; private set; }
        public RectTransform ScreenRoot { get; private set; }
        public RectTransform OverlayRoot { get; private set; }
        public DialogueOverlay Dialogue { get; private set; }
        public TutorialOverlay TutorialOverlay { get; private set; }
        public UIScreen Current { get { return current; } }

        public static UIRoot Create(Transform parent)
        {
            var go = new GameObject("UI");
            go.transform.SetParent(parent, false);
            go.layer = 5;
            var root = go.AddComponent<UIRoot>();

            root.Canvas = go.AddComponent<Canvas>();
            root.Canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            root.Canvas.sortingOrder = 10;
            var scaler = go.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 0.75f;
            go.AddComponent<GraphicRaycaster>();

            var safe = UIKit.Rect("SafeArea", go.transform).Stretch();
            safe.gameObject.AddComponent<SafeArea>();
            root.ScreenRoot = UIKit.Rect("Screens", safe).Stretch();
            root.OverlayRoot = UIKit.Rect("Overlays", safe).Stretch();
            root.toastRoot = UIKit.Rect("Toasts", safe).Stretch();

            root.Dialogue = DialogueOverlay.Create(root.OverlayRoot);
            root.TutorialOverlay = TutorialOverlay.Create(go.transform);

            EnsureEventSystem(parent);
            return root;
        }

        static void EnsureEventSystem(Transform parent)
        {
            if (EventSystem.current != null) return;
            var es = new GameObject("EventSystem", typeof(EventSystem));
            es.transform.SetParent(parent, false);
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            es.AddComponent<UnityEngine.InputSystem.UI.InputSystemUIInputModule>();
#else
            es.AddComponent<StandaloneInputModule>();
#endif
        }

        public T Get<T>() where T : UIScreen
        {
            UIScreen screen;
            if (!screens.TryGetValue(typeof(T), out screen))
            {
                var rt = UIKit.Rect(typeof(T).Name, ScreenRoot).Stretch();
                screen = rt.gameObject.AddComponent<T>();
                screen.EnsureBuilt();
                rt.gameObject.SetActive(false);
                screens.Add(typeof(T), screen);
            }
            return (T)screen;
        }

        public T Show<T>() where T : UIScreen
        {
            var screen = Get<T>();
            if (current != null && current != screen) current.Hide();
            current = screen;
            screen.Show();
            return screen;
        }

        /// <summary>Aktuellen Bildschirm neu aufbauen lassen (z. B. nach Währungsänderung).</summary>
        public void RefreshCurrent()
        {
            if (current != null && current.gameObject.activeSelf) current.OnShow();
        }

        public void Toast(string message, float seconds = 2f)
        {
            var panel = UIKit.Panel(toastRoot, "Toast", Theme.PanelDark, null, false);
            panel.rectTransform.Place(0.5f, 0.5f, 0, -260, 900, 90);
            var t = UIKit.Label(panel.transform, message, 34, Theme.Text);
            t.rectTransform.Stretch(20, 0, 20, 0);
            StartCoroutine(FadeOut(panel.gameObject, seconds));
        }

        IEnumerator FadeOut(GameObject go, float seconds)
        {
            var group = go.AddComponent<CanvasGroup>();
            float t = 0;
            while (t < seconds)
            {
                t += Time.unscaledDeltaTime;
                group.alpha = Mathf.Clamp01((seconds - t) / 0.4f);
                yield return null;
            }
            Destroy(go);
        }
    }

    /// <summary>Story-Dialoge: Namensschild, Schreibmaschinen-Text, Tippen zum Weiterblättern.</summary>
    public sealed class DialogueOverlay : MonoBehaviour
    {
        Text speaker;
        Image speakerPlate;
        Text body;
        List<DialogueLine> lines;
        int index;
        Action onDone;
        Coroutine typing;
        bool typingDone;

        public bool IsOpen { get { return gameObject.activeSelf; } }

        public static DialogueOverlay Create(Transform parent)
        {
            var dim = UIKit.Flat(parent, "Dialogue", new Color(0.02f, 0.02f, 0.08f, 0.55f), true);
            dim.rectTransform.Stretch();
            var overlay = dim.gameObject.AddComponent<DialogueOverlay>();
            var tap = dim.gameObject.AddComponent<Button>();
            tap.transition = Selectable.Transition.None;
            tap.onClick.AddListener(overlay.Next);

            var box = UIKit.Panel(dim.transform, "Box", Theme.Panel, null, false);
            box.rectTransform.anchorMin = new Vector2(0.05f, 0.03f);
            box.rectTransform.anchorMax = new Vector2(0.95f, 0.36f);
            box.rectTransform.offsetMin = box.rectTransform.offsetMax = Vector2.zero;
            var outline = box.gameObject.AddComponent<Outline>();
            outline.effectColor = Theme.Accent.WithAlpha(0.6f);
            outline.effectDistance = new Vector2(3, -3);

            overlay.speakerPlate = UIKit.Panel(box.transform, "Speaker", Theme.Accent, null, false);
            overlay.speakerPlate.rectTransform.Place(0, 1, 40, 36, 420, 72);
            overlay.speaker = UIKit.Label(overlay.speakerPlate.transform, "", 36, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
            overlay.speaker.rectTransform.Stretch(10, 0, 10, 0);

            overlay.body = UIKit.Label(box.transform, "", 40, Theme.Text, TextAnchor.UpperLeft);
            overlay.body.rectTransform.Stretch(50, 60, 50, 50);
            overlay.body.lineSpacing = 1.15f;

            var hint = UIKit.Label(box.transform, "Tippen ▶", 26, Theme.TextDim, TextAnchor.LowerRight);
            hint.rectTransform.Stretch(0, 0, 30, 14);

            var skip = UIKit.Button(dim.transform, "Überspringen ▸▸", Theme.PanelLight, overlay.Finish, 28);
            skip.GetComponent<RectTransform>().Place(1, 1, -30, -30, 300, 70);

            dim.gameObject.SetActive(false);
            return overlay;
        }

        public void Play(List<DialogueLine> dialogue, Action done)
        {
            if (dialogue == null || dialogue.Count == 0)
            {
                if (done != null) done();
                return;
            }
            lines = dialogue;
            onDone = done;
            index = -1;
            transform.SetAsLastSibling();
            gameObject.SetActive(true);
            Next();
        }

        void Next()
        {
            if (typing != null && !typingDone)
            {
                StopCoroutine(typing);
                body.text = Format(lines[index].Text);
                typingDone = true;
                return;
            }

            index++;
            if (index >= lines.Count)
            {
                Finish();
                return;
            }

            var line = lines[index];
            string name = Format(line.Speaker);
            speakerPlate.gameObject.SetActive(!string.IsNullOrEmpty(name));
            speaker.text = name;
            speakerPlate.color = SpeakerColor(line.Speaker);
            body.fontStyle = line.Speaker == "Erzähler" ? FontStyle.Italic : FontStyle.Normal;
            typing = StartCoroutine(Type(Format(line.Text)));
        }

        IEnumerator Type(string text)
        {
            typingDone = false;
            for (int i = 0; i <= text.Length; i++)
            {
                body.text = text.Substring(0, i);
                yield return new WaitForSecondsRealtime(0.018f);
            }
            typingDone = true;
        }

        void Finish()
        {
            if (!gameObject.activeSelf) return;
            if (typing != null) StopCoroutine(typing);
            gameObject.SetActive(false);
            var done = onDone;
            onDone = null;
            if (done != null) done();
        }

        static string Format(string s)
        {
            var app = GameApp.Instance;
            return app != null && s != null ? s.Replace("{name}", app.Profile.Name) : s;
        }

        static Color SpeakerColor(string speaker)
        {
            if (speaker == "Erzähler") return Theme.PanelLight;
            foreach (var c in GameDatabase.Characters)
                if (c.Name.StartsWith(speaker)) return Theme.Of(c.Element);
            return Theme.Accent;
        }
    }
}
