import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/character.dart';
import '../providers/game_provider.dart';
import '../widgets/character_card.dart';
import '../theme.dart';

class GachaScreen extends StatefulWidget {
  const GachaScreen({super.key});

  @override
  State<GachaScreen> createState() => _GachaScreenState();
}

class _GachaScreenState extends State<GachaScreen> with SingleTickerProviderStateMixin {
  List<Character>? _pullResults;
  bool _isAnimating = false;
  late AnimationController _animController;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeIn);
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  Future<void> _doPull(int count) async {
    final provider = context.read<GameProvider>();
    setState(() {
      _isAnimating = true;
      _pullResults = null;
    });

    _animController.reset();
    await Future.delayed(const Duration(milliseconds: 1200));

    final results = provider.performPull(count);
    setState(() {
      _pullResults = results;
      _isAnimating = false;
    });

    _animController.forward();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GameProvider>();
    final player = provider.player;

    return Scaffold(
      backgroundColor: kBgDark,
      appBar: AppBar(
        title: const Text('Beschwörungs-Portal'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Row(
              children: [
                const Text('💎 ', style: TextStyle(fontSize: 16)),
                Text(
                  player.gems.toString(),
                  style: const TextStyle(
                    color: kAccentGold,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              _buildBannerCard(),
              const SizedBox(height: 16),
              _buildRatesCard(player.pityCounter),
              const SizedBox(height: 16),
              _buildPullButtons(provider),
              const SizedBox(height: 16),
              if (_isAnimating) _buildPullingAnimation(),
              if (_pullResults != null && !_isAnimating)
                FadeTransition(
                  opacity: _fadeAnim,
                  child: _buildResults(_pullResults!, player),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBannerCard() {
    return Container(
      height: 180,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          colors: [Color(0xFF1A0533), Color(0xFF3D0A6B), Color(0xFF1A0533)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: [
          BoxShadow(color: kAccentPurple.withOpacity(0.3), blurRadius: 20, spreadRadius: 2),
        ],
      ),
      child: Stack(
        children: [
          Positioned(
            left: 16,
            top: 16,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.red.shade800,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text('BEGRENZT', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(height: 8),
                Text(
                  'Legendäre Helden',
                  style: GoogleFonts.cinzelDecorative(
                    color: kAccentGold,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                const Text('Erhalte die legendären Helden!', style: TextStyle(color: kTextSecondary, fontSize: 12)),
                const SizedBox(height: 12),
                Row(
                  children: const [
                    Text('🔥 ', style: TextStyle(fontSize: 20)),
                    Text('☀️ ', style: TextStyle(fontSize: 20)),
                    Text('🌑 ', style: TextStyle(fontSize: 20)),
                    Text('🐺 ', style: TextStyle(fontSize: 20)),
                    Text('❄️ ', style: TextStyle(fontSize: 20)),
                  ],
                ),
              ],
            ),
          ),
          const Positioned(
            right: 16,
            bottom: 16,
            child: Text('✨', style: TextStyle(fontSize: 60)),
          ),
        ],
      ),
    );
  }

  Widget _buildRatesCard(int pityCounter) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kAccentPurple.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Beschwörungs-Raten', style: TextStyle(color: kTextPrimary, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _rateChip('SSR', '3%', kColorSSR),
              _rateChip('SR', '15%', kColorSR),
              _rateChip('R', '82%', kColorR),
            ],
          ),
          const SizedBox(height: 8),
          const Divider(color: Colors.white12),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('🛡️ Pity-Zähler (SSR bei 90)', style: TextStyle(color: kTextSecondary, fontSize: 12)),
              Text(
                '$pityCounter / 90',
                style: TextStyle(
                  color: pityCounter > 70 ? kAccentGold : kTextPrimary,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: pityCounter / 90,
            backgroundColor: Colors.white12,
            valueColor: AlwaysStoppedAnimation<Color>(
              pityCounter > 70 ? kAccentGold : kAccentPurple,
            ),
            minHeight: 4,
          ),
        ],
      ),
    );
  }

  Widget _rateChip(String rarity, String rate, Color color) {
    return Column(
      children: [
        Text(rate, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
        Text(rarity, style: TextStyle(color: color.withOpacity(0.7), fontSize: 11)),
      ],
    );
  }

  Widget _buildPullButtons(GameProvider provider) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _pullButton(
                '1x Ziehen',
                '💎 10',
                provider.canSinglePull,
                kAccentPurple,
                () => _doPull(1),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _pullButton(
                '10x Ziehen',
                '💎 100',
                provider.canTenPull,
                kAccentGold,
                () => _doPull(10),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          '10x garantiert mindestens 1x SR oder besser!',
          style: const TextStyle(color: kTextSecondary, fontSize: 12),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _pullButton(String label, String cost, bool enabled, Color color, VoidCallback onTap) {
    return GestureDetector(
      onTap: enabled && !_isAnimating ? onTap : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        height: 70,
        decoration: BoxDecoration(
          gradient: enabled
              ? LinearGradient(
                  colors: [color.withOpacity(0.6), color],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: enabled ? null : Colors.grey.shade800,
          borderRadius: BorderRadius.circular(14),
          boxShadow: enabled
              ? [BoxShadow(color: color.withOpacity(0.4), blurRadius: 10, spreadRadius: 1)]
              : null,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              label,
              style: TextStyle(
                color: enabled ? Colors.white : Colors.grey,
                fontWeight: FontWeight.bold,
                fontSize: 15,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              cost,
              style: TextStyle(
                color: enabled ? Colors.white70 : Colors.grey,
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPullingAnimation() {
    return Container(
      height: 200,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(
            width: 60,
            height: 60,
            child: CircularProgressIndicator(
              color: kAccentGold,
              strokeWidth: 3,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            '✨ Die Geister werden beschworen... ✨',
            style: GoogleFonts.cinzelDecorative(color: kAccentGold, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildResults(List<Character> results, player) {
    final ownedIds = player.ownedCharacterIds as List<String>;
    // Track which are newly added
    final countBefore = <String, int>{};
    for (final id in ownedIds) {
      countBefore[id] = (countBefore[id] ?? 0) + 1;
    }

    final hasSSR = results.any((c) => c.rarity == Rarity.ssr);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: hasSSR ? kAccentGold.withOpacity(0.6) : kAccentPurple.withOpacity(0.3),
          width: hasSSR ? 2 : 1,
        ),
        boxShadow: hasSSR
            ? [BoxShadow(color: kAccentGold.withOpacity(0.3), blurRadius: 20)]
            : null,
      ),
      child: Column(
        children: [
          Text(
            hasSSR ? '🌟 LEGENDÄR! 🌟' : results.any((c) => c.rarity == Rarity.sr) ? '✨ Glückstreffer!' : 'Beschwörung abgeschlossen',
            style: GoogleFonts.cinzelDecorative(
              color: hasSSR ? kAccentGold : kAccentPurple,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: results.length == 1 ? 1 : results.length <= 3 ? 3 : 5,
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
              childAspectRatio: 0.75,
            ),
            itemCount: results.length,
            itemBuilder: (ctx, i) {
              final char = results[i];
              return PullResultCard(char: char);
            },
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () => setState(() => _pullResults = null),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: kAccentPurple),
            ),
            child: const Text('Schließen', style: TextStyle(color: kAccentPurple)),
          ),
        ],
      ),
    );
  }
}
