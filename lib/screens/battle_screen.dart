import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/battle_state.dart';
import '../models/quest.dart';
import '../providers/game_provider.dart';
import '../widgets/stat_bar.dart';
import '../theme.dart';

class BattleScreen extends StatefulWidget {
  final BattleState battleState;
  final Stage stage;

  const BattleScreen({
    super.key,
    required this.battleState,
    required this.stage,
  });

  @override
  State<BattleScreen> createState() => _BattleScreenState();
}

class _BattleScreenState extends State<BattleScreen> with SingleTickerProviderStateMixin {
  late BattleState _battle;
  late AnimationController _shakeController;
  bool _enemyShaking = false;
  bool _playerShaking = false;

  @override
  void initState() {
    super.initState();
    _battle = widget.battleState;
    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
  }

  @override
  void dispose() {
    _shakeController.dispose();
    super.dispose();
  }

  Future<void> _shake(bool isEnemy) async {
    setState(() {
      if (isEnemy) _enemyShaking = true;
      else _playerShaking = true;
    });
    await Future.delayed(const Duration(milliseconds: 300));
    if (mounted) {
      setState(() {
        _enemyShaking = false;
        _playerShaking = false;
      });
    }
  }

  void _playerAttack() {
    if (_battle.phase != BattlePhase.playerTurn) return;
    final player = _battle.activePlayer;
    final enemy = _battle.activeEnemy;
    if (player == null || enemy == null) return;

    final dmg = player.normalAttack(enemy);
    _battle.addLog('${player.character.name} greift an! ${enemy.name} -$dmg HP');

    _shake(true);
    _checkBattleEnd();
    if (_battle.phase == BattlePhase.playerTurn) {
      _battle.nextPlayerTurn();
      setState(() {});
      _scheduleEnemyTurn();
    }
  }

  void _playerSkill() {
    if (_battle.phase != BattlePhase.playerTurn) return;
    final player = _battle.activePlayer;
    final enemy = _battle.activeEnemy;
    if (player == null || enemy == null) return;
    if (player.skillCooldown > 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${player.character.normalSkill.name} noch ${player.skillCooldown} Runden cooldown!'),
          duration: const Duration(seconds: 1),
        ),
      );
      return;
    }

    final result = player.useSkill(enemy);
    final skill = player.character.normalSkill;
    if (skill.isHeal) {
      _battle.addLog('${player.character.name} setzt ${skill.name} ein! +$result HP', isHeal: true);
    } else {
      _battle.addLog('${player.character.name} setzt ${skill.name} ein! ${enemy.name} -$result HP');
    }

    _shake(true);
    _checkBattleEnd();
    if (_battle.phase == BattlePhase.playerTurn) {
      _battle.nextPlayerTurn();
      setState(() {});
      _scheduleEnemyTurn();
    }
  }

  void _playerUltimate() {
    if (_battle.phase != BattlePhase.playerTurn) return;
    final player = _battle.activePlayer;
    final enemy = _battle.activeEnemy;
    if (player == null || enemy == null) return;
    if (player.ultimateGauge < 100) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Ultimate nicht bereit! Gauge muss voll sein.'),
          duration: Duration(seconds: 1),
        ),
      );
      return;
    }

    final result = player.useUltimate(enemy);
    final skill = player.character.ultimateSkill;
    _battle.addLog('🌟 ${player.character.name}: ${skill.name}! ${enemy.name} -$result HP', isDmg: true);

    _shake(true);
    _checkBattleEnd();
    if (_battle.phase == BattlePhase.playerTurn) {
      _battle.nextPlayerTurn();
      setState(() {});
      _scheduleEnemyTurn();
    }
  }

  void _scheduleEnemyTurn() {
    if (_battle.allEnemiesDead) return;
    Future.delayed(const Duration(milliseconds: 800), () {
      if (!mounted) return;
      _doEnemyTurn();
    });
  }

  void _doEnemyTurn() {
    if (_battle.phase != BattlePhase.playerTurn) return;
    final enemy = _battle.activeEnemy;
    if (enemy == null || !enemy.isAlive) return;

    // Pick a random alive player
    final alivePlayers = _battle.playerTeam.where((c) => c.isAlive).toList();
    if (alivePlayers.isEmpty) return;

    final target = alivePlayers[0]; // Simple AI: target first alive player
    final dmg = target.takeDamage(enemy.atk);
    _battle.addLog('${enemy.name} greift ${target.character.name} an! -$dmg HP', isPlayer: false);

    _shake(false);
    _checkBattleEnd();
    setState(() {});
  }

  void _checkBattleEnd() {
    if (_battle.allEnemiesDead) {
      final expTotal = _battle.enemies.fold(0, (sum, e) => sum + e.expReward);
      final goldTotal = _battle.enemies.fold(0, (sum, e) => sum + e.goldReward);
      _battle.expGained = expTotal;
      _battle.goldGained = goldTotal;
      _battle.phase = BattlePhase.victory;
      context.read<GameProvider>().completeBattle(widget.stage, true);
      setState(() {});
    } else if (_battle.allPlayersDead) {
      _battle.phase = BattlePhase.defeat;
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBgDark,
      body: SafeArea(
        child: Column(
          children: [
            _buildTopBar(),
            Expanded(
              child: _battle.phase == BattlePhase.victory
                  ? _buildVictoryScreen()
                  : _battle.phase == BattlePhase.defeat
                      ? _buildDefeatScreen()
                      : _buildBattleField(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: kBgMid,
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back, color: kTextPrimary),
            onPressed: () => Navigator.pop(context),
          ),
          Expanded(
            child: Text(
              widget.stage.name,
              style: const TextStyle(color: kAccentGold, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBattleField() {
    return Column(
      children: [
        // Enemy area
        Expanded(
          flex: 3,
          child: _buildEnemyArea(),
        ),
        // Battle log
        _buildBattleLog(),
        // Player team
        _buildPlayerTeam(),
        // Action buttons
        _buildActionButtons(),
        const SizedBox(height: 8),
      ],
    );
  }

  Widget _buildEnemyArea() {
    final enemy = _battle.activeEnemy;
    if (enemy == null) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1A0020), Color(0xFF0A0010)],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.red.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            transform: _enemyShaking
                ? (Matrix4.identity()..translate(8.0, 0.0))
                : Matrix4.identity(),
            child: Text(
              enemy.emoji,
              style: const TextStyle(fontSize: 72),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            enemy.name,
            style: GoogleFonts.cinzelDecorative(
              color: Colors.red.shade300,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          StatBar(
            current: enemy.currentHp,
            max: enemy.maxHp,
            height: 12,
            showText: true,
            label: 'HP',
          ),
        ],
      ),
    );
  }

  Widget _buildBattleLog() {
    final logs = _battle.logs.reversed.take(3).toList();
    return Container(
      height: 72,
      margin: const EdgeInsets.symmetric(horizontal: 12),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black45,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        children: logs
            .map(
              (log) => Text(
                log.message,
                style: TextStyle(
                  color: log.isHeal
                      ? kHpHigh
                      : log.isPlayerAction
                          ? kTextPrimary
                          : Colors.red.shade300,
                  fontSize: 11,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _buildPlayerTeam() {
    return Container(
      height: 120,
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      child: Row(
        children: _battle.playerTeam.map((char) {
          final isActive = _battle.activePlayer == char;
          return Expanded(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.symmetric(horizontal: 4),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: char.isAlive ? kCardBg : Colors.grey.shade900,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isActive && char.isAlive ? kAccentGold : Colors.white12,
                  width: isActive ? 2 : 1,
                ),
                boxShadow: isActive && char.isAlive
                    ? [BoxShadow(color: kAccentGold.withOpacity(0.3), blurRadius: 8)]
                    : null,
              ),
              child: Column(
                children: [
                  Text(
                    char.character.emoji,
                    style: TextStyle(fontSize: 28, color: char.isAlive ? null : Colors.grey),
                  ),
                  Text(
                    char.character.name,
                    style: TextStyle(
                      color: char.isAlive ? kTextPrimary : Colors.grey,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  StatBar(current: char.currentHp, max: char.ownedChar.maxHp, height: 5),
                  const SizedBox(height: 2),
                  UltGaugeBar(gauge: char.ultimateGauge, height: 4),
                  Text(
                    char.isAlive ? '💎 ${char.ultimateGauge}%' : '💀',
                    style: const TextStyle(fontSize: 9, color: kTextSecondary),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildActionButtons() {
    final player = _battle.activePlayer;
    if (player == null) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        children: [
          Expanded(
            child: _actionBtn(
              '⚔️ Angriff',
              kAccentBlue,
              _playerAttack,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _actionBtn(
              '⚡ ${player.character.normalSkill.name}\n(CD: ${player.skillCooldown})',
              player.skillCooldown == 0 ? kAccentPurple : Colors.grey,
              player.skillCooldown == 0 ? _playerSkill : null,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _actionBtn(
              '🌟 Ultimate\n(${player.ultimateGauge}%)',
              player.ultimateGauge >= 100 ? kAccentGold : Colors.grey,
              player.ultimateGauge >= 100 ? _playerUltimate : null,
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionBtn(String label, Color color, VoidCallback? onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 60,
        decoration: BoxDecoration(
          color: color.withOpacity(onTap != null ? 0.2 : 0.05),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: onTap != null ? color.withOpacity(0.6) : Colors.white12),
        ),
        child: Center(
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: onTap != null ? color : Colors.grey,
              fontWeight: FontWeight.bold,
              fontSize: 11,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildVictoryScreen() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('🏆', style: TextStyle(fontSize: 80)),
            const SizedBox(height: 16),
            Text(
              'SIEG!',
              style: GoogleFonts.cinzelDecorative(
                color: kAccentGold,
                fontSize: 36,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: kCardBg,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: kAccentGold.withOpacity(0.3)),
              ),
              child: Column(
                children: [
                  const Text('Belohnungen erhalten:',
                      style: TextStyle(color: kTextSecondary, fontSize: 13)),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _victoryReward('💎', '+${widget.stage.gemReward}', kAccentPurple),
                      _victoryReward('🪙', '+${widget.stage.goldReward}', kAccentGold),
                      _victoryReward('⭐', 'EXP', kAccentBlue),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: kAccentGold,
                foregroundColor: kBgDark,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
              ),
              child: Text('Weiter', style: GoogleFonts.cinzelDecorative(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDefeatScreen() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('💀', style: TextStyle(fontSize: 80)),
            const SizedBox(height: 16),
            Text(
              'NIEDERLAGE',
              style: GoogleFonts.cinzelDecorative(
                color: Colors.red.shade400,
                fontSize: 32,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Trainiere deine Helden und versuche es erneut!',
              textAlign: TextAlign.center,
              style: TextStyle(color: kTextSecondary),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red.shade800,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
              ),
              child: const Text('Zurück'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _victoryReward(String emoji, String value, Color color) {
    return Column(
      children: [
        Text(emoji, style: const TextStyle(fontSize: 28)),
        const SizedBox(height: 4),
        Text(value, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
      ],
    );
  }
}
