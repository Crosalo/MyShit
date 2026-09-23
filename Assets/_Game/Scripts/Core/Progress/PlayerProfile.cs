using System;
using System.Collections.Generic;

namespace Aether.Core
{
    public enum TutorialPhase
    {
        /// <summary>Prolog-Kampf mit Kartenerklärung.</summary>
        Battle = 0,

        /// <summary>Erste Beschwörung und Team-Aufstellung.</summary>
        Summon = 1,

        Done = 2
    }

    [Serializable]
    public class OwnedCharacter
    {
        public string Id;
        public int Level = 1;
        public int Exp;
        public int LimitBreak;
    }

    /// <summary>Spielstand. Nur öffentliche Felder, damit Unitys JsonUtility ihn speichern kann.</summary>
    [Serializable]
    public class PlayerProfile
    {
        public int Version = 1;
        public string Name = "Beschwörer";
        public int Crystals;
        public int Gold;
        public List<OwnedCharacter> Characters = new List<OwnedCharacter>();
        public List<string> Team = new List<string>();
        public List<string> ClearedStages = new List<string>();
        public List<PityState> Pity = new List<PityState>();
        public int TutorialPhase;
        public int LastDailyClaimDay = -1;
        public int BattlesWon;

        public TutorialPhase Tutorial
        {
            get { return (TutorialPhase)TutorialPhase; }
            set { TutorialPhase = (int)value; }
        }
    }
}
