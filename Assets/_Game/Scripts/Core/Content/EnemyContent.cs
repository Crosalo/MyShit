using System.Collections.Generic;
using static Aether.Core.Sk;

namespace Aether.Core
{
    public static class EnemyContent
    {
        const TargetType One = TargetType.SingleEnemy;
        const TargetType AllFoes = TargetType.AllEnemies;
        const EffectTarget Hit = EffectTarget.SkillTargets;

        public static List<EnemyDefinition> All()
        {
            return new List<EnemyDefinition>
            {
                new EnemyDefinition
                {
                    Id = "slime_blue", Name = "Aqua-Schleimling", Element = Element.Water,
                    Hp = 600, Atk = 55, Def = 25, Shape = BodyShape.Slime, Color = "#4FA8FF", Scale = 0.9f,
                    Skills = new[] { Attack("e_slime_hop", "Schleimsprung", One, 1f, 1.4f, 2f, "") }
                },
                new EnemyDefinition
                {
                    Id = "slime_red", Name = "Glut-Schleimling", Element = Element.Fire,
                    Hp = 600, Atk = 60, Def = 25, Shape = BodyShape.Slime, Color = "#FF6B4A", Scale = 0.9f,
                    Skills = new[]
                    {
                        Attack("e_slime_spit", "Glutspucke", One, 0.9f, 1.3f, 1.9f, "",
                            Fx(StatusType.Burn, Hit, 0.2f).Chance(0.3f))
                    }
                },
                new EnemyDefinition
                {
                    Id = "wolf", Name = "Aschewolf", Element = Element.Fire,
                    Hp = 700, Atk = 75, Def = 35, Shape = BodyShape.Beast, Color = "#5A4A48",
                    Skills = new[]
                    {
                        Attack("e_bite", "Biss", One, 1.1f, 1.6f, 2.3f, ""),
                        Support("e_howl", "Rudelgeheul", TargetType.Self, "",
                            Fx(StatusType.AttackUp, EffectTarget.AllAllies, 0.2f))
                    }
                },
                new EnemyDefinition
                {
                    Id = "kobold", Name = "Dornenkobold", Element = Element.Earth,
                    Hp = 650, Atk = 70, Def = 45, Shape = BodyShape.Humanoid, Color = "#7A8B3A", Scale = 0.75f,
                    Skills = new[]
                    {
                        Attack("e_thorn", "Dornenwurf", One, 1f, 1.5f, 2.2f, ""),
                        Attack("e_rockrain", "Steinhagel", AllFoes, 0.6f, 0.9f, 1.3f, "")
                    }
                },
                new EnemyDefinition
                {
                    Id = "harpy", Name = "Sturmharpyie", Element = Element.Wind,
                    Hp = 600, Atk = 80, Def = 30, Shape = BodyShape.Wisp, Color = "#9FE8C8",
                    Skills = new[]
                    {
                        Attack("e_clawwind", "Krallenwind", AllFoes, 0.7f, 1f, 1.5f, ""),
                        Attack("e_dive", "Sturzflug", One, 1.2f, 1.8f, 2.6f, "")
                    }
                },
                new EnemyDefinition
                {
                    Id = "wisp", Name = "Irrlicht", Element = Element.Light,
                    Hp = 500, Atk = 70, Def = 30, Shape = BodyShape.Wisp, Color = "#FFF2A8", Scale = 0.8f,
                    Skills = new[]
                    {
                        Attack("e_glare", "Blendlicht", One, 0.9f, 1.3f, 1.9f, "",
                            Fx(StatusType.AttackDown, Hit, 0.15f))
                    }
                },
                new EnemyDefinition
                {
                    Id = "shadow", Name = "Schattenkrieger", Element = Element.Dark,
                    Hp = 850, Atk = 90, Def = 50, Shape = BodyShape.Humanoid, Color = "#2A2238",
                    Skills = new[]
                    {
                        Attack("e_shadowcut", "Schattenhieb", One, 1.2f, 1.8f, 2.6f, ""),
                        Attack("e_darkaura", "Finstere Aura", AllFoes, 0.6f, 0.9f, 1.3f, "",
                            Fx(StatusType.DefenseDown, Hit, 0.15f).Chance(0.5f))
                    }
                },

                // ============================================================ Bosse
                new EnemyDefinition
                {
                    Id = "golem", Name = "Kristallgolem", Element = Element.Earth, IsBoss = true,
                    Hp = 3200, Atk = 95, Def = 90, Shape = BodyShape.Golem, Color = "#8FD3FF", Scale = 1.6f,
                    SkillRank = 2,
                    Skills = new[]
                    {
                        Attack("e_crystalfist", "Kristallfaust", One, 1.1f, 1.3f, 1.8f, "",
                            Fx(StatusType.Stun, Hit, 0f, 1).Chance(0.25f)),
                        Attack("e_quake", "Beben", AllFoes, 0.6f, 0.8f, 1.1f, "")
                    },
                    Ultimate = Ultimate("e_crystalstorm", "Kristallsturm", AllFoes, 1.6f, "")
                },
                new EnemyDefinition
                {
                    Id = "witch", Name = "Nebelhexe Morwen", Element = Element.Dark, IsBoss = true,
                    Hp = 4200, Atk = 110, Def = 70, Shape = BodyShape.Humanoid, Color = "#6B4C9A", Scale = 1.3f,
                    SkillRank = 2,
                    Skills = new[]
                    {
                        Attack("e_fogcurse", "Nebelfluch", AllFoes, 0.5f, 0.7f, 1f, "",
                            Fx(StatusType.AttackDown, Hit, 0.2f)),
                        Attack("e_shadowbolt", "Schattenblitz", One, 1.1f, 1.4f, 2f, "")
                    },
                    Ultimate = Ultimate("e_nightmare", "Albtraumnebel", AllFoes, 1.5f, "",
                        Fx(StatusType.Stun, Hit, 0f, 1).Chance(0.3f))
                },
                new EnemyDefinition
                {
                    Id = "knight", Name = "Varkas, der gefallene Ritter", Element = Element.Fire, IsBoss = true,
                    Hp = 5000, Atk = 115, Def = 100, Shape = BodyShape.Humanoid, Color = "#3B1F1F", Scale = 1.5f,
                    SkillRank = 2,
                    Skills = new[]
                    {
                        Attack("e_hellblade", "Höllenklinge", One, 1.2f, 1.5f, 2.1f, "",
                            Fx(StatusType.Burn, Hit, 0.3f)),
                        Attack("e_darkwave", "Dunkle Welle", AllFoes, 0.7f, 0.9f, 1.2f, "")
                    },
                    Ultimate = Ultimate("e_worldfire", "Weltenbrand", AllFoes, 1.7f, "",
                        Fx(StatusType.Burn, Hit, 0.25f))
                }
            };
        }
    }
}
