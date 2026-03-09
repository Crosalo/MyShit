import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/character.dart';
import '../providers/game_provider.dart';
import '../widgets/character_card.dart';
import '../widgets/stat_bar.dart';
import '../theme.dart';

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key});

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  String _filterRarity = 'Alle';
  String _sortBy = 'ATK';

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GameProvider>();
    final allOwned = provider.ownedCharacters;

    List<OwnedCharacter> filtered = allOwned.where((o) {
      if (_filterRarity == 'SSR') return o.character.rarity == Rarity.ssr;
      if (_filterRarity == 'SR') return o.character.rarity == Rarity.sr;
      if (_filterRarity == 'R') return o.character.rarity == Rarity.r;
      return true;
    }).toList();

    filtered.sort((a, b) {
      if (_sortBy == 'ATK') return b.atk.compareTo(a.atk);
      if (_sortBy == 'HP') return b.maxHp.compareTo(a.maxHp);
      if (_sortBy == 'Lv') return b.level.compareTo(a.level);
      return a.character.name.compareTo(b.character.name);
    });

    return Scaffold(
      backgroundColor: kBgDark,
      appBar: AppBar(
        title: Text(
          'Sammlung (${allOwned.length})',
          style: GoogleFonts.cinzelDecorative(color: kAccentGold),
        ),
      ),
      body: Column(
        children: [
          _buildFilters(),
          Expanded(
            child: filtered.isEmpty
                ? _buildEmpty()
                : GridView.builder(
                    padding: const EdgeInsets.all(12),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                      childAspectRatio: 1.4,
                    ),
                    itemCount: filtered.length,
                    itemBuilder: (ctx, i) {
                      return CharacterCard(
                        owned: filtered[i],
                        onTap: () => _showCharacterDetail(context, filtered[i]),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilters() {
    return Container(
      color: kBgMid,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Column(
        children: [
          // Rarity filter
          Row(
            children: ['Alle', 'SSR', 'SR', 'R'].map((r) {
              final selected = _filterRarity == r;
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: GestureDetector(
                  onTap: () => setState(() => _filterRarity = r),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: selected
                          ? (r == 'SSR'
                              ? kColorSSR.withOpacity(0.3)
                              : r == 'SR'
                                  ? kColorSR.withOpacity(0.3)
                                  : r == 'R'
                                      ? kColorR.withOpacity(0.3)
                                      : kAccentPurple.withOpacity(0.3))
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: selected
                            ? (r == 'SSR'
                                ? kColorSSR
                                : r == 'SR'
                                    ? kColorSR
                                    : r == 'R'
                                        ? kColorR
                                        : kAccentPurple)
                            : Colors.white24,
                      ),
                    ),
                    child: Text(
                      r,
                      style: TextStyle(
                        color: selected ? Colors.white : kTextSecondary,
                        fontWeight: selected ? FontWeight.bold : FontWeight.normal,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 6),
          // Sort row
          Row(
            children: [
              const Text('Sortieren:', style: TextStyle(color: kTextSecondary, fontSize: 12)),
              const SizedBox(width: 8),
              ...['ATK', 'HP', 'Lv', 'Name'].map((s) {
                final selected = _sortBy == s;
                return Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: GestureDetector(
                    onTap: () => setState(() => _sortBy = s),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: selected ? kAccentPurple.withOpacity(0.3) : Colors.transparent,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: selected ? kAccentPurple : Colors.white24,
                        ),
                      ),
                      child: Text(
                        s,
                        style: TextStyle(
                          color: selected ? kAccentPurple : kTextSecondary,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('🎰', style: TextStyle(fontSize: 60)),
          const SizedBox(height: 16),
          Text(
            'Noch keine Charaktere!',
            style: GoogleFonts.cinzelDecorative(color: kTextPrimary, fontSize: 18),
          ),
          const SizedBox(height: 8),
          const Text(
            'Gehe zum Gacha-Portal und beschwöre\ndeine ersten Helden!',
            textAlign: TextAlign.center,
            style: TextStyle(color: kTextSecondary),
          ),
        ],
      ),
    );
  }

  void _showCharacterDetail(BuildContext context, OwnedCharacter owned) {
    final char = owned.character;
    showModalBottomSheet(
      context: context,
      backgroundColor: kBgLight,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => DraggableScrollableSheet(
        initialChildSize: 0.8,
        maxChildSize: 0.95,
        minChildSize: 0.5,
        expand: false,
        builder: (_, controller) => SingleChildScrollView(
          controller: controller,
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.white24,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                children: [
                  Text(char.emoji, style: const TextStyle(fontSize: 56)),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: rarityColor(char.rarityLabel).withOpacity(0.2),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: rarityColor(char.rarityLabel)),
                              ),
                              child: Text(
                                char.rarityLabel,
                                style: TextStyle(
                                  color: rarityColor(char.rarityLabel),
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          char.name,
                          style: GoogleFonts.cinzelDecorative(
                            color: kTextPrimary,
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(char.title, style: const TextStyle(color: kTextSecondary, fontSize: 14)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(char.elementLabel, style: const TextStyle(color: kTextSecondary, fontSize: 13)),
                  const SizedBox(width: 12),
                  Text(char.classLabel, style: const TextStyle(color: kTextSecondary, fontSize: 13)),
                  const Spacer(),
                  Text(
                    '×${owned.copies} Kopie${owned.copies > 1 ? "n" : ""}',
                    style: const TextStyle(color: kAccentGold, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const Divider(color: Colors.white12, height: 24),
              // Level & EXP
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Level ${owned.level}',
                      style: const TextStyle(color: kTextPrimary, fontWeight: FontWeight.bold, fontSize: 16)),
                  Text('${owned.experience} / ${owned.level * 100} EXP',
                      style: const TextStyle(color: kTextSecondary, fontSize: 12)),
                ],
              ),
              const SizedBox(height: 6),
              LinearProgressIndicator(
                value: owned.experience / (owned.level * 100),
                backgroundColor: Colors.white12,
                valueColor: const AlwaysStoppedAnimation<Color>(kAccentPurple),
                minHeight: 6,
              ),
              const SizedBox(height: 16),
              // Stats
              const Text('Kampfwerte', style: TextStyle(color: kTextSecondary, fontSize: 13)),
              const SizedBox(height: 8),
              _statRow('❤️ HP', owned.maxHp, 15000),
              const SizedBox(height: 6),
              _statRow('⚔️ ATK', owned.atk, 1200),
              const SizedBox(height: 6),
              _statRow('🛡️ DEF', owned.def, 800),
              const SizedBox(height: 6),
              _statRow('💨 SPD', owned.spd, 100),
              const SizedBox(height: 16),
              // Skills
              const Text('Fähigkeiten', style: TextStyle(color: kTextSecondary, fontSize: 13)),
              const SizedBox(height: 8),
              _skillCard(
                '⚡ ${char.normalSkill.name}',
                char.normalSkill.description,
                'Cooldown: ${char.normalSkill.cooldown} Runden',
                kAccentBlue,
              ),
              const SizedBox(height: 8),
              _skillCard(
                '🌟 ${char.ultimateSkill.name}',
                char.ultimateSkill.description,
                'Ultimate – 100 Gauge benötigt',
                kAccentGold,
              ),
              const SizedBox(height: 16),
              // Lore
              const Text('Hintergrundgeschichte', style: TextStyle(color: kTextSecondary, fontSize: 13)),
              const SizedBox(height: 8),
              Text(
                char.lore,
                style: const TextStyle(color: kTextPrimary, fontSize: 14, height: 1.6),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _statRow(String label, int value, int max) {
    return Row(
      children: [
        SizedBox(
          width: 70,
          child: Text(label, style: const TextStyle(color: kTextSecondary, fontSize: 13)),
        ),
        Expanded(
          child: LinearProgressIndicator(
            value: (value / max).clamp(0.0, 1.0),
            backgroundColor: Colors.white12,
            valueColor: AlwaysStoppedAnimation<Color>(
              label.contains('HP') ? kHpHigh : label.contains('ATK') ? kFireColor : label.contains('DEF') ? kAccentBlue : kWindColor,
            ),
            minHeight: 8,
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 50,
          child: Text('$value', style: const TextStyle(color: kTextPrimary, fontWeight: FontWeight.bold, fontSize: 13)),
        ),
      ],
    );
  }

  Widget _skillCard(String name, String description, String meta, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(name, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 14)),
          const SizedBox(height: 4),
          Text(description, style: const TextStyle(color: kTextPrimary, fontSize: 13)),
          const SizedBox(height: 4),
          Text(meta, style: TextStyle(color: color.withOpacity(0.7), fontSize: 11)),
        ],
      ),
    );
  }
}
