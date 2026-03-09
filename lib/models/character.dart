enum Rarity { r, sr, ssr }

enum Element { fire, water, wind, earth, light, dark }

enum CharacterClass { warrior, mage, rogue, healer, beast }

class Skill {
  final String name;
  final String description;
  final int damage; // multiplier in %
  final int cooldown;
  final bool isHeal;

  const Skill({
    required this.name,
    required this.description,
    required this.damage,
    this.cooldown = 3,
    this.isHeal = false,
  });
}

class CharacterStats {
  final int hp;
  final int atk;
  final int def;
  final int spd;

  const CharacterStats({
    required this.hp,
    required this.atk,
    required this.def,
    required this.spd,
  });
}

class Character {
  final String id;
  final String name;
  final String title;
  final String lore;
  final Rarity rarity;
  final Element element;
  final CharacterClass characterClass;
  final CharacterStats stats;
  final Skill normalSkill;
  final Skill ultimateSkill;
  final String emoji; // Visual representation

  const Character({
    required this.id,
    required this.name,
    required this.title,
    required this.lore,
    required this.rarity,
    required this.element,
    required this.characterClass,
    required this.stats,
    required this.normalSkill,
    required this.ultimateSkill,
    required this.emoji,
  });

  String get rarityLabel {
    switch (rarity) {
      case Rarity.ssr:
        return 'SSR';
      case Rarity.sr:
        return 'SR';
      case Rarity.r:
        return 'R';
    }
  }

  String get elementLabel {
    switch (element) {
      case Element.fire:
        return '🔥 Feuer';
      case Element.water:
        return '💧 Wasser';
      case Element.wind:
        return '🌪️ Wind';
      case Element.earth:
        return '🌍 Erde';
      case Element.light:
        return '✨ Licht';
      case Element.dark:
        return '🌑 Dunkel';
    }
  }

  String get classLabel {
    switch (characterClass) {
      case CharacterClass.warrior:
        return '⚔️ Krieger';
      case CharacterClass.mage:
        return '🔮 Magier';
      case CharacterClass.rogue:
        return '🗡️ Assassine';
      case CharacterClass.healer:
        return '💚 Heiler';
      case CharacterClass.beast:
        return '🐺 Bestie';
    }
  }
}

class OwnedCharacter {
  final Character character;
  int level;
  int experience;
  int copies; // Dupes for enhancement

  OwnedCharacter({
    required this.character,
    this.level = 1,
    this.experience = 0,
    this.copies = 1,
  });

  int get maxHp => (character.stats.hp * (1 + (level - 1) * 0.05)).round();
  int get atk => (character.stats.atk * (1 + (level - 1) * 0.05)).round();
  int get def => (character.stats.def * (1 + (level - 1) * 0.05)).round();
  int get spd => character.stats.spd;

  int get expNeeded => level * 100;

  void addExperience(int exp) {
    experience += exp;
    while (experience >= expNeeded && level < 100) {
      experience -= expNeeded;
      level++;
    }
  }

  Map<String, dynamic> toJson() => {
        'id': character.id,
        'level': level,
        'experience': experience,
        'copies': copies,
      };
}
