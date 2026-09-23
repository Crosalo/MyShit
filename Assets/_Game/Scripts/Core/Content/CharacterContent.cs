using System.Collections.Generic;
using static Aether.Core.Sk;

namespace Aether.Core
{
    /// <summary>
    /// Alle spielbaren Helden. Neuen Helden hinzufügen: Eintrag unten ergänzen –
    /// er erscheint automatisch im Gacha-Pool. Ein 3D-Modell mit gleicher Id unter
    /// Assets/_Game/Resources/Characters/ ersetzt das Platzhalter-Modell.
    /// </summary>
    public static class CharacterContent
    {
        const TargetType One = TargetType.SingleEnemy;
        const TargetType AllFoes = TargetType.AllEnemies;
        const TargetType Me = TargetType.Self;
        const TargetType Weakest = TargetType.LowestHpAlly;
        const TargetType Team = TargetType.AllAllies;
        const EffectTarget Hit = EffectTarget.SkillTargets;

        public static List<CharacterDefinition> All()
        {
            return new List<CharacterDefinition>
            {
                // ============================================================ SSR
                new CharacterDefinition
                {
                    Id = "kaito", Name = "Kaito Hayabusa", Title = "Klinge des Morgenrots",
                    Rarity = Rarity.SSR, Element = Element.Fire, Role = Role.Attacker,
                    BaseHp = 1500, BaseAtk = 165, BaseDef = 80,
                    HairColor = "#E8442E", OutfitColor = "#2B2B3A", EyeColor = "#FFB347",
                    Lore = "Schwertkämpfer aus dem Flammenkloster Akatsuki. Er hat geschworen, jeden Aether-Riss zu schließen – und sucht den Mann, der sein Kloster verraten hat.",
                    Skills = new[]
                    {
                        Attack("kaito_1", "Flammenschnitt", One, 1.3f, 2.0f, 3.1f,
                            "Ein glühender Hieb, der das Ziel in Brand setzen kann.",
                            Fx(StatusType.Burn, Hit, 0.25f, 0.35f, 0.5f).Chance(0.5f, 0.7f, 1f)),
                        Attack("kaito_2", "Phönixwirbel", AllFoes, 0.75f, 1.15f, 1.8f,
                            "Ein Flammenwirbel trifft alle Gegner.")
                    },
                    Ultimate = Ultimate("kaito_u", "Morgenrot-Sturz", One, 4.5f,
                        "Kaito stürzt wie die aufgehende Sonne herab. Erhöht danach seinen Angriff.",
                        Fx(StatusType.AttackUp, EffectTarget.Self, 0.3f))
                },
                new CharacterDefinition
                {
                    Id = "yuki", Name = "Yuki Shirogane", Title = "Eisprinzessin des Nordens",
                    Rarity = Rarity.SSR, Element = Element.Water, Role = Role.Support,
                    BaseHp = 1450, BaseAtk = 150, BaseDef = 90,
                    HairColor = "#DDEEFF", OutfitColor = "#3A6FD8", EyeColor = "#7FD4FF",
                    Lore = "Thronerbin des Frostreichs Hyōmon. Sie verließ den Palast, als die Risse den ewigen Winter ihrer Heimat zum Schmelzen brachten.",
                    Skills = new[]
                    {
                        Attack("yuki_1", "Frostlanze", One, 1.2f, 1.8f, 2.7f,
                            "Eine Eislanze, die die Verteidigung des Ziels senkt.",
                            Fx(StatusType.DefenseDown, Hit, 0.2f, 0.3f, 0.4f)),
                        Support("yuki_2", "Kristallbarriere", Team,
                            "Schützt alle Verbündeten mit einem Eisschild.",
                            Fx(StatusType.Shield, Hit, 0.1f, 0.16f, 0.25f))
                    },
                    Ultimate = Ultimate("yuki_u", "Ewiger Winter", AllFoes, 2.6f,
                        "Ein Schneesturm trifft alle Gegner und kann sie einfrieren.",
                        Fx(StatusType.Stun, Hit, 0f, 1).Chance(0.5f))
                },
                new CharacterDefinition
                {
                    Id = "ren", Name = "Ren Kurogane", Title = "Schattenklinge",
                    Rarity = Rarity.SSR, Element = Element.Dark, Role = Role.Attacker,
                    BaseHp = 1350, BaseAtk = 175, BaseDef = 70,
                    HairColor = "#1E1B2E", OutfitColor = "#6A3FA0", EyeColor = "#C77DFF",
                    Lore = "Ein Auftragsmörder ohne Erinnerung, der aus einem Riss gestolpert ist. Sein Schatten bewegt sich manchmal von selbst.",
                    Skills = new[]
                    {
                        Attack("ren_1", "Schattenstich", One, 1.45f, 2.2f, 3.4f,
                            "Ein lautloser Stich mit hohem Schaden."),
                        Support("ren_2", "Nachtschleier", Me,
                            "Ren verschmilzt mit den Schatten und erhöht seinen Angriff.",
                            Fx(StatusType.AttackUp, EffectTarget.Self, 0.2f, 0.3f, 0.45f))
                    },
                    Ultimate = Ultimate("ren_u", "Mondfinsternis", One, 5.0f,
                        "Ein Schnitt aus reiner Dunkelheit. Senkt den Angriff des Ziels.",
                        Fx(StatusType.AttackDown, Hit, 0.3f))
                },
                new CharacterDefinition
                {
                    Id = "aiko", Name = "Aiko Hoshino", Title = "Sternenheilerin",
                    Rarity = Rarity.SSR, Element = Element.Light, Role = Role.Healer,
                    BaseHp = 1550, BaseAtk = 140, BaseDef = 95,
                    HairColor = "#FFD6E8", OutfitColor = "#FFFFFF", EyeColor = "#FFC94D",
                    Lore = "Priesterin des Sternentempels. Man sagt, sie kann die Lieder der Sterne hören – und dass sie in letzter Zeit verstummen.",
                    Skills = new[]
                    {
                        Heal("aiko_1", "Sternensegen", Team, 0.5f, 0.8f, 1.2f,
                            "Heilt alle Verbündeten."),
                        Attack("aiko_2", "Lichtpfeil", One, 1.1f, 1.7f, 2.6f,
                            "Ein Pfeil aus Sternenlicht.")
                    },
                    Ultimate = UltimateHeal("aiko_u", "Himmelschor", Team, 1.8f,
                        "Heilt alle Verbündeten stark und erhöht ihren Angriff.",
                        Fx(StatusType.AttackUp, Hit, 0.25f))
                },

                // ============================================================ SR
                new CharacterDefinition
                {
                    Id = "haru", Name = "Haru Kazama", Title = "Sturmläufer",
                    Rarity = Rarity.SR, Element = Element.Wind, Role = Role.Attacker,
                    BaseHp = 1250, BaseAtk = 130, BaseDef = 65,
                    HairColor = "#7FE0A0", OutfitColor = "#2E5E4E", EyeColor = "#3CB371",
                    Lore = "Bote des Schreins von Kirahana und der schnellste Läufer des Tals. Redet mehr, als ihm guttut.",
                    Skills = new[]
                    {
                        Attack("haru_1", "Windklinge", One, 1.25f, 1.9f, 2.9f,
                            "Eine messerscharfe Windböe."),
                        Attack("haru_2", "Böenschlag", AllFoes, 0.7f, 1.1f, 1.7f,
                            "Ein Windstoß trifft alle Gegner.")
                    },
                    Ultimate = Ultimate("haru_u", "Orkanschnitt", AllFoes, 2.4f,
                        "Haru rast als Wirbelsturm durch die Gegnerreihen.")
                },
                new CharacterDefinition
                {
                    Id = "mei", Name = "Mei Tsuchiya", Title = "Felsenwächterin",
                    Rarity = Rarity.SR, Element = Element.Earth, Role = Role.Defender,
                    BaseHp = 1450, BaseAtk = 115, BaseDef = 95,
                    HairColor = "#8B5A2B", OutfitColor = "#C8A064", EyeColor = "#A0522D",
                    Lore = "Torwächterin der Bergfestung Ganseki. Sie hat noch nie einen Kampf verloren – sagt sie.",
                    Skills = new[]
                    {
                        Attack("mei_1", "Steinfaust", One, 1.1f, 1.65f, 2.5f,
                            "Ein wuchtiger Schlag, der betäuben kann.",
                            Fx(StatusType.Stun, Hit, 0f, 1).Chance(0.2f, 0.3f, 0.45f)),
                        Support("mei_2", "Erdwall", Team,
                            "Erhöht die Verteidigung aller Verbündeten.",
                            Fx(StatusType.DefenseUp, Hit, 0.2f, 0.3f, 0.45f))
                    },
                    Ultimate = Ultimate("mei_u", "Bergbrecher", One, 3.5f,
                        "Ein Schlag, der Berge spaltet. Betäubt das Ziel sicher.",
                        Fx(StatusType.Stun, Hit, 0f, 1))
                },
                new CharacterDefinition
                {
                    Id = "sora", Name = "Sora Amane", Title = "Gezeitenpriesterin",
                    Rarity = Rarity.SR, Element = Element.Water, Role = Role.Healer,
                    BaseHp = 1300, BaseAtk = 120, BaseDef = 75,
                    HairColor = "#4FC3D9", OutfitColor = "#E0F4FF", EyeColor = "#1E90FF",
                    Lore = "Hüterin des Gezeitenschreins von Seiryu. Ruhig wie das Meer – bis jemand ihre Stadt bedroht.",
                    Skills = new[]
                    {
                        Heal("sora_1", "Heilende Welle", Weakest, 0.9f, 1.4f, 2.1f,
                            "Heilt den Verbündeten mit den wenigsten LP."),
                        Attack("sora_2", "Wasserblase", One, 1.0f, 1.5f, 2.3f,
                            "Eine Blase aus Meerwasser.")
                    },
                    Ultimate = UltimateHeal("sora_u", "Flut des Lebens", Team, 1.4f,
                        "Heilt alle Verbündeten und schützt sie mit einem Wasserschild.",
                        Fx(StatusType.Shield, Hit, 0.12f))
                },
                new CharacterDefinition
                {
                    Id = "jin", Name = "Jin Kuroba", Title = "Fluchweber",
                    Rarity = Rarity.SR, Element = Element.Dark, Role = Role.Support,
                    BaseHp = 1250, BaseAtk = 125, BaseDef = 70,
                    HairColor = "#5B2A86", OutfitColor = "#222222", EyeColor = "#FF4F8B",
                    Lore = "Ein Fluchgelehrter, der von der Akademie verbannt wurde. Er schwört, seine Flüche nur noch für Gutes zu nutzen. Meistens.",
                    Skills = new[]
                    {
                        Attack("jin_1", "Schwächefluch", AllFoes, 0.4f, 0.6f, 0.9f,
                            "Verflucht alle Gegner und senkt ihren Angriff.",
                            Fx(StatusType.AttackDown, Hit, 0.15f, 0.22f, 0.3f)),
                        Attack("jin_2", "Dunkler Strahl", One, 1.2f, 1.8f, 2.7f,
                            "Ein Strahl aus verdichteter Finsternis.")
                    },
                    Ultimate = Ultimate("jin_u", "Seelenfessel", AllFoes, 2.0f,
                        "Fesselt die Seelen aller Gegner und senkt ihre Verteidigung.",
                        Fx(StatusType.DefenseDown, Hit, 0.3f))
                },

                // ============================================================ R
                new CharacterDefinition
                {
                    Id = "taro", Name = "Taro", Title = "Rekrut der Flammengarde",
                    Rarity = Rarity.R, Element = Element.Fire, Role = Role.Attacker,
                    BaseHp = 1100, BaseAtk = 105, BaseDef = 60,
                    HairColor = "#FF8A3D", OutfitColor = "#5A3A2A", EyeColor = "#8B4513",
                    Lore = "Frisch in der Flammengarde und fest entschlossen, eines Tages Hauptmann zu werden.",
                    Skills = new[]
                    {
                        Attack("taro_1", "Fackelhieb", One, 1.2f, 1.8f, 2.7f, "Ein Hieb mit brennender Klinge."),
                        Attack("taro_2", "Funkenregen", AllFoes, 0.6f, 0.95f, 1.45f, "Funken regnen auf alle Gegner.")
                    },
                    Ultimate = Ultimate("taro_u", "Flammenstoß", One, 3.2f, "Ein mutiger Sturmangriff.")
                },
                new CharacterDefinition
                {
                    Id = "nami", Name = "Nami", Title = "Harpunenfischerin",
                    Rarity = Rarity.R, Element = Element.Water, Role = Role.Attacker,
                    BaseHp = 1050, BaseAtk = 100, BaseDef = 55,
                    HairColor = "#2F7FD1", OutfitColor = "#F2E2C4", EyeColor = "#1C4E80",
                    Lore = "Fischerstochter aus Kirahana. Trifft mit ihrer Harpune alles, was sich bewegt – und manches, was sich nicht bewegt.",
                    Skills = new[]
                    {
                        Attack("nami_1", "Harpunenwurf", One, 1.2f, 1.8f, 2.7f, "Ein gezielter Harpunenwurf."),
                        Attack("nami_2", "Gischtwelle", AllFoes, 0.6f, 0.95f, 1.45f, "Eine Welle trifft alle Gegner.")
                    },
                    Ultimate = Ultimate("nami_u", "Große Flut", AllFoes, 2.0f, "Nami ruft eine Flutwelle herbei.")
                },
                new CharacterDefinition
                {
                    Id = "kenta", Name = "Kenta", Title = "Schmiedelehrling",
                    Rarity = Rarity.R, Element = Element.Earth, Role = Role.Defender,
                    BaseHp = 1200, BaseAtk = 95, BaseDef = 75,
                    HairColor = "#6B4A2F", OutfitColor = "#8A8A8A", EyeColor = "#5C4033",
                    Lore = "Lehrling in der Schmiede von Kirahana. Sein Hammer ist schwerer als er selbst.",
                    Skills = new[]
                    {
                        Attack("kenta_1", "Hammerschlag", One, 1.1f, 1.65f, 2.5f,
                            "Senkt die Verteidigung des Ziels.",
                            Fx(StatusType.DefenseDown, Hit, 0.15f, 0.22f, 0.3f)),
                        Support("kenta_2", "Schmiedeschild", Me,
                            "Kenta schützt sich mit einem Schild.",
                            Fx(StatusType.Shield, EffectTarget.Self, 0.15f, 0.25f, 0.4f))
                    },
                    Ultimate = Ultimate("kenta_u", "Ambossfall", One, 3.0f,
                        "Ein Amboss fällt vom Himmel. Kann betäuben.",
                        Fx(StatusType.Stun, Hit, 0f, 1).Chance(0.5f))
                },
                new CharacterDefinition
                {
                    Id = "lina", Name = "Lina", Title = "Botenläuferin",
                    Rarity = Rarity.R, Element = Element.Wind, Role = Role.Support,
                    BaseHp = 1000, BaseAtk = 100, BaseDef = 55,
                    HairColor = "#B8F28C", OutfitColor = "#3D6B8C", EyeColor = "#2E8B57",
                    Lore = "Harus kleine Schwester. Will ihm unbedingt beweisen, dass sie schneller ist.",
                    Skills = new[]
                    {
                        Support("lina_1", "Rückenwind", Team,
                            "Erhöht den Angriff aller Verbündeten.",
                            Fx(StatusType.AttackUp, Hit, 0.1f, 0.15f, 0.25f)),
                        Attack("lina_2", "Wirbeltritt", One, 1.1f, 1.65f, 2.5f, "Ein schneller Tritt.")
                    },
                    Ultimate = Support("lina_u", "Sturmbotschaft", Team,
                        "Stark erhöhter Angriff für alle Verbündeten.",
                        Fx(StatusType.AttackUp, Hit, 0.35f))
                }
            };
        }
    }
}
