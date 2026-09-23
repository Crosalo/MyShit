namespace Aether.Core
{
    /// <summary>Zufallsquelle als Interface, damit Kämpfe und Beschwörungen in Tests reproduzierbar sind.</summary>
    public interface IRandom
    {
        /// <summary>Wert in [0, 1).</summary>
        float NextFloat();

        /// <summary>Ganzzahl in [0, maxExclusive).</summary>
        int Next(int maxExclusive);
    }

    public sealed class SystemRandom : IRandom
    {
        readonly System.Random random;

        public SystemRandom() { random = new System.Random(); }
        public SystemRandom(int seed) { random = new System.Random(seed); }

        public float NextFloat() { return (float)random.NextDouble(); }
        public int Next(int maxExclusive) { return maxExclusive <= 0 ? 0 : random.Next(maxExclusive); }
    }
}
