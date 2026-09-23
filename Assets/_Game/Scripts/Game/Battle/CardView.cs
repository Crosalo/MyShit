using System.Collections;
using Aether.Core;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Aether.Game
{
    /// <summary>
    /// Eine Fähigkeitskarte in der Hand. Tippen = einsetzen, Ziehen = verschieben (kostet eine Aktion).
    /// </summary>
    public sealed class CardView : MonoBehaviour, IPointerClickHandler, IBeginDragHandler, IDragHandler, IEndDragHandler
    {
        public const float Width = 178f;
        public const float Height = 244f;

        BattleScreen screen;
        RectTransform rt;
        RectTransform dragLayer;
        RectTransform placeholder;
        CanvasGroup group;
        bool dragging;

        public int Index { get; private set; }
        public SkillCard Card { get; private set; }

        public static CardView Create(Transform row, RectTransform dragLayer, BattleScreen screen, int index, SkillCard card, bool usable)
        {
            var owner = card.Owner;
            var element = Theme.Of(owner.Element);

            var bg = UIKit.Panel(row, "Karte " + index, Theme.Hex("#20244A"));
            bg.Size(Width, Height);
            var view = bg.gameObject.AddComponent<CardView>();
            view.screen = screen;
            view.dragLayer = dragLayer;
            view.rt = bg.rectTransform;
            view.Index = index;
            view.Card = card;
            view.group = bg.gameObject.AddComponent<CanvasGroup>();
            view.group.alpha = usable ? 1f : 0.45f;

            var rankColor = card.Rank >= 3 ? Theme.Gold : card.Rank == 2 ? Theme.Accent2 : new Color(1, 1, 1, 0.25f);
            var outline = bg.gameObject.AddComponent<Outline>();
            outline.effectColor = rankColor;
            outline.effectDistance = card.Rank >= 2 ? new Vector2(4, -4) : new Vector2(2, -2);

            var band = UIKit.Panel(bg.transform, "Held", element, null, false);
            band.rectTransform.anchorMin = new Vector2(0, 1);
            band.rectTransform.anchorMax = new Vector2(1, 1);
            band.rectTransform.pivot = new Vector2(0.5f, 1);
            band.rectTransform.sizeDelta = new Vector2(-12, 48);
            band.rectTransform.anchoredPosition = new Vector2(0, -6);
            var ownerName = UIKit.Label(band.transform, FirstName(owner.Name), 24, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
            ownerName.rectTransform.Stretch();
            ownerName.Outlined(new Color(0, 0, 0, 0.5f), 1.5f);

            var skillName = UIKit.Label(bg.transform, card.Skill.Name, 27, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
            skillName.rectTransform.Stretch(10, 62, 10, 104);

            var kind = UIKit.Label(bg.transform, KindLabel(card.Skill), 20, Theme.TextDim);
            kind.rectTransform.Stretch(8, 138, 8, 70);

            var power = UIKit.Label(bg.transform, PowerLabel(card), 21, element);
            power.rectTransform.Stretch(8, 166, 8, 46);

            var stars = UIKit.Label(bg.transform, Names.RankLabel(card.Rank), 36, card.Rank >= 3 ? Theme.Gold : Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
            stars.rectTransform.Stretch(0, Height - 50, 0, 6);

            if (card.Rank >= 3) bg.gameObject.AddComponent<UIPulse>();
            return view;
        }

        public void PlayMergePop()
        {
            StartCoroutine(Pop());
        }

        IEnumerator Pop()
        {
            float t = 0;
            while (t < 1f)
            {
                t += Time.unscaledDeltaTime * 3.5f;
                float s = 1f + Mathf.Sin(Mathf.Clamp01(t) * Mathf.PI) * 0.3f;
                rt.localScale = new Vector3(s, s, 1);
                yield return null;
            }
            rt.localScale = Vector3.one;
        }

        public void OnPointerClick(PointerEventData eventData)
        {
            if (dragging) return;
            screen.OnCardTapped(Index);
        }

        public void OnBeginDrag(PointerEventData eventData)
        {
            if (!screen.CanDragCards)
            {
                eventData.pointerDrag = null;
                return;
            }
            dragging = true;

            // Platzhalter hält die Lücke in der Reihe offen
            placeholder = UIKit.Rect("Platzhalter", rt.parent);
            placeholder.gameObject.AddComponent<LayoutElement>().preferredWidth = Width;
            placeholder.SetSiblingIndex(rt.GetSiblingIndex());

            rt.SetParent(dragLayer, true);
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.sizeDelta = new Vector2(Width, Height);
            rt.localScale = Vector3.one * 1.1f;
            group.blocksRaycasts = false;
            OnDrag(eventData);
        }

        public void OnDrag(PointerEventData eventData)
        {
            if (!dragging) return;
            Vector2 local;
            if (RectTransformUtility.ScreenPointToLocalPointInRectangle(dragLayer, eventData.position, eventData.pressEventCamera, out local))
                rt.localPosition = local;
        }

        public void OnEndDrag(PointerEventData eventData)
        {
            if (!dragging) return;
            dragging = false;

            // Zielposition = Anzahl der übrigen Karten links vom Finger
            int to = 0;
            var row = placeholder.parent;
            for (int i = 0; i < row.childCount; i++)
            {
                var child = row.GetChild(i);
                if (child == placeholder) continue;
                var other = child.GetComponent<CardView>();
                if (other == null) continue;
                if (other.rt.position.x < eventData.position.x) to++;
            }

            Destroy(placeholder.gameObject);
            screen.OnCardDropped(Index, to);
        }

        static string FirstName(string name)
        {
            int space = name.IndexOf(' ');
            return space > 0 ? name.Substring(0, space) : name;
        }

        public static string KindLabel(SkillDefinition s)
        {
            if (s.IsHeal) return s.Target == TargetType.AllAllies ? "Heilt alle" : "Heilung";
            switch (s.Target)
            {
                case TargetType.AllEnemies: return "Alle Gegner";
                case TargetType.Self: return "Selbst";
                case TargetType.AllAllies: return "Ganzes Team";
                case TargetType.LowestHpAlly: return "Verbündeter";
                default: return "Einzelziel";
            }
        }

        static string PowerLabel(SkillCard card)
        {
            float p = card.Skill.PowerAt(card.Rank);
            if (p > 0f) return Mathf.RoundToInt(p * 100f) + " % ANG";
            if (card.Skill.Effects.Length > 0) return Names.Short(card.Skill.Effects[0].Type);
            return "";
        }
    }

    /// <summary>Sanftes Pulsieren für wichtige Elemente (Rang-3-Karten, bereite Ultimative).</summary>
    public sealed class UIPulse : MonoBehaviour
    {
        public float Amount = 0.04f;
        public float Speed = 5f;

        void Update()
        {
            float s = 1f + Mathf.Sin(Time.unscaledTime * Speed) * Amount;
            transform.localScale = new Vector3(s, s, 1f);
        }

        void OnDisable()
        {
            transform.localScale = Vector3.one;
        }
    }
}
