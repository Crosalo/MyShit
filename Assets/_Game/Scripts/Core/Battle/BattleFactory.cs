using System.Collections.Generic;

namespace Aether.Core
{
    public static class BattleFactory
    {
        /// <summary>Baut einen Kampf aus Stage und Spielstand (Team, Level, Durchbrüche).</summary>
        public static BattleSetup Create(StageDefinition stage, PlayerProfile profile, IRandom random)
        {
            var setup = new BattleSetup
            {
                Random = stage.Seed != 0 ? new SystemRandom(stage.Seed) : random,
                InitialHand = stage.InitialHand,
                InitialGauge = stage.InitialGauge
            };

            IList<string> team = stage.FixedTeam ?? (IList<string>)profile.Team;
            for (int i = 0; i < team.Count; i++)
            {
                var def = GameDatabase.FindCharacter(team[i]);
                if (def == null) continue;
                var owned = ProfileService.Find(profile, def.Id);
                int level = owned != null ? owned.Level : 1;
                int limitBreak = owned != null ? owned.LimitBreak : 0;
                setup.Players.Add(new BattleUnit(def, level, limitBreak, setup.Players.Count));
            }

            foreach (var wave in stage.Waves)
            {
                var units = new List<BattleUnit>();
                foreach (var spawn in wave)
                {
                    var enemy = GameDatabase.FindEnemy(spawn.EnemyId);
                    if (enemy != null) units.Add(new BattleUnit(enemy, spawn.Level, units.Count));
                }
                if (units.Count > 0) setup.Waves.Add(units);
            }
            return setup;
        }

        public static IList<string> TeamFor(StageDefinition stage, PlayerProfile profile)
        {
            return stage.FixedTeam ?? (IList<string>)profile.Team;
        }
    }
}
