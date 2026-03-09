import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/quest.dart';
import '../providers/game_provider.dart';
import '../theme.dart';
import 'battle_screen.dart';

class StoryScreen extends StatefulWidget {
  const StoryScreen({super.key});

  @override
  State<StoryScreen> createState() => _StoryScreenState();
}

class _StoryScreenState extends State<StoryScreen> {
  int _selectedChapter = 0;

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GameProvider>();
    final chapters = provider.chapters;

    return Scaffold(
      backgroundColor: kBgDark,
      appBar: AppBar(
        title: Text('Story', style: GoogleFonts.cinzelDecorative(color: kAccentGold)),
      ),
      body: Row(
        children: [
          // Chapter list sidebar
          Container(
            width: 100,
            color: kBgMid,
            child: ListView.builder(
              itemCount: chapters.length,
              itemBuilder: (ctx, i) {
                final chapter = chapters[i];
                final isUnlocked = i == 0 ||
                    provider.isStageCompleted(chapters[i - 1].stages.last.id);
                final isSelected = _selectedChapter == i;

                return GestureDetector(
                  onTap: isUnlocked ? () => setState(() => _selectedChapter = i) : null,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
                    color: isSelected ? kAccentPurple.withOpacity(0.2) : Colors.transparent,
                    child: Column(
                      children: [
                        Text(
                          isUnlocked ? '📖' : '🔒',
                          style: const TextStyle(fontSize: 24),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Kap. ${chapter.id}',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: isSelected
                                ? kAccentGold
                                : isUnlocked
                                    ? kTextPrimary
                                    : kTextSecondary,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          // Stage content
          Expanded(
            child: _buildChapterContent(context, chapters[_selectedChapter], provider),
          ),
        ],
      ),
    );
  }

  Widget _buildChapterContent(BuildContext context, Chapter chapter, GameProvider provider) {
    final isChapterUnlocked = chapter.id == 1 ||
        provider.isStageCompleted(provider.chapters[chapter.id - 2].stages.last.id);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Chapter header
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF1A1040), Color(0xFF0A0E1A)],
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: kAccentPurple.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  chapter.title,
                  style: GoogleFonts.cinzelDecorative(
                    color: kAccentGold,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  chapter.description,
                  style: const TextStyle(color: kTextSecondary, fontSize: 12),
                ),
                const SizedBox(height: 8),
                GestureDetector(
                  onTap: () => _showStoryDialog(context, chapter),
                  child: Row(
                    children: [
                      const Icon(Icons.menu_book, size: 14, color: kAccentBlue),
                      const SizedBox(width: 4),
                      const Text('Geschichte lesen', style: TextStyle(color: kAccentBlue, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // Stages
          ...chapter.stages.asMap().entries.map((entry) {
            final i = entry.key;
            final stage = entry.value;
            final isCompleted = provider.isStageCompleted(stage.id);
            final isUnlocked = isChapterUnlocked &&
                (i == 0 || provider.isStageCompleted(chapter.stages[i - 1].id));

            return _buildStageCard(context, stage, isCompleted, isUnlocked, provider);
          }),
        ],
      ),
    );
  }

  Widget _buildStageCard(
    BuildContext context,
    Stage stage,
    bool isCompleted,
    bool isUnlocked,
    GameProvider provider,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isCompleted
              ? kHpHigh.withOpacity(0.4)
              : isUnlocked
                  ? kAccentPurple.withOpacity(0.3)
                  : Colors.white12,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  isCompleted ? '✅' : isUnlocked ? '⚔️' : '🔒',
                  style: const TextStyle(fontSize: 20),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        stage.name,
                        style: TextStyle(
                          color: isUnlocked ? kTextPrimary : kTextSecondary,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                      Text(
                        stage.description,
                        style: const TextStyle(color: kTextSecondary, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                if (isUnlocked)
                  ElevatedButton(
                    onPressed: () => _startBattle(context, stage, provider),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isCompleted ? Colors.green.shade800 : kAccentPurple,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    ),
                    child: Text(
                      isCompleted ? 'Nochmal' : 'Kämpfen!',
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    _rewardChip('💎', stage.gemReward.toString()),
                    const SizedBox(width: 6),
                    _rewardChip('🪙', stage.goldReward.toString()),
                    const SizedBox(width: 6),
                    _rewardChip('⭐', 'EXP +${stage.expReward}'),
                  ],
                ),
                Text(
                  '⚡ ${stage.recommendedPower}',
                  style: TextStyle(
                    color: provider.totalPower >= stage.recommendedPower
                        ? kHpHigh
                        : kHpLow,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _rewardChip(String emoji, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 11)),
          const SizedBox(width: 2),
          Text(value, style: const TextStyle(color: kTextSecondary, fontSize: 11)),
        ],
      ),
    );
  }

  void _showStoryDialog(BuildContext context, Chapter chapter) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: kBgLight,
        title: Text(
          chapter.title,
          style: GoogleFonts.cinzelDecorative(color: kAccentGold, fontSize: 14),
        ),
        content: Text(
          chapter.storyText,
          style: const TextStyle(color: kTextPrimary, height: 1.7, fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Schließen', style: TextStyle(color: kAccentPurple)),
          ),
        ],
      ),
    );
  }

  void _startBattle(BuildContext context, Stage stage, GameProvider provider) {
    if (provider.ownedCharacters.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Du brauchst Charaktere! Gehe zum Gacha-Portal.'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final battleState = provider.createBattle(stage);
    if (battleState == null) return;

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => BattleScreen(
          battleState: battleState,
          stage: stage,
        ),
      ),
    ).then((_) {
      // Refresh state after battle
      setState(() {});
    });
  }
}
