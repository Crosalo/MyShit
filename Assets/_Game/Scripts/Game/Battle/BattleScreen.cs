using System;
using System.Collections;
using System.Collections.Generic;
using Aether.Core;
using UnityEngine;
using UnityEngine.UI;

namespace Aether.Game
{
    /// <summary>
    /// Kampf-HUD und Steuerung. Planung passiert sofort in der <see cref="BattleEngine"/>,
    /// nach „Kampf!“ werden die Ereignisse der Runde mit Animationen abgespielt.
    /// </summary>
    public sealed class BattleScreen : UIScreen
    {
        sealed class PartyEntry
        {
            public BattleUnit Unit;
            public CanvasGroup Group;
            public Image HpFill;
            public Text HpText;
            public Text Status;
            public Image[] Pips;
            public Button Ult;
            public Image UltImage;
            public UIPulse UltPulse;
        }

        sealed class EnemyHud
        {
            public BattleUnit Unit;
            public RectTransform Root;
            public Image HpFill;
            public Text Status;
        }

        BattleEngine engine;
        StageDefinition stage;
        Action<bool> onFinished;
        BattleArena arena;
        BattleUnit target;
        bool busy = true;
        bool finished;
        int speed = 1;
        float surrenderArmed = -10f;

        RectTransform hudLayer;
        RectTransform fxLayer;
        RectTransform dragLayer;
        RectTransform handRow;
        RectTransform partyRoot;
        Text stageLabel;
        Text waveLabel;
        Text hintLabel;
        Image[] slotImages;
        Text[] slotTexts;
        Button executeButton;
        Button resetButton;
        Button speedButton;
        Button surrenderButton;
        Text banner;
        Coroutine bannerRoutine;
        Text skillLabel;
        Image skillPanel;
        Coroutine skillRoutine;
        RectTransform cutIn;
        Image cutInBand;
        Text cutInName;
        Text cutInSkill;

        readonly List<PartyEntry> party = new List<PartyEntry>();
        readonly List<EnemyHud> enemyHuds = new List<EnemyHud>();
        readonly Dictionary<BattleUnit, int> shownHp = new Dictionary<BattleUnit, int>();
        readonly List<CardView> cards = new List<CardView>();

        TutorialDirector Tutorial { get { return App.Tutorial; } }

        public bool CanDragCards
        {
            get { return !busy && engine != null && engine.Phase == BattlePhase.Planning && engine.FreeSlotCount > 0; }
        }

        // ------------------------------------------------------------------ Aufbau

        protected override void Build()
        {
            hudLayer = UIKit.Rect("HUD", Root).Stretch();

            var info = UIKit.Panel(Root, "Info", Theme.PanelDark, null, false);
            info.rectTransform.Place(0, 1, 24, -20, 520, 104);
            stageLabel = UIKit.Label(info.transform, "", 32, Theme.Text, TextAnchor.UpperLeft, FontStyle.Bold);
            stageLabel.rectTransform.Stretch(22, 12, 16, 50);
            waveLabel = UIKit.Label(info.transform, "", 26, Theme.TextDim, TextAnchor.LowerLeft);
            waveLabel.rectTransform.Stretch(22, 50, 16, 12);

            speedButton = UIKit.Button(Root, "1×", Theme.PanelLight, ToggleSpeed, 32);
            speedButton.GetComponent<RectTransform>().Place(1, 1, -250, -24, 110, 80);
            surrenderButton = UIKit.Button(Root, "Aufgeben", Theme.Hex("#5A2340"), Surrender, 26);
            surrenderButton.GetComponent<RectTransform>().Place(1, 1, -24, -24, 210, 80);

            partyRoot = UIKit.Rect("Team", Root);
            partyRoot.Place(0, 1, 24, -150, 560, 390);

            // Aktionsslots
            var slotsRoot = UIKit.Rect("Aktionen", Root);
            slotsRoot.Place(0.5f, 0, -60, 290, 600, 96);
            UIAnchors.Register("battle.slots", slotsRoot);
            slotImages = new Image[Balance.ActionsPerTurn];
            slotTexts = new Text[Balance.ActionsPerTurn];
            for (int i = 0; i < slotImages.Length; i++)
            {
                var slot = UIKit.Panel(slotsRoot, "Slot " + i, Theme.PanelDark, null, false);
                slot.rectTransform.Place(0, 0.5f, i * 204, 0, 188, 92);
                var o = slot.gameObject.AddComponent<Outline>();
                o.effectColor = new Color(1, 1, 1, 0.25f);
                o.effectDistance = new Vector2(2, -2);
                slotImages[i] = slot;
                slotTexts[i] = UIKit.Label(slot.transform, "", 22, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
                slotTexts[i].rectTransform.Stretch(6, 4, 6, 4);
            }
            var slotsTitle = UIKit.Label(slotsRoot, "AKTIONEN", 20, Theme.TextDim, TextAnchor.LowerLeft, FontStyle.Bold);
            slotsTitle.rectTransform.Place(0, 1, 4, 30, 300, 30);

            hintLabel = UIKit.Label(Root, "", 24, Theme.TextDim);
            hintLabel.rectTransform.Place(0.5f, 0, -60, 262, 900, 30);

            // Kartenhand
            var handBg = UIKit.Panel(Root, "Hand", new Color(0, 0, 0, 0.35f), null, false);
            handBg.rectTransform.Place(0.5f, 0, -60, 8, 1330, 262);
            handRow = UIKit.Rect("Karten", handBg.transform).Stretch(8, 8, 8, 8);
            handRow.HList(10, 0, TextAnchor.MiddleCenter, false);
            UIAnchors.Register("battle.hand", handBg.rectTransform);

            executeButton = UIKit.Button(Root, "Kampf!", Theme.Accent, Execute, 44);
            executeButton.GetComponent<RectTransform>().Place(1, 0, -24, 130, 250, 130);
            UIAnchors.Register("battle.execute", executeButton.GetComponent<RectTransform>());
            resetButton = UIKit.Button(Root, "Zurücksetzen", Theme.PanelLight, ResetPlanning, 26);
            resetButton.GetComponent<RectTransform>().Place(1, 0, -24, 24, 250, 90);

            fxLayer = UIKit.Rect("Effekte", Root).Stretch();

            // Banner in der Mitte
            banner = UIKit.Label(Root, "", 110, Theme.Gold, TextAnchor.MiddleCenter, FontStyle.Bold);
            banner.rectTransform.Place(0.5f, 0.5f, 0, 120, 1600, 180);
            banner.Outlined(new Color(0.1f, 0, 0.2f, 0.9f), 5f);
            banner.gameObject.SetActive(false);

            skillPanel = UIKit.Panel(Root, "Fähigkeit", Theme.PanelDark, null, false);
            skillPanel.rectTransform.Place(0.5f, 1, 0, -24, 760, 80);
            skillLabel = UIKit.Label(skillPanel.transform, "", 34, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
            skillLabel.rectTransform.Stretch(12, 0, 12, 0);
            skillPanel.gameObject.SetActive(false);

            BuildCutIn();
            dragLayer = UIKit.Rect("Ziehen", Root).Stretch();
        }

        void BuildCutIn()
        {
            cutIn = UIKit.Rect("CutIn", Root).Stretch();
            var dim = UIKit.Flat(cutIn, "Dim", new Color(0, 0, 0, 0.55f));
            dim.rectTransform.Stretch();
            cutInBand = UIKit.Flat(cutIn, "Band", Theme.Accent);
            cutInBand.rectTransform.Place(0.5f, 0.5f, 0, 0, 2600, 300);
            cutInBand.rectTransform.localEulerAngles = new Vector3(0, 0, 6);
            var stripe = UIKit.Flat(cutInBand.transform, "Streifen", new Color(1, 1, 1, 0.85f));
            stripe.rectTransform.anchorMin = new Vector2(0, 0);
            stripe.rectTransform.anchorMax = new Vector2(1, 0);
            stripe.rectTransform.sizeDelta = new Vector2(0, 14);
            cutInName = UIKit.Label(cutInBand.transform, "", 96, Theme.Text, TextAnchor.MiddleCenter, FontStyle.BoldAndItalic);
            cutInName.rectTransform.Stretch(0, 20, 0, 110);
            cutInName.Outlined(new Color(0, 0, 0, 0.6f), 4f);
            cutInSkill = UIKit.Label(cutInBand.transform, "", 52, Theme.Gold, TextAnchor.MiddleCenter, FontStyle.Bold);
            cutInSkill.rectTransform.Stretch(0, 180, 0, 20);
            cutInSkill.Outlined(new Color(0, 0, 0, 0.6f), 3f);
            cutIn.gameObject.SetActive(false);
        }

        // ------------------------------------------------------------------ Start

        /// <summary>Baut den Kampf auf (läuft schon während des Intro-Dialogs im Hintergrund).</summary>
        public void Prepare(StageDefinition battleStage)
        {
            EnsureBuilt();
            stage = battleStage;
            finished = false;
            busy = true;
            engine = new BattleEngine(BattleFactory.Create(stage, App.Profile, App.Random));

            arena = App.Stage.Arena;
            arena.UnitClicked -= OnUnitClicked;
            arena.UnitClicked += OnUnitClicked;
            arena.Clear();
            arena.SpawnPlayers(engine.Players);
            arena.SpawnEnemies(engine.Enemies);

            shownHp.Clear();
            foreach (var p in engine.Players) shownHp[p] = p.Hp;
            for (int w = 0; w < engine.WaveCount; w++)
                foreach (var e in engine.Wave(w)) shownHp[e] = e.Hp;

            BuildParty();
            BuildEnemyHuds();
            SelectTarget(null);
            stageLabel.text = (stage.IsBoss ? "BOSS · " : "") + stage.Code + "  " + stage.Name;
            SetSpeed(1);
            cutIn.gameObject.SetActive(false);
            banner.gameObject.SetActive(false);
            RefreshAll();
        }

        public void Begin(StageDefinition battleStage, Action<bool> finishedCallback)
        {
            onFinished = finishedCallback;
            busy = false;
            if (stage == GameDatabase.Prologue && App.Profile.Tutorial == TutorialPhase.Battle)
                Tutorial.Begin(TutorialPhase.Battle);
            ShowBanner("Kampfbeginn!", Theme.Accent2, 1f);
            RefreshAll();
        }

        public override void OnHide()
        {
            Time.timeScale = 1f;
            if (arena != null) arena.UnitClicked -= OnUnitClicked;
            StopAllCoroutines();
        }

        void Update()
        {
            if (engine == null) return;
            var cam = App.Stage.Camera;
            foreach (var hud in enemyHuds)
            {
                var view = arena.ViewOf(hud.Unit);
                bool visible = view != null && view.gameObject.activeInHierarchy;
                if (hud.Root.gameObject.activeSelf != visible) hud.Root.gameObject.SetActive(visible);
                if (!visible) continue;
                var screen = cam.WorldToScreenPoint(view.HeadPosition);
                Vector2 local;
                if (RectTransformUtility.ScreenPointToLocalPointInRectangle(hudLayer, screen, null, out local))
                    hud.Root.localPosition = local;
            }
        }

        // ------------------------------------------------------------------ Eingaben (Planung)

        public void OnCardTapped(int index)
        {
            if (busy || engine.Phase != BattlePhase.Planning) return;
            if (!Tutorial.Allows(TutorialAction.UseCard, index))
            {
                App.UI.Toast("Folge dem Hinweis des Tutorials.");
                return;
            }
            if (engine.FreeSlotCount == 0)
            {
                App.UI.Toast("Alle Aktionen verplant – tippe auf „Kampf!“");
                return;
            }
            var card = engine.Hand[index];
            if (!engine.CanAct(card.Owner))
            {
                App.UI.Toast(card.Owner.Name + " kann gerade nicht handeln.");
                return;
            }

            var result = engine.UseCard(index, target);
            if (!result.Success) return;
            var view = arena.ViewOf(card.Owner);
            if (view != null) Vfx.Rise(view.transform.position, Theme.Of(card.Owner.Element), 6);
            RefreshAll(result.Merges);
            if (result.Merges.Count > 0) Tutorial.Notify(TutorialTrigger.CardUsed, TutorialTrigger.CardsMerged);
            else Tutorial.Notify(TutorialTrigger.CardUsed);
        }

        public void OnCardDropped(int from, int to)
        {
            if (busy || from == to || !Tutorial.Allows(TutorialAction.MoveCard, from, to))
            {
                if (!busy && from != to) App.UI.Toast("Folge dem Hinweis des Tutorials.");
                RefreshHand(null);
                return;
            }
            var result = engine.MoveCard(from, to);
            RefreshAll(result.Merges);
            if (!result.Success) return;
            if (result.Merges.Count > 0) Tutorial.Notify(TutorialTrigger.CardMoved, TutorialTrigger.CardsMerged);
            else Tutorial.Notify(TutorialTrigger.CardMoved);
        }

        void OnUltimate(int unitIndex)
        {
            if (busy) return;
            var unit = engine.Players[unitIndex];
            if (!Tutorial.Allows(TutorialAction.UseUltimate, -1, -1, unitIndex))
            {
                App.UI.Toast("Folge dem Hinweis des Tutorials.");
                return;
            }
            if (!engine.CanUseUltimate(unit))
            {
                App.UI.Toast(unit.UltimateReady ? "Kein freier Aktionsslot." : "Die Ultimativ-Leiste ist noch nicht voll.");
                return;
            }
            engine.UseUltimate(unit, target);
            RefreshAll();
            Tutorial.Notify(TutorialTrigger.UltimateUsed);
        }

        void OnUnitClicked(BattleUnit unit)
        {
            if (busy || unit.IsPlayer || !unit.IsAlive) return;
            SelectTarget(unit);
        }

        void SelectTarget(BattleUnit unit)
        {
            if (unit == null || !unit.IsAlive)
            {
                unit = null;
                foreach (var e in engine.Enemies) if (e.IsAlive) { unit = e; break; }
            }
            target = unit;
            arena.SetTarget(target);
        }

        void ResetPlanning()
        {
            if (busy) return;
            if (!Tutorial.CanPress("battle.reset"))
            {
                App.UI.Toast("Folge dem Hinweis des Tutorials.");
                return;
            }
            engine.ResetPlanning();
            RefreshAll();
        }

        void ToggleSpeed()
        {
            SetSpeed(speed == 1 ? 2 : 1);
        }

        void SetSpeed(int value)
        {
            speed = value;
            Time.timeScale = speed;
            speedButton.SetLabel(speed + "×");
        }

        void Surrender()
        {
            if (busy || finished) return;
            if (!Tutorial.CanPress("battle.surrender"))
            {
                App.UI.Toast("Im Tutorial kannst du nicht aufgeben.");
                return;
            }
            if (Time.unscaledTime - surrenderArmed > 3f)
            {
                surrenderArmed = Time.unscaledTime;
                surrenderButton.SetLabel("Sicher?");
                return;
            }
            engine.Surrender();
            Finish(false);
        }

        void Execute()
        {
            if (busy || engine.Phase != BattlePhase.Planning) return;
            if (!Tutorial.Allows(TutorialAction.Execute))
            {
                App.UI.Toast("Folge dem Hinweis des Tutorials.");
                return;
            }
            StartCoroutine(RunTurn());
        }

        // ------------------------------------------------------------------ Ausführung

        IEnumerator RunTurn()
        {
            busy = true;
            RefreshAll();
            var events = engine.ExecuteTurn();
            yield return Play(events);

            foreach (var kv in new List<BattleUnit>(shownHp.Keys)) shownHp[kv] = kv.Hp;
            busy = false;

            if (engine.Phase == BattlePhase.Victory)
            {
                Tutorial.Notify(TutorialTrigger.BattleWon);
                Finish(true);
                yield break;
            }
            if (engine.Phase == BattlePhase.Defeat)
            {
                Finish(false);
                yield break;
            }

            if (target == null || !target.IsAlive) SelectTarget(null);
            RefreshAll();
            Tutorial.Notify(TutorialTrigger.TurnExecuted);
        }

        void Finish(bool victory)
        {
            if (finished) return;
            finished = true;
            busy = true;
            RefreshAll();
            Time.timeScale = 1f;
            if (onFinished != null) onFinished(victory);
        }

        IEnumerator Play(List<BattleEvent> events)
        {
            foreach (var ev in events)
            {
                switch (ev.Type)
                {
                    case BattleEventType.ActionStarted:
                    {
                        ShowSkill(ev);
                        if (ev.IsUltimate) yield return CutIn(ev.Source, ev.Skill);
                        var view = arena.ViewOf(ev.Source);
                        if (view != null && view.gameObject.activeInHierarchy) yield return view.Lunge(ev.IsUltimate);
                        break;
                    }
                    case BattleEventType.Damage:
                    {
                        var view = arena.ViewOf(ev.Target);
                        shownHp[ev.Target] = Mathf.Max(0, Shown(ev.Target) - ev.Amount);
                        if (view != null)
                        {
                            view.Hit();
                            var color = ev.IsBurn ? Theme.Hex("#FF8A3D") : Theme.Of(ev.Source != null ? ev.Source.Element : Element.Fire);
                            Vfx.Burst(view.CenterPosition, color, ev.Critical ? 16 : 9);
                            string text = ev.Amount.ToString();
                            Color textColor = ev.IsBurn ? Theme.Hex("#FF8A3D") : ev.Target.IsPlayer ? Theme.Danger : Theme.Text;
                            FloatText(view.HeadPosition, ev.Critical ? text + "!" : text, ev.Critical ? Theme.Gold : textColor, ev.Critical ? 68 : 52, 0);
                            if (ev.Absorbed > 0) FloatText(view.HeadPosition, "Schild -" + ev.Absorbed, Theme.Accent2, 28, -60);
                            if (ev.ElementMultiplier > 1f) FloatText(view.HeadPosition, "EFFEKTIV!", Theme.Gold, 32, 70);
                            else if (ev.ElementMultiplier < 1f) FloatText(view.HeadPosition, "schwach", Theme.TextDim, 28, 70);
                            if (ev.Critical || ev.Amount > ev.Target.MaxHp / 4) App.Stage.Shake(0.12f, 0.2f);
                        }
                        RefreshBars();
                        yield return new WaitForSeconds(0.2f);
                        break;
                    }
                    case BattleEventType.Heal:
                    {
                        var view = arena.ViewOf(ev.Target);
                        shownHp[ev.Target] = Mathf.Min(ev.Target.MaxHp, Shown(ev.Target) + ev.Amount);
                        if (view != null)
                        {
                            Vfx.Rise(view.transform.position, Theme.Success);
                            FloatText(view.HeadPosition, "+" + ev.Amount, Theme.Success, 50, 0);
                        }
                        RefreshBars();
                        yield return new WaitForSeconds(0.15f);
                        break;
                    }
                    case BattleEventType.StatusApplied:
                    {
                        var view = arena.ViewOf(ev.Target);
                        bool good = ev.Status == StatusType.AttackUp || ev.Status == StatusType.DefenseUp || ev.Status == StatusType.Shield;
                        if (view != null) FloatText(view.HeadPosition, Names.Short(ev.Status), good ? Theme.Buff : Theme.Debuff, 30, 110);
                        yield return new WaitForSeconds(0.08f);
                        break;
                    }
                    case BattleEventType.Stunned:
                    {
                        var view = arena.ViewOf(ev.Source);
                        if (view != null) FloatText(view.HeadPosition, "BETÄUBT", Theme.Debuff, 36, 0);
                        yield return new WaitForSeconds(0.4f);
                        break;
                    }
                    case BattleEventType.Death:
                    {
                        var view = arena.ViewOf(ev.Target);
                        if (view != null) yield return view.Die();
                        if (!ev.Target.IsPlayer && ev.Target == target) SelectTarget(null);
                        RefreshBars();
                        break;
                    }
                    case BattleEventType.WaveCleared:
                        ShowBanner("Welle geschafft!", Theme.Accent2, 0.8f);
                        yield return new WaitForSeconds(0.8f);
                        break;
                    case BattleEventType.WaveStarted:
                        arena.SpawnEnemies(engine.Wave(ev.Wave));
                        BuildEnemyHuds();
                        SelectTarget(null);
                        UpdateLabels(ev.Wave);
                        ShowBanner(ev.Wave == engine.WaveCount - 1 && stage.IsBoss ? "BOSS!" : "Welle " + (ev.Wave + 1) + "/" + engine.WaveCount,
                            ev.Wave == engine.WaveCount - 1 && stage.IsBoss ? Theme.Danger : Theme.Accent2, 1f);
                        yield return new WaitForSeconds(1f);
                        break;
                    case BattleEventType.Victory:
                        ShowBanner("SIEG!", Theme.Gold, 1.6f);
                        yield return new WaitForSeconds(1.4f);
                        break;
                    case BattleEventType.Defeat:
                        ShowBanner("NIEDERLAGE", Theme.Danger, 1.6f);
                        yield return new WaitForSeconds(1.4f);
                        break;
                    case BattleEventType.TurnStarted:
                        ShowBanner("Runde " + ev.Turn, Theme.Text, 0.6f);
                        break;
                }
            }
        }

        int Shown(BattleUnit unit)
        {
            int hp;
            return shownHp.TryGetValue(unit, out hp) ? hp : unit.Hp;
        }

        IEnumerator CutIn(BattleUnit unit, SkillDefinition skill)
        {
            cutIn.gameObject.SetActive(true);
            cutIn.SetAsLastSibling();
            cutInBand.color = Theme.Of(unit.Element);
            cutInName.text = unit.Name;
            cutInSkill.text = "✦ " + skill.Name + " ✦";
            var band = cutInBand.rectTransform;
            float t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime * 5f;
                band.anchoredPosition = new Vector2(Mathf.Lerp(-2600, 0, 1f - Mathf.Pow(1f - Mathf.Clamp01(t), 3f)), 0);
                yield return null;
            }
            yield return new WaitForSeconds(0.7f);
            t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime * 6f;
                band.anchoredPosition = new Vector2(Mathf.Lerp(0, 2600, t * t), 0);
                yield return null;
            }
            cutIn.gameObject.SetActive(false);
        }

        void ShowSkill(BattleEvent ev)
        {
            if (skillRoutine != null) StopCoroutine(skillRoutine);
            skillRoutine = StartCoroutine(SkillRoutine(ev));
        }

        IEnumerator SkillRoutine(BattleEvent ev)
        {
            skillPanel.gameObject.SetActive(true);
            skillPanel.color = (ev.Source.IsPlayer ? Theme.Of(ev.Source.Element) * 0.6f : Theme.Hex("#5A2340")).WithAlpha(0.9f);
            string rank = ev.IsUltimate ? "ULTIMATIV" : Names.RankLabel(ev.Rank);
            skillLabel.text = ev.Source.Name + ": " + ev.Skill.Name + "  " + rank;
            yield return new WaitForSeconds(1.1f);
            skillPanel.gameObject.SetActive(false);
        }

        void ShowBanner(string text, Color color, float seconds)
        {
            if (bannerRoutine != null) StopCoroutine(bannerRoutine);
            bannerRoutine = StartCoroutine(BannerRoutine(text, color, seconds));
        }

        IEnumerator BannerRoutine(string text, Color color, float seconds)
        {
            banner.gameObject.SetActive(true);
            banner.text = text;
            banner.color = color;
            float t = 0;
            while (t < seconds)
            {
                t += Time.deltaTime;
                float k = Mathf.Clamp01(t / 0.18f);
                float s = Mathf.Lerp(1.6f, 1f, k);
                banner.rectTransform.localScale = new Vector3(s, s, 1);
                var c = banner.color;
                c.a = Mathf.Clamp01((seconds - t) / 0.25f);
                banner.color = c;
                yield return null;
            }
            banner.gameObject.SetActive(false);
        }

        void FloatText(Vector3 world, string text, Color color, int size, float offsetX)
        {
            var screen = App.Stage.Camera.WorldToScreenPoint(world);
            Vector2 local;
            if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(fxLayer, screen, null, out local)) return;
            var label = UIKit.Label(fxLayer, text, size, color, TextAnchor.MiddleCenter, FontStyle.Bold);
            label.Outlined(new Color(0, 0, 0, 0.8f), 3f);
            label.rectTransform.sizeDelta = new Vector2(500, 100);
            label.rectTransform.localPosition = local + new Vector2(offsetX, UnityEngine.Random.Range(-10f, 10f));
            StartCoroutine(FloatRoutine(label));
        }

        IEnumerator FloatRoutine(Text label)
        {
            var start = label.rectTransform.localPosition;
            var color = label.color;
            float t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime * 1.1f;
                label.rectTransform.localPosition = start + Vector3.up * (90f * Mathf.Sqrt(Mathf.Clamp01(t)));
                float s = t < 0.12f ? Mathf.Lerp(1.5f, 1f, t / 0.12f) : 1f;
                label.rectTransform.localScale = new Vector3(s, s, 1);
                color.a = Mathf.Clamp01((1f - t) / 0.3f);
                label.color = color;
                yield return null;
            }
            Destroy(label.gameObject);
        }

        // ------------------------------------------------------------------ Anzeige

        void BuildParty()
        {
            partyRoot.ClearChildren();
            party.Clear();
            for (int i = 0; i < engine.Players.Count; i++)
            {
                var unit = engine.Players[i];
                var entry = new PartyEntry { Unit = unit };
                var panel = UIKit.Panel(partyRoot, unit.Name, Theme.PanelDark, null, false);
                panel.rectTransform.Place(0, 1, 0, -i * 128, 430, 118);
                entry.Group = panel.gameObject.AddComponent<CanvasGroup>();

                var portrait = UIKit.Panel(panel.transform, "Portrait", Theme.Hex(unit.Character.HairColor), UIKit.Circle, false);
                portrait.type = Image.Type.Simple;
                portrait.rectTransform.Place(0, 0.5f, 12, 0, 88, 88);
                var ring = portrait.gameObject.AddComponent<Outline>();
                ring.effectColor = Theme.Of(unit.Element);
                ring.effectDistance = new Vector2(4, -4);
                var initial = UIKit.Label(portrait.transform, unit.Name.Substring(0, 1), 46, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
                initial.rectTransform.Stretch();
                initial.Outlined(new Color(0, 0, 0, 0.6f), 2f);

                var name = UIKit.Label(panel.transform, unit.Name + "  <size=20>Lv " + unit.Level + "</size>", 26, Theme.Text, TextAnchor.UpperLeft, FontStyle.Bold);
                name.rectTransform.Stretch(114, 8, 10, 70);

                Image fill;
                var bar = UIKit.Bar(panel.transform, new Color(0, 0, 0, 0.6f), Theme.Success, out fill);
                bar.Place(0, 1, 114, -44, 300, 22);
                entry.HpFill = fill;
                entry.HpText = UIKit.Label(bar, "", 18, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
                entry.HpText.rectTransform.Stretch();
                entry.HpText.Outlined(new Color(0, 0, 0, 0.8f), 1.5f);

                entry.Pips = new Image[Balance.MaxGauge];
                for (int p = 0; p < entry.Pips.Length; p++)
                {
                    var pip = UIKit.Panel(panel.transform, "Pip", Theme.Disabled, null, false);
                    pip.rectTransform.Place(0, 0, 114 + p * 38, 30, 32, 14);
                    entry.Pips[p] = pip;
                }
                entry.Status = UIKit.Label(panel.transform, "", 18, Theme.Buff, TextAnchor.LowerLeft);
                entry.Status.rectTransform.Place(0, 0, 114, 4, 310, 24);

                int index = i;
                entry.Ult = UIKit.Button(partyRoot, "ULT", Theme.Disabled, () => OnUltimate(index), 30);
                var ultRt = entry.Ult.GetComponent<RectTransform>();
                ultRt.Place(0, 1, 442, -i * 128 - 9, 100, 100);
                entry.UltImage = entry.Ult.GetComponent<Image>();
                entry.UltImage.sprite = UIKit.Circle;
                entry.UltImage.type = Image.Type.Simple;
                entry.UltPulse = entry.Ult.gameObject.AddComponent<UIPulse>();
                entry.UltPulse.Amount = 0.08f;
                UIAnchors.Register("battle.ult." + i, ultRt);
                party.Add(entry);
            }
        }

        void BuildEnemyHuds()
        {
            foreach (var h in enemyHuds) if (h.Root != null) Destroy(h.Root.gameObject);
            enemyHuds.Clear();
            foreach (var unit in engine.Enemies)
            {
                var hud = new EnemyHud { Unit = unit };
                bool boss = unit.Enemy.IsBoss;
                var panel = UIKit.Panel(hudLayer, unit.Name, Theme.PanelDark, null, false);
                panel.rectTransform.anchorMin = panel.rectTransform.anchorMax = new Vector2(0.5f, 0.5f);
                panel.rectTransform.pivot = new Vector2(0.5f, 0);
                panel.rectTransform.sizeDelta = new Vector2(boss ? 360 : 250, 64);
                hud.Root = panel.rectTransform;

                var name = UIKit.Label(panel.transform, (boss ? "BOSS " : "") + unit.Name + " <size=16>Lv " + unit.Level + "</size>", 20,
                    boss ? Theme.Danger : Theme.Text, TextAnchor.UpperCenter, FontStyle.Bold);
                name.rectTransform.Stretch(6, 4, 6, 30);
                var element = UIKit.Panel(panel.transform, "Element", Theme.Of(unit.Element), UIKit.Circle, false);
                element.type = Image.Type.Simple;
                element.rectTransform.Place(0, 0, 8, 10, 20, 20);

                Image fill;
                var bar = UIKit.Bar(panel.transform, new Color(0, 0, 0, 0.6f), Theme.Danger, out fill);
                bar.Place(0, 0, 34, 8, (boss ? 360 : 250) - 44, 22);
                hud.HpFill = fill;
                hud.Status = UIKit.Label(panel.transform, "", 18, Theme.Debuff, TextAnchor.UpperCenter);
                hud.Status.rectTransform.Place(0.5f, 0, 0, -26, 300, 24);
                enemyHuds.Add(hud);
            }
        }

        void RefreshAll(List<MergeInfo> merges = null)
        {
            RefreshHand(merges);
            RefreshSlots();
            RefreshBars();
            UpdateLabels(engine.WaveIndex);

            bool planning = !busy && engine.Phase == BattlePhase.Planning;
            executeButton.interactable = planning;
            resetButton.interactable = planning && engine.HasPlannedActions;
            surrenderButton.interactable = planning;
            if (Time.unscaledTime - surrenderArmed > 3f) surrenderButton.SetLabel("Aufgeben");

            if (!planning) hintLabel.text = "";
            else if (engine.FreeSlotCount == 0) hintLabel.text = "Alle Aktionen verplant – tippe auf „Kampf!“";
            else hintLabel.text = "Tippen = einsetzen · Ziehen = verschieben (kostet 1 Aktion) · Gegner antippen = Ziel";
        }

        void RefreshHand(List<MergeInfo> merges)
        {
            handRow.ClearChildren();
            cards.Clear();
            for (int i = 0; i < engine.Hand.Count; i++)
            {
                var card = engine.Hand[i];
                bool usable = !busy && engine.CanUseCard(i);
                var view = CardView.Create(handRow, dragLayer, this, i, card, usable);
                UIAnchors.Register("battle.card." + i, view.GetComponent<RectTransform>());
                cards.Add(view);
                if (merges != null)
                    foreach (var m in merges)
                        if (m.Result.Uid == card.Uid) view.PlayMergePop();
            }
            if (merges != null && merges.Count > 0)
            {
                var best = 1;
                foreach (var m in merges) best = Mathf.Max(best, m.Result.Rank);
                ShowBanner(best >= 3 ? "Rang 3!" : "Verschmolzen!", best >= 3 ? Theme.Gold : Theme.Accent2, 0.7f);
            }
        }

        void RefreshSlots()
        {
            for (int i = 0; i < slotImages.Length; i++)
            {
                var slot = engine.Slots[i];
                switch (slot.State)
                {
                    case SlotState.Card:
                        slotImages[i].color = (Theme.Of(slot.Card.Owner.Element) * 0.75f).WithAlpha(0.95f);
                        slotTexts[i].text = slot.Card.IsUltimate
                            ? "ULTIMATIV\n<size=18>" + slot.Card.Owner.Name + "</size>"
                            : slot.Card.Skill.Name + "\n<size=20>" + Names.RankLabel(slot.Card.Rank) + "</size>";
                        break;
                    case SlotState.Locked:
                        slotImages[i].color = Theme.Hex("#3A1830");
                        slotTexts[i].text = "GESPERRT\n<size=18>Karte verschoben</size>";
                        break;
                    default:
                        slotImages[i].color = Theme.PanelDark;
                        slotTexts[i].text = "<color=#A9ADD6>" + (i + 1) + "</color>";
                        break;
                }
            }
        }

        void RefreshBars()
        {
            foreach (var entry in party)
            {
                var u = entry.Unit;
                int hp = Shown(u);
                entry.HpFill.SetFill(hp / (float)u.MaxHp);
                entry.HpFill.color = hp < u.MaxHp * 0.3f ? Theme.Danger : Theme.Success;
                entry.HpText.text = hp + " / " + u.MaxHp;
                entry.Group.alpha = hp > 0 ? 1f : 0.4f;
                for (int p = 0; p < entry.Pips.Length; p++)
                    entry.Pips[p].color = p < u.Gauge ? Theme.Gold : Theme.Disabled;
                entry.Status.text = StatusText(u);

                bool ready = u.UltimateReady && u.IsAlive;
                entry.UltImage.color = ready ? Theme.Gold : Theme.Disabled;
                entry.UltPulse.enabled = ready && !busy;
                entry.Ult.interactable = !busy;
            }

            foreach (var hud in enemyHuds)
            {
                hud.HpFill.SetFill(Shown(hud.Unit) / (float)hud.Unit.MaxHp);
                hud.Status.text = StatusText(hud.Unit);
            }
        }

        void UpdateLabels(int wave)
        {
            waveLabel.text = "Welle " + (wave + 1) + "/" + engine.WaveCount + "   ·   Runde " + engine.Turn;
        }

        static string StatusText(BattleUnit u)
        {
            if (!u.IsAlive || u.Statuses.Count == 0) return "";
            var parts = new List<string>();
            foreach (var s in u.Statuses) parts.Add(Names.Short(s.Type) + (s.Type == StatusType.Shield ? " " + s.Amount : ""));
            return string.Join("  ", parts.ToArray());
        }
    }
}
