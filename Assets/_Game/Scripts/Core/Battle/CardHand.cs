using System;
using System.Collections.Generic;

namespace Aether.Core
{
    public sealed class SkillCard
    {
        public int Uid;
        public readonly BattleUnit Owner;
        public readonly SkillDefinition Skill;
        public readonly bool IsUltimate;
        public int Rank;

        public SkillCard(BattleUnit owner, SkillDefinition skill, int rank, bool isUltimate = false)
        {
            Owner = owner;
            Skill = skill;
            Rank = rank;
            IsUltimate = isUltimate;
        }

        /// <summary>Zwei Karten verschmelzen, wenn Held, Fähigkeit und Rang gleich sind und Rang 3 noch nicht erreicht ist.</summary>
        public bool CanMergeWith(SkillCard other)
        {
            return other != null
                && !IsUltimate && !other.IsUltimate
                && Owner == other.Owner
                && Skill == other.Skill
                && Rank == other.Rank
                && Rank < Balance.MaxCardRank;
        }

        public SkillCard Clone()
        {
            return new SkillCard(Owner, Skill, Rank, IsUltimate) { Uid = Uid };
        }

        public override string ToString() { return Skill.Name + " R" + Rank; }
    }

    public struct MergeInfo
    {
        /// <summary>Die Karte, die nach dem Verschmelzen übrig bleibt (Rang schon erhöht).</summary>
        public SkillCard Result;

        /// <summary>Position der Ergebniskarte in der Hand.</summary>
        public int Index;

        public int ConsumedUid;
    }

    /// <summary>
    /// Die Kartenhand. Gleiche, benachbarte Karten verschmelzen automatisch –
    /// auch in Ketten (R1+R1 → R2, liegt daneben ein R2, entsteht direkt ein R3).
    /// </summary>
    public sealed class CardHand
    {
        readonly List<SkillCard> cards = new List<SkillCard>();
        int nextUid;

        public CardHand(int capacity)
        {
            Capacity = capacity;
        }

        public int Capacity { get; private set; }
        public int Count { get { return cards.Count; } }
        public IReadOnlyList<SkillCard> Cards { get { return cards; } }
        public SkillCard this[int index] { get { return cards[index]; } }
        public bool IsFull { get { return cards.Count >= Capacity; } }

        public void Add(SkillCard card)
        {
            card.Uid = ++nextUid;
            cards.Add(card);
        }

        public SkillCard RemoveAt(int index)
        {
            var card = cards[index];
            cards.RemoveAt(index);
            return card;
        }

        /// <summary>Nimmt die Karte bei <paramref name="from"/> heraus und fügt sie bei <paramref name="to"/> wieder ein.</summary>
        public void Move(int from, int to)
        {
            var card = cards[from];
            cards.RemoveAt(from);
            to = Math.Max(0, Math.Min(cards.Count, to));
            cards.Insert(to, card);
        }

        public List<MergeInfo> ResolveMerges()
        {
            var merges = new List<MergeInfo>();
            bool merged;
            do
            {
                merged = false;
                for (int i = 0; i < cards.Count - 1; i++)
                {
                    if (!cards[i].CanMergeWith(cards[i + 1])) continue;
                    var consumed = cards[i + 1];
                    cards.RemoveAt(i + 1);
                    cards[i].Rank++;
                    merges.Add(new MergeInfo { Result = cards[i], Index = i, ConsumedUid = consumed.Uid });
                    merged = true;
                    break;
                }
            } while (merged);
            return merges;
        }

        public int RemoveCardsOf(BattleUnit owner)
        {
            return cards.RemoveAll(c => c.Owner == owner);
        }

        public List<SkillCard> Snapshot()
        {
            var copy = new List<SkillCard>(cards.Count);
            foreach (var c in cards) copy.Add(c.Clone());
            return copy;
        }

        public void Restore(List<SkillCard> snapshot)
        {
            cards.Clear();
            foreach (var c in snapshot) cards.Add(c.Clone());
        }
    }
}
