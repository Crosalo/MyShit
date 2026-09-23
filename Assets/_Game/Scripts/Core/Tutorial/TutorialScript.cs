using System;
using System.Collections.Generic;

namespace Aether.Core
{
    public enum TutorialTrigger
    {
        Tap,
        CardUsed,
        CardMoved,
        CardsMerged,
        UltimateUsed,
        TurnExecuted,
        BattleWon,
        OpenGacha,
        GachaPulled,
        GachaClosed,
        OpenHome,
        OpenTeam,
        TeamChanged
    }

    public enum TutorialAction { None, Any, UseCard, MoveCard, UseUltimate, Execute }

    public sealed class TutorialStep
    {
        public string Id;

        /// <summary>Text der Erklärung. null = kein Hinweis anzeigen (freies Spiel).</summary>
        public string Text;

        /// <summary>Schlüssel des UI-Elements, das hervorgehoben wird.</summary>
        public string Anchor;

        public TutorialTrigger Trigger;

        /// <summary>Welche Kampfaktion erlaubt ist.</summary>
        public TutorialAction Action = TutorialAction.None;

        public int HandIndex = -1;
        public int[] MoveTargets;
        public int UnitIndex = -1;

        /// <summary>Wenn gesetzt, dürfen nur diese Buttons gedrückt werden.</summary>
        public string[] AllowedButtons;

        public bool WaitsForTap { get { return Trigger == TutorialTrigger.Tap; } }
    }

    /// <summary>
    /// Ablauf des Tutorials. Der Prolog-Kampf hat eine feste Starthand
    /// (siehe <see cref="StoryContent.Prologue"/>), damit jeder Schritt garantiert funktioniert.
    /// </summary>
    public static class TutorialScript
    {
        public const string FirstSummonStepId = "summon_open";
        public const string TeamStepId = "summon_team";

        public static List<TutorialStep> Battle()
        {
            return new List<TutorialStep>
            {
                Tap("battle_welcome", null,
                    "Willkommen, Beschwörer! Monster sind aus dem Riss gekrochen. Zeit für deinen ersten Kampf!"),
                Tap("battle_hand", "battle.hand",
                    "Unten liegen deine Fähigkeitskarten. Jede Karte gehört zu einem deiner Helden – Farbe und Name zeigen, zu wem."),
                Tap("battle_slots", "battle.slots",
                    "Pro Runde hast du 3 Aktionen. Jede Aktion belegt einen dieser Slots. Danach greifen die Gegner an."),
                new TutorialStep
                {
                    Id = "battle_use", Anchor = "battle.card.1", Trigger = TutorialTrigger.CardsMerged,
                    Action = TutorialAction.UseCard, HandIndex = 1,
                    Text = "Tippe auf die markierte Karte, um sie einzusetzen. Achte darauf, was mit ihren Nachbarn passiert!"
                },
                Tap("battle_merged", "battle.card.0",
                    "Zwei gleiche Karten lagen nebeneinander und sind zu einer Rang-2-Karte verschmolzen! Höherer Rang = mehr Schaden und stärkere Effekte. Maximum ist Rang 3."),
                new TutorialStep
                {
                    Id = "battle_move", Anchor = "battle.card.4", Trigger = TutorialTrigger.CardsMerged,
                    Action = TutorialAction.MoveCard, HandIndex = 4, MoveTargets = new[] { 1, 2 },
                    Text = "Du kannst Karten auch verschieben: Ziehe die markierte Karte neben die gleiche Karte von Kenta."
                },
                Tap("battle_locked", "battle.slots",
                    "Verschmolzen! Aber Achtung: Verschieben kostet eine Aktion – dieser Slot ist jetzt gesperrt. Überlege also gut, wann es sich lohnt."),
                new TutorialStep
                {
                    Id = "battle_use_rank2", Anchor = "battle.card.0", Trigger = TutorialTrigger.CardUsed,
                    Action = TutorialAction.UseCard, HandIndex = 0,
                    Text = "Setze jetzt Harus Rang-2-Karte ein."
                },
                new TutorialStep
                {
                    Id = "battle_execute", Anchor = "battle.execute", Trigger = TutorialTrigger.TurnExecuted,
                    Action = TutorialAction.Execute,
                    Text = "Alle 3 Slots sind belegt. Tippe auf „Kampf!“, um deine Aktionen auszuführen."
                },
                Tap("battle_gauge", "battle.ult.0",
                    "Jede eingesetzte Karte lädt die Ultimativ-Leiste ihres Helden – Rang 2 gibt 2 Punkte. Harus Leiste ist voll!"),
                new TutorialStep
                {
                    Id = "battle_ultimate", Anchor = "battle.ult.0", Trigger = TutorialTrigger.UltimateUsed,
                    Action = TutorialAction.UseUltimate, UnitIndex = 0,
                    Text = "Tippe auf Harus Ultimativ-Button, um seine Spezialattacke einzuplanen."
                },
                Tap("battle_free", null,
                    "Tipp: Tippe auf einen Gegner, um ihn als Ziel zu wählen. Elementvorteil macht 50 % mehr Schaden. Jetzt bist du dran – besiege die Monster!"),
                new TutorialStep
                {
                    Id = "battle_play", Trigger = TutorialTrigger.BattleWon, Action = TutorialAction.Any
                }
            };
        }

        public static List<TutorialStep> Summon()
        {
            return new List<TutorialStep>
            {
                Button(FirstSummonStepId, "home.gacha", TutorialTrigger.OpenGacha,
                    "Mit Aether-Splittern beschwörst du neue Helden. Öffne die Beschwörung!"),
                Button("summon_pull", "gacha.pull10", TutorialTrigger.GachaPulled,
                    "Die Einsteiger-Beschwörung ist kostenlos und enthält garantiert einen SSR-Helden. Tippe auf „10× Beschwören“!"),
                Button("summon_close", "gacha.close", TutorialTrigger.GachaClosed,
                    "Glückwunsch! Kaito, die Klinge des Morgenrots, hat sich dir angeschlossen. Schließe die Ergebnisse."),
                Button("summon_back", "nav.back", TutorialTrigger.OpenHome,
                    "Zurück ins Hauptmenü."),
                Button(TeamStepId, "home.team", TutorialTrigger.OpenTeam,
                    "Jetzt stellen wir dein Team zusammen. Öffne das Team-Menü!"),
                new TutorialStep
                {
                    Id = "summon_assign", Anchor = "team.char.kaito", Trigger = TutorialTrigger.TeamChanged,
                    AllowedButtons = new[] { "team.character", "team.assign", "team.slot" },
                    Text = "Tippe auf Kaito und dann auf „Ins Team“. Er ersetzt den markierten Teamplatz."
                },
                Tap("summon_done", null,
                    "Perfekt! Das Tutorial ist geschafft. Als Belohnung bekommst du " + Balance.TutorialRewardCrystals +
                    " Kristalle. Die Story wartet auf dich!")
            };
        }

        public static List<TutorialStep> For(TutorialPhase phase)
        {
            switch (phase)
            {
                case TutorialPhase.Battle: return Battle();
                case TutorialPhase.Summon: return Summon();
                default: return new List<TutorialStep>();
            }
        }

        /// <summary>Darf diese Kampfaktion im aktuellen Schritt ausgeführt werden?</summary>
        public static bool Allows(TutorialStep step, TutorialAction action, int handIndex = -1, int moveTo = -1, int unitIndex = -1)
        {
            if (step == null || step.Action == TutorialAction.Any) return true;
            if (step.Action != action) return false;
            if (step.HandIndex >= 0 && step.HandIndex != handIndex) return false;
            if (step.MoveTargets != null && Array.IndexOf(step.MoveTargets, moveTo) < 0) return false;
            if (step.UnitIndex >= 0 && step.UnitIndex != unitIndex) return false;
            return true;
        }

        /// <summary>Darf dieser (Navigations-)Button gedrückt werden?</summary>
        public static bool AllowsButton(TutorialStep step, string key)
        {
            if (step == null) return true;
            if (step.AllowedButtons != null) return key != null && Array.IndexOf(step.AllowedButtons, key) >= 0;
            if (step.WaitsForTap) return false;
            return step.Action == TutorialAction.Any;
        }

        static TutorialStep Tap(string id, string anchor, string text)
        {
            return new TutorialStep { Id = id, Anchor = anchor, Text = text, Trigger = TutorialTrigger.Tap };
        }

        static TutorialStep Button(string id, string key, TutorialTrigger trigger, string text)
        {
            return new TutorialStep { Id = id, Anchor = key, Trigger = trigger, Text = text, AllowedButtons = new[] { key } };
        }
    }
}
