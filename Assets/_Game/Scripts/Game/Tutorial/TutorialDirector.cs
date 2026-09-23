using System;
using System.Collections.Generic;
using Aether.Core;
using UnityEngine;
using UnityEngine.UI;

namespace Aether.Game
{
    /// <summary>Führt durch die Tutorialschritte und sperrt alles, was gerade nicht dran ist.</summary>
    public sealed class TutorialDirector
    {
        readonly GameApp app;
        List<TutorialStep> steps;
        int index;
        TutorialPhase phase;

        public TutorialDirector(GameApp app)
        {
            this.app = app;
        }

        public TutorialStep Current
        {
            get { return steps != null && index < steps.Count ? steps[index] : null; }
        }

        public bool Active { get { return Current != null; } }

        public void Begin(TutorialPhase tutorialPhase, string startAtId = null)
        {
            phase = tutorialPhase;
            steps = TutorialScript.For(tutorialPhase);
            index = 0;
            if (startAtId != null)
            {
                int i = steps.FindIndex(s => s.Id == startAtId);
                if (i >= 0) index = i;
            }
            Show();
        }

        /// <summary>Geht einen Schritt weiter, wenn einer der Auslöser zum aktuellen Schritt passt (höchstens einmal).</summary>
        public void Notify(params TutorialTrigger[] triggers)
        {
            var step = Current;
            if (step == null || Array.IndexOf(triggers, step.Trigger) < 0) return;
            index++;
            if (Current == null) Finish();
            else Show();
        }

        public bool Allows(TutorialAction action, int handIndex = -1, int moveTo = -1, int unitIndex = -1)
        {
            return TutorialScript.Allows(Current, action, handIndex, moveTo, unitIndex);
        }

        public bool CanPress(string key)
        {
            return TutorialScript.AllowsButton(Current, key);
        }

        public void OnHomeShown()
        {
            if (Active || app.Profile.Tutorial != TutorialPhase.Summon) return;
            var beginner = GameDatabase.Banners[0];
            bool pulled = ProfileService.BeginnerUsed(app.Profile, beginner);
            Begin(TutorialPhase.Summon, pulled ? TutorialScript.TeamStepId : null);
        }

        public void Cancel()
        {
            steps = null;
            app.UI.TutorialOverlay.Hide();
        }

        void Show()
        {
            app.UI.TutorialOverlay.Show(Current, () => Notify(TutorialTrigger.Tap));
        }

        void Finish()
        {
            steps = null;
            app.UI.TutorialOverlay.Hide();
            if (phase == TutorialPhase.Summon)
            {
                ProfileService.CompleteTutorial(app.Profile);
                app.SaveNow();
                app.UI.Toast("+" + Balance.TutorialRewardCrystals + " Kristalle erhalten!", 3f);
                app.UI.RefreshCurrent();
            }
        }
    }

    /// <summary>Hinweisbox mit pulsierendem Rahmen um das Element, das gerade dran ist.</summary>
    public sealed class TutorialOverlay : MonoBehaviour
    {
        Image dim;
        Button dimButton;
        RectTransform frame;
        RectTransform box;
        Text text;
        Text hint;
        TutorialStep step;
        Action onTap;
        RectTransform canvasRect;

        public static TutorialOverlay Create(Transform canvasRoot)
        {
            var canvasGo = new GameObject("TutorialCanvas", typeof(RectTransform));
            canvasGo.layer = 5;
            canvasGo.transform.SetParent(canvasRoot, false);
            var rt = ((RectTransform)canvasGo.transform).Stretch();
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.overrideSorting = true;
            canvas.sortingOrder = 100;
            canvasGo.AddComponent<GraphicRaycaster>();
            var overlay = canvasGo.AddComponent<TutorialOverlay>();
            overlay.canvasRect = rt;

            overlay.dim = UIKit.Flat(rt, "Dim", new Color(0, 0, 0, 0.45f), true);
            overlay.dim.rectTransform.Stretch();
            overlay.dimButton = overlay.dim.gameObject.AddComponent<Button>();
            overlay.dimButton.transition = Selectable.Transition.None;
            overlay.dimButton.onClick.AddListener(() => { if (overlay.onTap != null && overlay.step != null && overlay.step.WaitsForTap) overlay.onTap(); });

            var frameImg = UIKit.Panel(rt, "Frame", Theme.Gold, UIKit.Frame, false);
            overlay.frame = frameImg.rectTransform;
            overlay.frame.anchorMin = overlay.frame.anchorMax = new Vector2(0.5f, 0.5f);

            var boxImg = UIKit.Panel(rt, "Box", Theme.Panel, null, false);
            overlay.box = boxImg.rectTransform;
            overlay.box.anchorMin = overlay.box.anchorMax = overlay.box.pivot = new Vector2(0.5f, 0.5f);
            overlay.box.sizeDelta = new Vector2(1100, 230);
            var outline = boxImg.gameObject.AddComponent<Outline>();
            outline.effectColor = Theme.Gold.WithAlpha(0.8f);
            outline.effectDistance = new Vector2(3, -3);

            var badge = UIKit.Panel(overlay.box, "Badge", Theme.Accent, null, false);
            badge.rectTransform.Place(0, 1, 30, 26, 220, 54);
            var badgeText = UIKit.Label(badge.transform, "TUTORIAL", 28, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
            badgeText.rectTransform.Stretch();

            overlay.text = UIKit.Label(overlay.box, "", 34, Theme.Text, TextAnchor.MiddleLeft);
            overlay.text.rectTransform.Stretch(40, 36, 40, 44);
            overlay.hint = UIKit.Label(overlay.box, "Tippen zum Fortfahren ▶", 24, Theme.Gold, TextAnchor.LowerRight);
            overlay.hint.rectTransform.Stretch(0, 0, 26, 12);

            canvasGo.SetActive(false);
            return overlay;
        }

        public void Show(TutorialStep tutorialStep, Action tap)
        {
            step = tutorialStep;
            onTap = tap;
            if (step == null || string.IsNullOrEmpty(step.Text))
            {
                gameObject.SetActive(step != null);
                box.gameObject.SetActive(false);
                frame.gameObject.SetActive(false);
                dim.color = Color.clear;
                dim.raycastTarget = false;
                return;
            }

            gameObject.SetActive(true);
            box.gameObject.SetActive(true);
            text.text = step.Text;
            hint.gameObject.SetActive(step.WaitsForTap);
            dim.raycastTarget = step.WaitsForTap;
            dim.color = new Color(0, 0, 0, step.WaitsForTap ? 0.45f : 0.12f);
            LateUpdate();
        }

        public void Hide()
        {
            step = null;
            gameObject.SetActive(false);
        }

        void LateUpdate()
        {
            if (step == null || !box.gameObject.activeSelf) return;

            var target = UIAnchors.Find(step.Anchor);
            bool hasTarget = target != null;
            frame.gameObject.SetActive(hasTarget);
            float boxY = 0;

            if (hasTarget)
            {
                var corners = new Vector3[4];
                target.GetWorldCorners(corners);
                Vector2 min, max;
                RectTransformUtility.ScreenPointToLocalPointInRectangle(canvasRect, corners[0], null, out min);
                RectTransformUtility.ScreenPointToLocalPointInRectangle(canvasRect, corners[2], null, out max);
                float pulse = 14f + Mathf.Sin(Time.unscaledTime * 6f) * 6f;
                frame.anchoredPosition = (min + max) * 0.5f;
                frame.sizeDelta = (max - min) + new Vector2(pulse * 2, pulse * 2);

                float height = canvasRect.rect.height;
                bool targetInLowerHalf = (min.y + max.y) * 0.5f < 0;
                boxY = targetInLowerHalf ? height * 0.5f - 190 : -height * 0.5f + 170;
            }
            box.anchoredPosition = new Vector2(0, boxY);
        }
    }
}
