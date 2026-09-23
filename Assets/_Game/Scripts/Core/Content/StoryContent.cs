using System;
using System.Collections.Generic;

namespace Aether.Core
{
    /// <summary>
    /// Story: Prolog (Tutorial) und drei Kapitel à vier Etappen.
    /// Dialogzeilen: "Sprecher|Text". Der Sprecher "{name}" wird durch den Spielernamen ersetzt.
    /// </summary>
    public static class StoryContent
    {
        public const string PrologueId = "stage_0_1";

        public static StageDefinition Prologue()
        {
            var s = Stage("ch0", "0-1", "Der Riss im Schrein",
                "Ein Riss hat sich im Schrein von Kirahana geöffnet.",
                new Reward { Gold = 500, Exp = 50 }, new Reward { Gold = 100, Exp = 20 },
                W("slime_blue:1", "slime_red:1"));
            s.FixedTeam = new[] { "haru", "nami", "kenta" };
            // Haru = 0, Nami = 1, Kenta = 2 | Fähigkeit 0 oder 1.
            // Karte 1 (Nami) einsetzen → Haru-Karten links verschmelzen.
            // Karte 4 (Kenta) neben Karte 1 schieben → Kenta-Karten verschmelzen.
            s.InitialHand = new List<CardSeed>
            {
                new CardSeed(0, 0), new CardSeed(1, 0), new CardSeed(0, 0), new CardSeed(2, 0),
                new CardSeed(1, 1), new CardSeed(2, 1), new CardSeed(2, 0)
            };
            s.InitialGauge = new[] { 3, 0, 0 };
            s.Seed = 1337;
            s.Intro = D(
                "Erzähler|Vor hundert Jahren zerbrach der Himmelskristall über Aetheria. Seine Splitter regneten auf die Welt herab – und mit ihnen die Macht der Beschwörung.",
                "Erzähler|Wer einen Aether-Splitter berührt, kann die Seelen von Helden rufen. Menschen wie dich nennt man Beschwörer.",
                "Erzähler|Heute, im Schrein von Kirahana, beginnt deine Geschichte ...",
                "Haru|Hey! Du bist doch der neue Beschwörer, oder? Gut, dass du da bist – im Schrein hat sich ein Riss geöffnet!",
                "Nami|Da kommen Schleimlinge raus! Kenta, schnapp dir deinen Hammer!",
                "Kenta|Schon dabei! Beschwörer, sag uns, was wir tun sollen!");
            s.Outro = D(
                "Haru|Puh ... das war knapp. Du hast echt Talent!",
                "Kenta|Der Riss ist wieder zu. Aber schau mal – da liegt ein leuchtender Splitter.",
                "Nami|Ein Aether-Splitter! Damit kannst du einen neuen Helden beschwören, oder?",
                "Haru|Probier's aus! Vielleicht erwischst du ja jemanden richtig Starkes.");
            return s;
        }

        public static List<ChapterDefinition> Chapters()
        {
            var ch1 = new ChapterDefinition
            {
                Id = "ch1", Number = 1, Title = "Das Erwachen der Splitter",
                Summary = "Überall im Tal von Kirahana öffnen sich Risse. Folge ihrer Spur bis zu den Ruinen des Mondtempels."
            };
            var r1 = new Reward { Crystals = 100, Gold = 1500, Exp = 120 };
            var r1b = new Reward { Crystals = 300, Gold = 2500, Exp = 200 };
            var rep1 = new Reward { Gold = 400, Exp = 60 };

            ch1.Stages.Add(Stage("ch1", "1-1", "Waldpfad von Kirahana", "Folge den Rissen in den Wald.", r1, rep1,
                W("slime_blue:2", "slime_red:2"), W("wolf:3")).Talk(
                D("Haru|Die Dorfältesten sagen, seit gestern tauchen überall im Wald Risse auf.",
                  "Kaito|Risse erscheinen nie ohne Grund. Irgendetwas zieht an ihnen.",
                  "Nami|Du bist der Held aus dem Splitter, oder? Cool!",
                  "Haru|Los, wir folgen dem Waldpfad!"),
                D("Kenta|Die Monster kamen alle aus Richtung Aschewald.",
                  "Kaito|Dann gehen wir dorthin.")));

            ch1.Stages.Add(Stage("ch1", "1-2", "Der Aschewald", "Ein Wald, der seit hundert Jahren glüht.", r1, rep1,
                W("wolf:3", "wolf:3"), W("kobold:4", "slime_red:4")).Talk(
                D("Erzähler|Der Aschewald brennt seit hundert Jahren, ohne je zu verlöschen.",
                  "Haru|Hier riecht's nach verbranntem Fell ...",
                  "Kaito|Aschewölfe. Bleibt zusammen!"),
                D("Nami|Schaut, Spuren im Boden! Sie führen zu den alten Ruinen.",
                  "Kaito|Der Mondtempel ... dort wurde früher ein Fragment des Himmelskristalls aufbewahrt.")));

            ch1.Stages.Add(Stage("ch1", "1-3", "Ruinen des Mondtempels", "Etwas Uraltes erwacht in den Ruinen.", r1, rep1,
                W("kobold:5", "wisp:5", "kobold:5"), W("shadow:5")).Talk(
                D("Kenta|Die Ruinen leuchten. Das ist doch nicht normal, oder?",
                  "???|Wer wagt es, den Schlaf des Wächters zu stören ...",
                  "Haru|Äh. Hat das gerade jemand gesagt?"),
                D("Kaito|Die Schatten hier sind organisiert. Jemand führt sie an.",
                  "Nami|Da hinten! Der Boden bebt!")));

            ch1.Stages.Add(Stage("ch1", "1-4", "Herz des Kristallgolems", "BOSS: Der Wächter des Tempels.", r1b, rep1,
                W("kobold:6", "kobold:6"), W("golem:6")).Boss().Talk(
                D("Erzähler|Im Herzen des Tempels erhebt sich ein Riese aus reinem Kristall.",
                  "Kaito|Ein Golem, der sich von Aether-Splittern nährt. Er muss fallen, bevor er das ganze Tal leersaugt!",
                  "Haru|Na dann – zeigen wir ihm, was ein Team kann!"),
                D("Erzähler|Der Golem zerfällt zu glitzerndem Staub. In seiner Mitte schwebt ein großer Aether-Splitter.",
                  "Kaito|Das ist kein normaler Splitter ... jemand hat ihn hierhergebracht.",
                  "Haru|Da hängt ein Zettel dran: „Für Morwen. Hafen von Seiryu.“",
                  "Kaito|Dann ist unser nächstes Ziel klar.")));

            var ch2 = new ChapterDefinition
            {
                Id = "ch2", Number = 2, Title = "Nebel über Seiryu",
                Summary = "Die Hafenstadt Seiryu versinkt in unnatürlichem Nebel. Wer ist Morwen – und für wen sammelt sie Splitter?"
            };
            var r2 = new Reward { Crystals = 100, Gold = 3000, Exp = 350 };
            var r2b = new Reward { Crystals = 300, Gold = 5000, Exp = 500 };
            var rep2 = new Reward { Gold = 800, Exp = 175 };

            ch2.Stages.Add(Stage("ch2", "2-1", "Hafen von Seiryu", "Nebel liegt über dem Hafen.", r2, rep2,
                W("slime_blue:8", "slime_blue:8", "slime_blue:8"), W("harpy:9", "harpy:9")).Talk(
                D("Sora|Reisende? Ihr solltet nicht hier sein. Der Nebel frisst jeden, der zu lange bleibt.",
                  "Kaito|Wir suchen eine gewisse Morwen.",
                  "Sora|... Dann seid ihr entweder mutig oder dumm. Ich komme mit."),
                D("Sora|Die Harpyien fliegen zu den Sturmklippen. Aber zuerst müssen wir durch die Altstadt.")));

            ch2.Stages.Add(Stage("ch2", "2-2", "Die stillen Gassen", "Eine Stadt im Tiefschlaf.", r2, rep2,
                W("shadow:10", "wisp:10"), W("shadow:11", "shadow:11")).Talk(
                D("Nami|Warum ist hier niemand? Die Stadt ist wie ausgestorben.",
                  "Sora|Morwen hat die Bewohner in den Schlaf gesungen. Sie träumen – und ihre Träume nähren den Nebel."),
                D("Yuki|Ihr seid also die Gruppe, die den Golem besiegt hat.",
                  "Haru|Wow ... wer bist du denn?",
                  "Yuki|Yuki Shirogane. Ich jage Morwen seit Wochen. Wir sollten zusammenarbeiten.")));

            ch2.Stages.Add(Stage("ch2", "2-3", "Sturmklippen", "Der Weg zu Morwens Turm.", r2, rep2,
                W("harpy:12", "harpy:12", "harpy:12"), W("wolf:12", "kobold:12")).Talk(
                D("Yuki|Ihr Turm steht auf den Klippen. Die Harpyien bewachen den Weg.",
                  "Kaito|Dann schlagen wir uns durch."),
                D("Sora|Der Nebel wird dichter ... sie weiß, dass wir kommen.")));

            ch2.Stages.Add(Stage("ch2", "2-4", "Die Nebelhexe", "BOSS: Morwen erwartet euch.", r2b, rep2,
                W("shadow:13", "wisp:13"), W("witch:14")).Boss().Talk(
                D("Morwen|Wie rührend. Kleine Helden, die glauben, sie könnten das Unvermeidliche aufhalten.",
                  "Kaito|Für wen sammelst du die Splitter?",
                  "Morwen|Für den Einzigen, der den Himmelskristall neu schmieden kann. Für Varkas!",
                  "Kaito|... Varkas?!"),
                D("Morwen|Ihr ... seid zu spät ... Varkas hat genug Splitter ...",
                  "Erzähler|Morwen löst sich im Nebel auf. Die Bewohner von Seiryu erwachen.",
                  "Haru|Kaito, du siehst aus, als hättest du einen Geist gesehen.",
                  "Kaito|Varkas war mein Meister. Hauptmann der Flammengarde ... und der Mann, der mein Kloster niederbrannte.")));

            var ch3 = new ChapterDefinition
            {
                Id = "ch3", Number = 3, Title = "Der gefallene Ritter",
                Summary = "Varkas will den Himmelskristall neu schmieden – um jeden Preis. Kaito muss sich seiner Vergangenheit stellen."
            };
            var r3 = new Reward { Crystals = 150, Gold = 5000, Exp = 700 };
            var r3b = new Reward { Crystals = 500, Gold = 10000, Exp = 1000 };
            var rep3 = new Reward { Gold = 1200, Exp = 350 };

            ch3.Stages.Add(Stage("ch3", "3-1", "Brennende Ebene", "Varkas' Truppen versperren den Weg.", r3, rep3,
                W("wolf:17", "slime_red:17", "wolf:17"), W("shadow:18", "shadow:18")).Talk(
                D("Erzähler|Die Ebene vor der Festung Grauwacht steht in Flammen.",
                  "Kenta|Hier ist es heißer als in meiner Schmiede!",
                  "Kaito|Varkas' Truppen. Wir müssen durch."),
                D("Haru|Die Festung ist gleich da vorne!")));

            ch3.Stages.Add(Stage("ch3", "3-2", "Festung Grauwacht", "Ein Golem bewacht das Tor.", r3, rep3,
                W("kobold:19", "kobold:19", "shadow:19"), W("golem:20")).Talk(
                D("Yuki|Sie haben einen Golem ans Tor gestellt. Noch einer dieser Kristallriesen.",
                  "Kaito|Dann reißen wir ihn nieder."),
                D("Kenta|Das Tor ist offen! Weiter zum Thronsaal!")));

            ch3.Stages.Add(Stage("ch3", "3-3", "Thronsaal der Asche", "Eine alte Bekannte kehrt zurück.", r3, rep3,
                W("shadow:21", "harpy:21", "wisp:21"), W("witch:22")).Talk(
                D("Morwen|Ihr hättet in Seiryu bleiben sollen.",
                  "Nami|Du schon wieder?! Wir haben dich doch besiegt!",
                  "Morwen|Nebel stirbt nicht, Kleine. Er verzieht sich nur."),
                D("Erzähler|Morwen verschwindet endgültig. Hinter ihr öffnet sich das Tor zur Himmelsschmiede.")));

            ch3.Stages.Add(Stage("ch3", "3-4", "Varkas' Urteil", "FINALE: Meister gegen Schüler.", r3b, rep3,
                W("shadow:23", "shadow:23"), W("knight:24")).Boss().Talk(
                D("Varkas|Kaito. Du bist groß geworden.",
                  "Kaito|Warum, Meister? Warum hast du das Kloster verbrannt?",
                  "Varkas|Weil der Himmelskristall nicht zerbrochen ist – man hat ihn zerbrochen. Ich schmiede ihn neu und lösche diesen Fehler aus der Geschichte.",
                  "Kaito|Und alle, die in dieser Geschichte leben, gleich mit? Nicht mit uns!"),
                D("Varkas|Du ... hast mich übertroffen, Schüler ...",
                  "Erzähler|Die gesammelten Splitter steigen in den Himmel und verglühen wie Sternschnuppen.",
                  "Aiko|Die Sterne ... sie singen wieder. Aber sie singen von etwas Neuem.",
                  "Erzähler|Hoch über Aetheria öffnet sich ein Riss, größer als alle zuvor ...",
                  "Erzähler|Fortsetzung folgt.")));

            return new List<ChapterDefinition> { ch1, ch2, ch3 };
        }

        // ------------------------------------------------------------------ Hilfen

        static StageDefinition Stage(string chapterId, string code, string name, string description,
            Reward firstClear, Reward repeat, params List<EnemySpawn>[] waves)
        {
            var s = new StageDefinition
            {
                Id = "stage_" + code.Replace('-', '_'),
                ChapterId = chapterId,
                Code = code,
                Name = name,
                Description = description,
                FirstClear = firstClear,
                Repeat = repeat,
                Waves = new List<List<EnemySpawn>>(waves)
            };
            int maxLevel = 1;
            foreach (var wave in waves)
                foreach (var spawn in wave) maxLevel = Math.Max(maxLevel, spawn.Level);
            s.RecommendedPower = (int)Math.Round(2400 * Balance.LevelMultiplier(maxLevel) / 50.0) * 50;
            return s;
        }

        static StageDefinition Talk(this StageDefinition s, List<DialogueLine> intro, List<DialogueLine> outro)
        {
            s.Intro = intro;
            s.Outro = outro;
            return s;
        }

        static StageDefinition Boss(this StageDefinition s)
        {
            s.IsBoss = true;
            return s;
        }

        /// <summary>Welle aus "gegnerId:level"-Einträgen.</summary>
        static List<EnemySpawn> W(params string[] entries)
        {
            var list = new List<EnemySpawn>();
            foreach (var e in entries)
            {
                var parts = e.Split(':');
                list.Add(new EnemySpawn(parts[0], int.Parse(parts[1])));
            }
            return list;
        }

        static List<DialogueLine> D(params string[] lines)
        {
            var list = new List<DialogueLine>();
            foreach (var l in lines)
            {
                int bar = l.IndexOf('|');
                list.Add(bar < 0 ? new DialogueLine("", l) : new DialogueLine(l.Substring(0, bar), l.Substring(bar + 1)));
            }
            return list;
        }
    }
}
