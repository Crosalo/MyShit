import 'character.dart';

enum BattlePhase { playerTurn, enemyTurn, victory, defeat }

class Enemy {
  final String id;
  final String name;
  final String emoji;
  final int maxHp;
  final int atk;
  final int def;
  final int spd;
  final int expReward;
  final int goldReward;
  int currentHp;

  Enemy({
    required this.id,
    required this.name,
    required this.emoji,
    required this.maxHp,
    required this.atk,
    required this.def,
    required this.spd,
    required this.expReward,
    required this.goldReward,
  }) : currentHp = maxHp;

  bool get isAlive => currentHp > 0;

  int takeDamage(int damage) {
    final reduced = (damage * (100 / (100 + def))).round();
    final actual = reduced < 1 ? 1 : reduced;
    currentHp = (currentHp - actual).clamp(0, maxHp);
    return actual;
  }

  int attackTarget(int targetDef) {
    final reduced = (atk * (100 / (100 + targetDef))).round();
    return reduced < 1 ? 1 : reduced;
  }
}

class BattleCharacter {
  final OwnedCharacter ownedChar;
  int currentHp;
  int ultimateGauge; // 0-100
  int skillCooldown;
  bool isAlive;

  BattleCharacter({required this.ownedChar})
      : currentHp = ownedChar.maxHp,
        ultimateGauge = 0,
        skillCooldown = 0,
        isAlive = true;

  Character get character => ownedChar.character;

  int takeDamage(int damage) {
    final reduced = (damage * (100 / (100 + ownedChar.def))).round();
    final actual = reduced < 1 ? 1 : reduced;
    currentHp = (currentHp - actual).clamp(0, ownedChar.maxHp);
    if (currentHp <= 0) isAlive = false;
    // Fill ultimate gauge when taking damage
    ultimateGauge = (ultimateGauge + 15).clamp(0, 100);
    return actual;
  }

  int normalAttack(Enemy enemy) {
    final dmg = (ownedChar.atk * 1.0).round();
    final dealt = enemy.takeDamage(dmg);
    ultimateGauge = (ultimateGauge + 10).clamp(0, 100);
    return dealt;
  }

  int useSkill(Enemy enemy) {
    if (skillCooldown > 0) return 0;
    final skill = character.normalSkill;
    final dmg = (ownedChar.atk * skill.damage / 100).round();
    int dealt = 0;
    if (skill.isHeal) {
      final heal = dmg;
      currentHp = (currentHp + heal).clamp(0, ownedChar.maxHp);
      dealt = heal;
    } else {
      dealt = enemy.takeDamage(dmg);
    }
    skillCooldown = skill.cooldown;
    ultimateGauge = (ultimateGauge + 20).clamp(0, 100);
    return dealt;
  }

  int useUltimate(Enemy enemy) {
    if (ultimateGauge < 100) return 0;
    final skill = character.ultimateSkill;
    final dmg = (ownedChar.atk * skill.damage / 100).round();
    int dealt = 0;
    if (skill.isHeal) {
      final heal = dmg;
      currentHp = (currentHp + heal).clamp(0, ownedChar.maxHp);
      dealt = heal;
    } else {
      dealt = enemy.takeDamage(dmg);
    }
    ultimateGauge = 0;
    return dealt;
  }

  void tickCooldowns() {
    if (skillCooldown > 0) skillCooldown--;
  }
}

class BattleLog {
  final String message;
  final bool isPlayerAction;
  final bool isDamage;
  final bool isHeal;

  BattleLog({
    required this.message,
    this.isPlayerAction = true,
    this.isDamage = true,
    this.isHeal = false,
  });
}

class BattleState {
  final List<BattleCharacter> playerTeam;
  final List<Enemy> enemies;
  BattlePhase phase;
  int currentPlayerIndex;
  int currentEnemyIndex;
  final List<BattleLog> logs;
  int expGained;
  int goldGained;

  BattleState({
    required this.playerTeam,
    required this.enemies,
  })  : phase = BattlePhase.playerTurn,
        currentPlayerIndex = 0,
        currentEnemyIndex = 0,
        logs = [],
        expGained = 0,
        goldGained = 0;

  BattleCharacter? get activePlayer {
    final alive = playerTeam.where((c) => c.isAlive).toList();
    if (alive.isEmpty) return null;
    return alive[currentPlayerIndex % alive.length];
  }

  Enemy? get activeEnemy {
    final alive = enemies.where((e) => e.isAlive).toList();
    if (alive.isEmpty) return null;
    return alive[currentEnemyIndex % alive.length];
  }

  bool get allEnemiesDead => enemies.every((e) => !e.isAlive);
  bool get allPlayersDead => playerTeam.every((c) => !c.isAlive);

  void addLog(String msg, {bool isPlayer = true, bool isDmg = true, bool isHeal = false}) {
    logs.add(BattleLog(message: msg, isPlayerAction: isPlayer, isDamage: isDmg, isHeal: isHeal));
    if (logs.length > 20) logs.removeAt(0);
  }

  void nextPlayerTurn() {
    final alive = playerTeam.where((c) => c.isAlive).toList();
    if (alive.isEmpty) return;
    currentPlayerIndex = (currentPlayerIndex + 1) % alive.length;
    for (final c in alive) {
      c.tickCooldowns();
    }
  }
}
