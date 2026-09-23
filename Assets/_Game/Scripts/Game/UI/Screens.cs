using System.Collections;
using System.Collections.Generic;
using Aether.Core;
using UnityEngine;
using UnityEngine.UI;

namespace Aether.Game
{
    // ====================================================================== Hauptmenü

    public sealed class HomeScreen : UIScreen
    {
        HeaderBar header;
        Text leaderName;
        Text power;
        Button daily;
        float resetArmed = -10f;
        Button resetButton;

        protected override void Build()
        {
            header = HeaderBar.Create(Root, "", null);
            var logo = UIKit.Label(Root, "AETHER\n<size=54>CHRONICLES</size>", 96, Theme.Text, TextAnchor.UpperLeft, FontStyle.BoldAndItalic);
            logo.rectTransform.Place(0, 1, 40, -20, 900, 240);
            logo.Outlined(Theme.Accent.WithAlpha(0.8f), 4f);

            var menu = UIKit.Rect("Menü", Root);
            menu.Place(1, 0.5f, -50, -40, 520, 560);
            menu.VList(22);
            UIKit.Button(menu, "Story", Theme.Accent, () => App.GoStory(), 46, "home.story").Size(-1, 120);
            UIKit.Button(menu, "Beschwörung", Theme.Hex("#7B5CFF"), () => App.GoGacha(), 46, "home.gacha").Size(-1, 120);
            UIKit.Button(menu, "Team", Theme.Hex("#2E8BC0"), () => App.GoTeam(), 46, "home.team").Size(-1, 120);
            daily = UIKit.Button(menu, "Tagesbonus", Theme.Hex("#C8A04A"), ClaimDaily, 38, "home.daily");
            daily.Size(-1, 100);

            var plate = UIKit.Panel(Root, "Anführer", Theme.PanelDark, null, false);
            plate.rectTransform.Place(0, 0, 40, 40, 700, 130);
            leaderName = UIKit.Label(plate.transform, "", 36, Theme.Text, TextAnchor.UpperLeft, FontStyle.Bold);
            leaderName.rectTransform.Stretch(26, 16, 20, 50);
            power = UIKit.Label(plate.transform, "", 28, Theme.Gold, TextAnchor.LowerLeft);
            power.rectTransform.Stretch(26, 60, 20, 16);

            resetButton = UIKit.Button(Root, "Spielstand löschen", Theme.Hex("#3A1830"), ResetSave, 22, "home.reset");
            resetButton.GetComponent<RectTransform>().Place(1, 0, -50, 30, 300, 60);
        }

        public override void OnShow()
        {
            header.Refresh();
            var p = App.Profile;
            var leader = p.Team.Count > 0 ? GameDatabase.FindCharacter(p.Team[0]) : null;
            leaderName.text = leader != null ? leader.Name + "  <size=24><color=#A9ADD6>" + leader.Title + "</color></size>" : "";
            power.text = "Team-Kampfkraft " + ProfileService.TeamPower(p).ToString("N0");
            daily.interactable = ProfileService.CanClaimDaily(p, GameApp.Today());
            daily.SetLabel(daily.interactable ? "Tagesbonus ✦" : "Bonus abgeholt");
            resetButton.SetLabel("Spielstand löschen");
        }

        void ClaimDaily()
        {
            if (ProfileService.ClaimDaily(App.Profile, GameApp.Today()))
            {
                App.SaveNow();
                App.UI.Toast("+" + Balance.DailyCrystals + " Kristalle, +" + Balance.DailyGold + " Gold");
            }
            OnShow();
        }

        void ResetSave()
        {
            if (Time.unscaledTime - resetArmed > 3f)
            {
                resetArmed = Time.unscaledTime;
                resetButton.SetLabel("Wirklich löschen?");
                return;
            }
            App.ResetProfile();
        }
    }

    // ====================================================================== Story

    public sealed class StoryScreen : UIScreen
    {
        HeaderBar header;
        RectTransform chapterList;
        RectTransform stageList;
        Text chapterTitle;
        Text chapterSummary;
        string chapterId = "ch0";

        protected override void Build()
        {
            header = HeaderBar.Create(Root, "Story", () => App.GoHome());
            var bg = UIKit.Flat(Root, "BG", new Color(0.03f, 0.03f, 0.1f, 0.6f));
            bg.rectTransform.Stretch(0, 110, 0, 0);
            bg.transform.SetAsFirstSibling();

            chapterList = UIKit.Rect("Kapitel", Root);
            chapterList.Place(0, 1, 30, -140, 420, 800);
            chapterList.VList(16);

            var right = UIKit.Rect("Rechts", Root);
            right.anchorMin = new Vector2(0, 0);
            right.anchorMax = new Vector2(1, 1);
            right.offsetMin = new Vector2(480, 30);
            right.offsetMax = new Vector2(-30, -140);
            chapterTitle = UIKit.Label(right, "", 48, Theme.Text, TextAnchor.UpperLeft, FontStyle.Bold);
            chapterTitle.rectTransform.anchorMin = new Vector2(0, 1);
            chapterTitle.rectTransform.anchorMax = new Vector2(1, 1);
            chapterTitle.rectTransform.pivot = new Vector2(0, 1);
            chapterTitle.rectTransform.sizeDelta = new Vector2(0, 60);
            chapterSummary = UIKit.Label(right, "", 28, Theme.TextDim, TextAnchor.UpperLeft);
            chapterSummary.rectTransform.anchorMin = new Vector2(0, 1);
            chapterSummary.rectTransform.anchorMax = new Vector2(1, 1);
            chapterSummary.rectTransform.pivot = new Vector2(0, 1);
            chapterSummary.rectTransform.sizeDelta = new Vector2(0, 80);
            chapterSummary.rectTransform.anchoredPosition = new Vector2(0, -66);

            var scroll = UIKit.Scroll(right, true, out stageList);
            scroll.GetComponent<RectTransform>().Stretch(0, 160, 0, 0);
            stageList.VList(16, 4);
        }

        public override void OnShow()
        {
            header.Refresh();
            chapterList.ClearChildren();
            var p = App.Profile;
            AddChapterButton("ch0", "Prolog", true);
            foreach (var ch in GameDatabase.Chapters)
                AddChapterButton(ch.Id, "Kapitel " + ch.Number + "\n<size=22>" + ch.Title + "</size>", ProfileService.IsUnlocked(p, ch.Stages[0]));
            ShowChapter(chapterId);
        }

        void AddChapterButton(string id, string label, bool unlocked)
        {
            var color = id == chapterId ? Theme.Accent : unlocked ? Theme.PanelLight : Theme.Disabled;
            var b = UIKit.Button(chapterList, unlocked ? label : "🔒 " + label, color, () => { chapterId = id; OnShow(); }, 32);
            b.interactable = unlocked;
            b.Size(-1, 110);
        }

        void ShowChapter(string id)
        {
            stageList.ClearChildren();
            List<StageDefinition> stages;
            if (id == "ch0")
            {
                chapterTitle.text = "Prolog";
                chapterSummary.text = "Der Riss im Schrein von Kirahana – hier beginnt alles.";
                stages = new List<StageDefinition> { GameDatabase.Prologue };
            }
            else
            {
                var ch = GameDatabase.FindChapter(id);
                chapterTitle.text = "Kapitel " + ch.Number + ": " + ch.Title;
                chapterSummary.text = ch.Summary;
                stages = ch.Stages;
            }

            var p = App.Profile;
            int team = ProfileService.TeamPower(p);
            foreach (var s in stages)
            {
                bool unlocked = ProfileService.IsUnlocked(p, s);
                bool cleared = ProfileService.IsCleared(p, s.Id);
                var row = UIKit.Panel(stageList, s.Code, s.IsBoss ? Theme.Hex("#3A1830EE") : Theme.Panel, null, false);
                row.Size(-1, 150);
                var title = UIKit.Label(row.transform, s.Code + "  " + s.Name + (s.IsBoss ? "  <color=#FF5A5A>BOSS</color>" : ""),
                    34, unlocked ? Theme.Text : Theme.TextDim, TextAnchor.UpperLeft, FontStyle.Bold);
                title.rectTransform.Stretch(28, 18, 330, 70);
                string status = !unlocked ? "Gesperrt" : cleared ? "<color=#46E08A>✓ Geschafft</color>" : "<color=#FFC83C>NEU · +" + s.FirstClear.Crystals + " Kristalle</color>";
                var powerColor = team >= s.RecommendedPower ? "#46E08A" : "#FF5A5A";
                var info = UIKit.Label(row.transform, s.Description + "\n<color=" + powerColor + ">Empf. Kampfkraft " + s.RecommendedPower.ToString("N0") + "</color>   " + status,
                    24, Theme.TextDim, TextAnchor.LowerLeft);
                info.rectTransform.Stretch(28, 60, 330, 16);
                var stage = s;
                var start = UIKit.Button(row.transform, unlocked ? "Start ▶" : "🔒", unlocked ? Theme.Accent : Theme.Disabled, () => App.PlayStage(stage), 36);
                start.GetComponent<RectTransform>().Place(1, 0.5f, -24, 0, 260, 100);
                start.interactable = unlocked;
            }
        }
    }

    // ====================================================================== Team

    public sealed class TeamScreen : UIScreen
    {
        HeaderBar header;
        RectTransform slots;
        RectTransform grid;
        RectTransform detail;
        Text teamPower;
        int selectedSlot = 2;
        string selectedId;

        protected override void Build()
        {
            header = HeaderBar.Create(Root, "Team", () => App.GoHome());
            var bg = UIKit.Flat(Root, "BG", new Color(0.03f, 0.03f, 0.1f, 0.75f));
            bg.rectTransform.Stretch(0, 110, 0, 0);
            bg.transform.SetAsFirstSibling();

            slots = UIKit.Rect("Slots", Root);
            slots.Place(0, 1, 30, -130, 1000, 170);
            slots.HList(20, 0, TextAnchor.MiddleLeft);
            teamPower = UIKit.Label(Root, "", 30, Theme.Gold, TextAnchor.MiddleLeft, FontStyle.Bold);
            teamPower.rectTransform.Place(0, 1, 30, -310, 900, 40);

            var scroll = UIKit.Scroll(Root, true, out grid);
            var srt = scroll.GetComponent<RectTransform>();
            srt.anchorMin = new Vector2(0, 0);
            srt.anchorMax = new Vector2(0, 1);
            srt.pivot = new Vector2(0, 0);
            srt.offsetMin = new Vector2(30, 30);
            srt.offsetMax = new Vector2(1030, -370);
            var g = grid.gameObject.AddComponent<GridLayoutGroup>();
            g.cellSize = new Vector2(230, 150);
            g.spacing = new Vector2(16, 16);
            UIAnchors.Register("team.list", srt);

            detail = UIKit.Panel(Root, "Details", Theme.Panel, null, false).rectTransform;
            detail.anchorMin = new Vector2(0, 0);
            detail.anchorMax = new Vector2(1, 1);
            detail.offsetMin = new Vector2(1070, 30);
            detail.offsetMax = new Vector2(-30, -130);
        }

        public override void OnShow()
        {
            header.Refresh();
            var p = App.Profile;
            if (selectedId == null || ProfileService.Find(p, selectedId) == null) selectedId = p.Team[0];

            slots.ClearChildren();
            for (int i = 0; i < ProfileService.TeamSize; i++)
            {
                string id = i < p.Team.Count ? p.Team[i] : null;
                var def = GameDatabase.FindCharacter(id);
                var owned = ProfileService.Find(p, id);
                int slot = i;
                string label = def != null ? def.Name + "\n<size=22>Lv " + owned.Level + " · " + Names.Of(def.Element) + "</size>" : "Leer";
                var b = UIKit.Button(slots, (i == 0 ? "★ " : "") + label, i == selectedSlot ? Theme.Accent : Theme.PanelLight,
                    () => { selectedSlot = slot; OnShow(); }, 28, "team.slot");
                b.Size(310, 160);
            }
            teamPower.text = "Team-Kampfkraft " + ProfileService.TeamPower(p).ToString("N0") + "   ·   Platz " + (selectedSlot + 1) + " ausgewählt (★ = Anführer)";

            grid.ClearChildren();
            var sorted = new List<OwnedCharacter>(p.Characters);
            sorted.Sort((a, b) =>
            {
                int r = GameDatabase.FindCharacter(b.Id).Rarity.CompareTo(GameDatabase.FindCharacter(a.Id).Rarity);
                return r != 0 ? r : b.Level.CompareTo(a.Level);
            });
            foreach (var owned in sorted)
            {
                var def = GameDatabase.FindCharacter(owned.Id);
                string id = owned.Id;
                bool inTeam = p.Team.Contains(id);
                var b = UIKit.Button(grid, def.Name + "\n<size=20>" + def.Rarity + " · Lv " + owned.Level + (owned.LimitBreak > 0 ? " · +" + owned.LimitBreak : "") + (inTeam ? " · Team" : "") + "</size>",
                    id == selectedId ? Theme.Accent : Theme.Of(def.Element) * 0.6f + new Color(0, 0, 0, 0.4f), () => { selectedId = id; OnShow(); }, 26, "team.character");
                var o = b.gameObject.AddComponent<Outline>();
                o.effectColor = Theme.Of(def.Rarity);
                o.effectDistance = new Vector2(3, -3);
                UIAnchors.Register("team.char." + id, b.GetComponent<RectTransform>());
            }
            ShowDetail();
        }

        void ShowDetail()
        {
            detail.ClearChildren();
            var p = App.Profile;
            var def = GameDatabase.FindCharacter(selectedId);
            var owned = ProfileService.Find(p, selectedId);
            if (def == null || owned == null) return;

            var content = UIKit.Rect("Inhalt", detail).Stretch(30, 24, 30, 150);
            content.VList(8, 0, TextAnchor.UpperLeft);
            Line(content, def.Name, 42, Theme.Text, FontStyle.Bold);
            Line(content, "<color=#" + ColorUtility.ToHtmlStringRGB(Theme.Of(def.Rarity)) + ">" + def.Rarity + "</color> · " + def.Title, 26, Theme.TextDim);
            Line(content, Names.Of(def.Element) + " · " + Names.Of(def.Role) + " · Lv " + owned.Level + "/" + Balance.MaxLevel +
                " · Durchbruch " + owned.LimitBreak + "/" + Balance.MaxLimitBreak, 24, Theme.Of(def.Element));
            Line(content, "LP " + Balance.ScaleStat(def.BaseHp, owned.Level, owned.LimitBreak) +
                "   ANG " + Balance.ScaleStat(def.BaseAtk, owned.Level, owned.LimitBreak) +
                "   VER " + Balance.ScaleStat(def.BaseDef, owned.Level, owned.LimitBreak) +
                "   EXP " + owned.Exp + "/" + Balance.ExpToNext(owned.Level), 24, Theme.Text);
            foreach (var s in def.Skills) Line(content, SkillText(s, false), 22, Theme.Text);
            Line(content, SkillText(def.Ultimate, true), 22, Theme.Gold);
            Line(content, "<i>" + def.Lore + "</i>", 20, Theme.TextDim);

            var assign = UIKit.Button(detail, "Ins Team (Platz " + (selectedSlot + 1) + ")", Theme.Accent, Assign, 30, "team.assign");
            assign.GetComponent<RectTransform>().Place(0, 0, 30, 30, 360, 100);
            int cost = Balance.LevelUpGoldCost(owned.Level);
            var level = UIKit.Button(detail, "Level Up\n<size=22>" + cost + " Gold</size>", Theme.Hex("#C8A04A"), LevelUp, 30, "team.levelup");
            level.GetComponent<RectTransform>().Place(1, 0, -30, 30, 300, 100);
            level.interactable = owned.Level < Balance.MaxLevel && p.Gold >= cost;
        }

        static void Line(Transform parent, string text, int size, Color color, FontStyle style = FontStyle.Normal)
        {
            var t = UIKit.Label(parent, text, size, color, TextAnchor.UpperLeft, style);
            t.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        }

        static string SkillText(SkillDefinition s, bool ultimate)
        {
            string power = "";
            if (s.PowerAt(1) > 0)
                power = ultimate ? " (" + Mathf.RoundToInt(s.PowerAt(1) * 100) + " %)"
                    : " (" + Mathf.RoundToInt(s.PowerAt(1) * 100) + " / " + Mathf.RoundToInt(s.PowerAt(2) * 100) + " / " + Mathf.RoundToInt(s.PowerAt(3) * 100) + " %)";
            return "<b>" + (ultimate ? "ULT " : "") + s.Name + "</b>" + power + " – " + CardView.KindLabel(s) + ". " + s.Description;
        }

        void Assign()
        {
            if (ProfileService.SetTeamSlot(App.Profile, selectedSlot, selectedId))
            {
                App.SaveNow();
                OnShow();
                App.Tutorial.Notify(TutorialTrigger.TeamChanged);
            }
            else App.UI.Toast("Ist schon auf diesem Platz.");
        }

        void LevelUp()
        {
            if (ProfileService.TryLevelUpWithGold(App.Profile, selectedId))
            {
                App.SaveNow();
                OnShow();
            }
        }
    }

    // ====================================================================== Beschwörung

    public sealed class GachaScreen : UIScreen
    {
        HeaderBar header;
        RectTransform tabs;
        Image bannerPanel;
        Text bannerName;
        Text bannerInfo;
        Button pull1;
        Button pull10;
        RectTransform results;
        BannerDefinition banner;

        protected override void Build()
        {
            header = HeaderBar.Create(Root, "Beschwörung", () => App.GoHome());
            tabs = UIKit.Rect("Banner", Root);
            tabs.Place(0, 1, 30, -140, 420, 800);
            tabs.VList(16);

            bannerPanel = UIKit.Panel(Root, "Banner", Theme.Accent, null, false);
            var rt = bannerPanel.rectTransform;
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = new Vector2(480, 180);
            rt.offsetMax = new Vector2(-30, -140);
            bannerName = UIKit.Label(rt, "", 64, Theme.Text, TextAnchor.UpperLeft, FontStyle.BoldAndItalic);
            bannerName.rectTransform.Stretch(40, 30, 40, 0);
            bannerName.Outlined(new Color(0, 0, 0, 0.5f), 3f);
            bannerInfo = UIKit.Label(rt, "", 30, Theme.Text, TextAnchor.UpperLeft);
            bannerInfo.rectTransform.Stretch(40, 130, 40, 30);
            bannerInfo.Outlined(new Color(0, 0, 0, 0.4f), 1.5f);

            pull1 = UIKit.Button(Root, "1× Beschwören", Theme.Hex("#7B5CFF"), () => Summon(1), 32, "gacha.pull1");
            pull1.GetComponent<RectTransform>().Place(1, 0, -420, 40, 360, 120);
            pull10 = UIKit.Button(Root, "10× Beschwören", Theme.Accent, () => Summon(10), 32, "gacha.pull10");
            pull10.GetComponent<RectTransform>().Place(1, 0, -30, 40, 360, 120);

            results = UIKit.Flat(Root, "Ergebnisse", new Color(0.02f, 0.02f, 0.08f, 0.94f), true).rectTransform;
            results.Stretch();
            results.gameObject.SetActive(false);
        }

        public override void OnShow()
        {
            header.Refresh();
            var p = App.Profile;
            if (banner == null || (banner.IsBeginner && ProfileService.BeginnerUsed(p, banner)))
            {
                banner = null;
                foreach (var b in GameDatabase.Banners)
                    if (!b.IsBeginner || !ProfileService.BeginnerUsed(p, b)) { banner = b; break; }
            }

            tabs.ClearChildren();
            foreach (var b in GameDatabase.Banners)
            {
                if (b.IsBeginner && ProfileService.BeginnerUsed(p, b)) continue;
                var bb = b;
                UIKit.Button(tabs, b.Name, b == banner ? Theme.Hex(b.Color) : Theme.PanelLight, () => { banner = bb; OnShow(); }, 28, "gacha.tab").Size(-1, 110);
            }

            bannerPanel.color = Theme.Hex(banner.Color);
            bannerName.text = banner.Name;
            var pity = ProfileService.GetPity(p, banner);
            string info = banner.Subtitle + "\n\n";
            foreach (var id in banner.FeaturedIds)
            {
                var c = GameDatabase.FindCharacter(id);
                info += "★ " + c.Name + " – " + c.Title + " (" + Names.Of(c.Element) + ")\n";
            }
            info += "\nRaten: SSR 3 % · SR 15 % · R 82 %\n";
            if (!banner.IsBeginner)
            {
                info += "SSR garantiert in spätestens " + (Balance.HardPity - pity.SinceSsr) + " Zügen";
                if (banner.FeaturedIds.Length > 0) info += pity.FeaturedGuaranteed ? " · nächster SSR ist garantiert Featured!" : " · 50/50 auf Featured";
            }
            bannerInfo.text = info;

            pull1.gameObject.SetActive(!banner.IsBeginner);
            pull1.SetLabel("1× Beschwören\n<size=22>" + banner.CostSingle + " ✦</size>");
            pull10.SetLabel("10× Beschwören\n<size=22>" + (banner.IsBeginner ? "KOSTENLOS" : banner.CostMulti + " ✦") + "</size>");
            pull1.interactable = ProfileService.CheckSummon(p, banner, 1) == null;
            pull10.interactable = ProfileService.CheckSummon(p, banner, 10) == null;
        }

        void Summon(int count)
        {
            var gacha = new GachaSystem(GameDatabase.Characters, App.Random);
            var result = ProfileService.Summon(App.Profile, banner, count, gacha);
            if (!result.Success)
            {
                App.UI.Toast(result.Error);
                return;
            }
            App.SaveNow();
            StartCoroutine(Reveal(result.Pulls));
            App.Tutorial.Notify(TutorialTrigger.GachaPulled);
        }

        IEnumerator Reveal(List<GachaPull> pulls)
        {
            results.ClearChildren();
            results.gameObject.SetActive(true);
            results.SetAsLastSibling();

            var best = Rarity.R;
            foreach (var p in pulls) if (p.Character.Rarity > best) best = p.Character.Rarity;
            var flash = UIKit.Flat(results, "Blitz", Theme.Of(best));
            flash.rectTransform.Stretch();
            float t = 0;
            while (t < 1f)
            {
                t += Time.unscaledDeltaTime * 1.6f;
                flash.color = Theme.Of(best).WithAlpha(1f - t);
                yield return null;
            }
            Destroy(flash.gameObject);

            var grid = UIKit.Rect("Raster", results);
            grid.Place(0.5f, 0.5f, 0, 60, 1500, 700);
            var g = grid.gameObject.AddComponent<GridLayoutGroup>();
            g.cellSize = new Vector2(280, 330);
            g.spacing = new Vector2(20, 20);
            g.childAlignment = TextAnchor.MiddleCenter;

            foreach (var pull in pulls)
            {
                var c = pull.Character;
                var card = UIKit.Panel(grid, c.Name, Theme.Panel, null, false);
                var o = card.gameObject.AddComponent<Outline>();
                o.effectColor = Theme.Of(c.Rarity);
                o.effectDistance = new Vector2(5, -5);
                var band = UIKit.Panel(card.transform, "Seltenheit", Theme.Of(c.Rarity), null, false);
                band.rectTransform.Place(0.5f, 1, 0, -10, 250, 60);
                var r = UIKit.Label(band.transform, c.Rarity.ToString(), 40, Theme.Text, TextAnchor.MiddleCenter, FontStyle.Bold);
                r.rectTransform.Stretch();
                var portrait = UIKit.Panel(card.transform, "Portrait", Theme.Hex(c.HairColor), UIKit.Circle, false);
                portrait.type = Image.Type.Simple;
                portrait.rectTransform.Place(0.5f, 1, 0, -84, 110, 110);
                var name = UIKit.Label(card.transform, c.Name + "\n<size=20>" + c.Title + "</size>", 28, Theme.Text, TextAnchor.UpperCenter, FontStyle.Bold);
                name.rectTransform.Stretch(10, 204, 10, 40);
                string tag = pull.IsNew ? "<color=#FFC83C>NEU!</color>" : pull.BonusCrystals > 0 ? "+" + pull.BonusCrystals + " ✦" : "Durchbruch +" + pull.LimitBreak;
                var tagLabel = UIKit.Label(card.transform, tag, 24, Theme.Accent2, TextAnchor.LowerCenter, FontStyle.Bold);
                tagLabel.rectTransform.Stretch(0, 0, 0, 12);

                card.rectTransform.localScale = Vector3.zero;
                float s = 0;
                while (s < 1f)
                {
                    s += Time.unscaledDeltaTime * (c.Rarity == Rarity.SSR ? 2.5f : 7f);
                    float k = Mathf.Sin(Mathf.Clamp01(s) * Mathf.PI * 0.75f) / 0.707f;
                    card.rectTransform.localScale = Vector3.one * Mathf.Min(k, 1.15f) * (s >= 1f ? 1f / Mathf.Min(k, 1.15f) : 1f);
                    yield return null;
                }
                card.rectTransform.localScale = Vector3.one;
            }

            var close = UIKit.Button(results, "Weiter", Theme.Accent, Close, 36, "gacha.close");
            close.GetComponent<RectTransform>().Place(0.5f, 0, 0, 40, 360, 110);
        }

        void Close()
        {
            results.gameObject.SetActive(false);
            OnShow();
            App.Tutorial.Notify(TutorialTrigger.GachaClosed);
        }
    }

    // ====================================================================== Ergebnis

    public sealed class ResultScreen : UIScreen
    {
        Text title;
        Text body;
        Button primary;
        Button secondary;
        StageDefinition stage;

        protected override void Build()
        {
            var dim = UIKit.Flat(Root, "Dim", new Color(0.02f, 0.02f, 0.08f, 0.7f), true);
            dim.rectTransform.Stretch();
            var panel = UIKit.Panel(Root, "Panel", Theme.Panel, null, false);
            panel.rectTransform.Place(0.5f, 0.5f, 0, 0, 1100, 760);
            title = UIKit.Label(panel.transform, "", 110, Theme.Gold, TextAnchor.UpperCenter, FontStyle.BoldAndItalic);
            title.rectTransform.Stretch(20, 30, 20, 560);
            title.Outlined(new Color(0, 0, 0, 0.6f), 4f);
            body = UIKit.Label(panel.transform, "", 34, Theme.Text, TextAnchor.UpperCenter);
            body.rectTransform.Stretch(60, 210, 60, 160);
            primary = UIKit.Button(panel.transform, "", Theme.Accent, null, 36);
            primary.GetComponent<RectTransform>().Place(1, 0, -60, 40, 400, 110);
            secondary = UIKit.Button(panel.transform, "", Theme.PanelLight, null, 32);
            secondary.GetComponent<RectTransform>().Place(0, 0, 60, 40, 400, 110);
        }

        public void ShowVictory(StageDefinition s, StageResult r)
        {
            stage = s;
            title.text = "SIEG!";
            title.color = Theme.Gold;
            string text = s.Code + "  " + s.Name + (r.FirstClear ? "\n<color=#FFC83C>Erstabschluss!</color>" : "") + "\n\n";
            if (r.Crystals > 0) text += "+" + r.Crystals + " Kristalle ✦\n";
            text += "+" + r.Gold + " Gold\n+" + r.Exp + " EXP für jedes Teammitglied\n";
            foreach (var lu in r.LevelUps)
                text += "\n<color=#46E08A>" + GameDatabase.FindCharacter(lu.CharacterId).Name + ": Level " + lu.From + " → " + lu.To + "</color>";
            body.text = text;
            bool prologue = s == GameDatabase.Prologue;
            Setup(primary, "Weiter", () => { if (prologue) App.GoHome(); else App.GoStory(); });
            Setup(secondary, "Nochmal", () => App.PlayStage(stage));
            secondary.gameObject.SetActive(!prologue);
        }

        public void ShowDefeat(StageDefinition s)
        {
            stage = s;
            title.text = "NIEDERLAGE";
            title.color = Theme.Danger;
            body.text = s.Code + "  " + s.Name + "\n\nTipps:\n• Nutze Elementvorteile (Wasser > Feuer > Wind > Erde > Wasser)\n• Verschmelze Karten zu Rang 2 und 3\n• Levele deine Helden im Team-Menü\n• Beschwöre neue Helden";
            Setup(primary, "Erneut versuchen", () => App.PlayStage(stage));
            Setup(secondary, "Zurück", () => { if (App.Profile.Tutorial == TutorialPhase.Battle) App.PlayStage(stage); else App.GoStory(); });
            secondary.gameObject.SetActive(true);
        }

        static void Setup(Button b, string label, UnityEngine.Events.UnityAction action)
        {
            b.SetLabel(label);
            b.onClick.RemoveAllListeners();
            b.onClick.AddListener(action);
        }
    }
}
