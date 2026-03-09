import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/game_provider.dart';
import '../theme.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkDailyLogin());
  }

  void _checkDailyLogin() {
    final provider = context.read<GameProvider>();
    final reward = provider.claimDailyLogin();
    if (reward != null && mounted) {
      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          backgroundColor: kBgLight,
          title: Text(
            '🎁 Tägliche Belohnung!',
            style: GoogleFonts.cinzelDecorative(color: kAccentGold),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Tag ${reward['day']} in Folge!',
                style: const TextStyle(color: kTextSecondary),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _rewardChip('💎', '+${reward['gems']} Kristalle', kAccentPurple),
                  _rewardChip('🪙', '+${reward['gold']} Gold', kAccentGold),
                ],
              ),
            ],
          ),
          actions: [
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Danke!'),
            ),
          ],
        ),
      );
    }
  }

  Widget _rewardChip(String emoji, String text, Color color) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Column(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 24)),
          const SizedBox(height: 4),
          Text(text, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GameProvider>();
    final player = provider.player;

    return Scaffold(
      backgroundColor: kBgDark,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 200,
            floating: false,
            pinned: true,
            backgroundColor: kBgDark,
            flexibleSpace: FlexibleSpaceBar(
              background: _buildBanner(),
            ),
            title: Row(
              children: [
                Text(
                  'Realm Chronicles',
                  style: GoogleFonts.cinzelDecorative(
                    color: kAccentGold,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            actions: [
              _currencyChip('💎', player.gems.toString(), kAccentPurple),
              const SizedBox(width: 4),
              _currencyChip('🪙', player.gold.toString(), kAccentGold),
              const SizedBox(width: 8),
            ],
          ),
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                _buildPlayerCard(player, provider),
                const SizedBox(height: 16),
                _buildNewsSection(),
                const SizedBox(height: 16),
                _buildQuickActions(context),
                const SizedBox(height: 80),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBanner() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF1A0533), Color(0xFF0A0E1A)],
        ),
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(height: 40),
            Text(
              '⚔️ 🔥 🌑 ☀️ 🐺 🧚 💰 ⚔️',
              style: const TextStyle(fontSize: 22, letterSpacing: 4),
            ),
            const SizedBox(height: 8),
            Text(
              'REALM CHRONICLES',
              style: GoogleFonts.cinzelDecorative(
                color: kAccentGold,
                fontSize: 26,
                fontWeight: FontWeight.bold,
                letterSpacing: 4,
                shadows: [
                  Shadow(color: kAccentGold.withOpacity(0.5), blurRadius: 20),
                ],
              ),
            ),
            Text(
              'Anime Gacha RPG',
              style: GoogleFonts.cinzelDecorative(
                color: kTextSecondary,
                fontSize: 13,
                letterSpacing: 2,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _currencyChip(String emoji, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 14)),
          const SizedBox(width: 4),
          Text(value, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildPlayerCard(player, GameProvider provider) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kAccentPurple.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: const LinearGradient(
                    colors: [kAccentPurple, kAccentBlue],
                  ),
                ),
                child: const Center(child: Text('⚔️', style: TextStyle(fontSize: 28))),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      player.playerName,
                      style: const TextStyle(
                        color: kTextPrimary,
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                    Text(
                      'Kampfkraft: ${provider.totalPower}',
                      style: const TextStyle(color: kAccentGold, fontSize: 13),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${provider.ownedCharacters.length} Charaktere',
                    style: const TextStyle(color: kTextSecondary, fontSize: 12),
                  ),
                  Text(
                    '${player.totalPulls} Züge gesamt',
                    style: const TextStyle(color: kTextSecondary, fontSize: 12),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (provider.ownedCharacters.isNotEmpty) ...[
            const Text('Aktives Team:', style: TextStyle(color: kTextSecondary, fontSize: 12)),
            const SizedBox(height: 6),
            Row(
              children: provider.teamCharacters.map((c) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Column(
                    children: [
                      Text(c.character.emoji, style: const TextStyle(fontSize: 28)),
                      Text(c.character.name,
                          style: const TextStyle(color: kTextSecondary, fontSize: 10)),
                    ],
                  ),
                );
              }).toList(),
            ),
          ] else
            const Text(
              '🎯 Ziehe deinen ersten Charakter!',
              style: TextStyle(color: kAccentGold, fontSize: 13),
            ),
        ],
      ),
    );
  }

  Widget _buildNewsSection() {
    final news = [
      {'icon': '🌟', 'title': 'Neue Banners verfügbar!', 'text': 'SSR Zorn & Sol — begrenzte Zeit'},
      {'icon': '⚔️', 'title': 'Story Kapitel 5 ist da!', 'text': 'Konfrontiere Dämonenlord Moros'},
      {'icon': '🎁', 'title': 'Tägliche Belohnung', 'text': 'Einloggen für Kristalle & Gold!'},
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Neuigkeiten', style: TextStyle(color: kTextSecondary, fontSize: 14)),
        const SizedBox(height: 8),
        ...news.map(
          (item) => Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kCardBg,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Text(item['icon']!, style: const TextStyle(fontSize: 24)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(item['title']!,
                          style: const TextStyle(
                              color: kTextPrimary, fontWeight: FontWeight.bold, fontSize: 13)),
                      Text(item['text']!,
                          style: const TextStyle(color: kTextSecondary, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Schnellaktionen', style: TextStyle(color: kTextSecondary, fontSize: 14)),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _actionButton(
                '🎰',
                'Gacha',
                kAccentPurple,
                () => DefaultTabController.of(context)
                    .animateTo(1),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _actionButton(
                '📖',
                'Story',
                kAccentBlue,
                () => DefaultTabController.of(context)
                    .animateTo(2),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _actionButton(
                '👥',
                'Sammlung',
                const Color(0xFF26A69A),
                () => DefaultTabController.of(context)
                    .animateTo(3),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _actionButton(String emoji, String label, Color color, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 80,
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.4)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 28)),
            const SizedBox(height: 4),
            Text(label, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
