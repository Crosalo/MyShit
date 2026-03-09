import 'package:flutter/material.dart';
import '../models/character.dart';
import '../theme.dart';

class CharacterCard extends StatelessWidget {
  final OwnedCharacter owned;
  final bool isCompact;
  final VoidCallback? onTap;

  const CharacterCard({
    super.key,
    required this.owned,
    this.isCompact = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final char = owned.character;
    final rarity = char.rarityLabel;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          gradient: rarityGradient(rarity),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: rarityColor(rarity).withOpacity(0.3),
              blurRadius: 12,
              spreadRadius: 1,
            ),
          ],
        ),
        child: isCompact ? _buildCompact(char, rarity) : _buildFull(char, rarity),
      ),
    );
  }

  Widget _buildCompact(Character char, String rarity) {
    return Stack(
      children: [
        Center(
          child: Text(char.emoji, style: const TextStyle(fontSize: 48)),
        ),
        Positioned(
          top: 4,
          right: 4,
          child: _rarityBadge(rarity),
        ),
        Positioned(
          bottom: 4,
          left: 0,
          right: 0,
          child: Center(
            child: Text(
              char.name,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 12,
                shadows: [Shadow(color: Colors.black, blurRadius: 4)],
              ),
            ),
          ),
        ),
        if (owned.copies > 1)
          Positioned(
            top: 4,
            left: 4,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '×${owned.copies}',
                style: const TextStyle(color: Colors.white, fontSize: 10),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildFull(Character char, String rarity) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(char.emoji, style: const TextStyle(fontSize: 36)),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _rarityBadge(rarity),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            char.name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                        ),
                      ],
                    ),
                    Text(
                      char.title,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.7),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _statChip('Lv', '${owned.level}', Colors.white70),
              _statChip('ATK', '${owned.atk}', const Color(0xFFFF7043)),
              _statChip('DEF', '${owned.def}', const Color(0xFF42A5F5)),
              _statChip('HP', '${owned.maxHp}', const Color(0xFF66BB6A)),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Text(char.elementLabel, style: const TextStyle(fontSize: 11, color: Colors.white70)),
              const SizedBox(width: 8),
              Text(char.classLabel, style: const TextStyle(fontSize: 11, color: Colors.white70)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _rarityBadge(String rarity) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: rarityColor(rarity).withOpacity(0.3),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: rarityColor(rarity), width: 1),
      ),
      child: Text(
        rarity,
        style: TextStyle(
          color: rarityColor(rarity),
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _statChip(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: TextStyle(color: color.withOpacity(0.7), fontSize: 10)),
        Text(value, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13)),
      ],
    );
  }
}

class PullResultCard extends StatelessWidget {
  final Character char;
  final bool isNew;

  const PullResultCard({super.key, required this.char, this.isNew = false});

  @override
  Widget build(BuildContext context) {
    final rarity = char.rarityLabel;
    return Container(
      width: 90,
      decoration: BoxDecoration(
        gradient: rarityGradient(rarity),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: rarityColor(rarity).withOpacity(0.5),
            blurRadius: 15,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Stack(
        children: [
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(char.emoji, style: const TextStyle(fontSize: 36)),
              const SizedBox(height: 4),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(
                  char.name,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                    shadows: [Shadow(color: Colors.black, blurRadius: 4)],
                  ),
                ),
              ),
              const SizedBox(height: 2),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: BoxDecoration(
                  color: rarityColor(rarity).withOpacity(0.3),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  rarity,
                  style: TextStyle(
                    color: rarityColor(rarity),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          if (isNew)
            Positioned(
              top: 4,
              left: 4,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.red.shade700,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text('NEU!',
                    style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold)),
              ),
            ),
        ],
      ),
    );
  }
}
