import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/character.dart';
import '../models/player_data.dart';
import '../models/battle_state.dart';
import '../models/quest.dart';
import '../data/characters_data.dart';
import '../data/story_data.dart';

class GameProvider extends ChangeNotifier {
  PlayerData _player = PlayerData();
  final Random _random = Random();

  PlayerData get player => _player;

  List<OwnedCharacter> get ownedCharacters {
    return _player.ownedCharacterIds.map((id) {
      final char = findCharacterById(id);
      if (char == null) return null;
      final owned = OwnedCharacter(character: char);
      owned.level = _player.characterLevels[id] ?? 1;
      owned.experience = _player.characterExp[id] ?? 0;
      owned.copies = _player.characterCopies[id] ?? 1;
      return owned;
    }).whereType<OwnedCharacter>().toList();
  }

  List<OwnedCharacter> get teamCharacters {
    // Return top 3 characters by ATK for battle
    final owned = ownedCharacters;
    owned.sort((a, b) => b.atk.compareTo(a.atk));
    return owned.take(3).toList();
  }

  int get totalPower {
    return teamCharacters.fold(0, (sum, c) => sum + c.atk + c.def + (c.maxHp ~/ 10));
  }

  // ─── Save/Load ───

  Future<void> loadGame() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonStr = prefs.getString('player_data');
    if (jsonStr != null) {
      try {
        final json = jsonDecode(jsonStr);
        _player = PlayerData.fromJson(json);
      } catch (_) {
        _player = PlayerData();
      }
    }
    notifyListeners();
  }

  Future<void> saveGame() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('player_data', jsonEncode(_player.toJson()));
  }

  // ─── Daily Login ───

  Map<String, dynamic>? claimDailyLogin() {
    if (!_player.canClaimDailyLogin) return null;

    final now = DateTime.now();
    final last = _player.lastDailyLogin;
    if (last != null) {
      final diff = now.difference(last).inDays;
      if (diff <= 1) {
        _player.consecutiveDays++;
      } else {
        _player.consecutiveDays = 1;
      }
    } else {
      _player.consecutiveDays = 1;
    }
    _player.lastDailyLogin = now;

    final gemReward = 30 + (_player.consecutiveDays * 5).clamp(0, 50);
    final goldReward = 500 + (_player.consecutiveDays * 100).clamp(0, 1000);
    _player.gems += gemReward;
    _player.gold += goldReward;

    saveGame();
    notifyListeners();
    return {'gems': gemReward, 'gold': goldReward, 'day': _player.consecutiveDays};
  }

  // ─── Gacha ───

  static const double _ssrRate = 0.03;
  static const double _srRate = 0.15;
  static const int _ssrPityAt = 90;
  static const int _srPityAt = 10;
  static const int _singlePullCost = 10;
  static const int _tenPullCost = 100;

  bool get canSinglePull => _player.gems >= _singlePullCost;
  bool get canTenPull => _player.gems >= _tenPullCost;

  List<Character> performPull(int count) {
    if (count == 1 && !canSinglePull) return [];
    if (count == 10 && !canTenPull) return [];

    final cost = count == 10 ? _tenPullCost : _singlePullCost;
    _player.gems -= cost;
    _player.totalPulls += count;

    final results = <Character>[];
    for (int i = 0; i < count; i++) {
      results.add(_pullSingle());
    }

    // Give pity SR on 10-pull if no SR/SSR
    if (count == 10) {
      final hasSrOrBetter = results.any((c) => c.rarity != Rarity.r);
      if (!hasSrOrBetter) {
        results[9] = _pickRandom(srPool);
      }
    }

    for (final char in results) {
      _addCharacter(char.id);
    }

    saveGame();
    notifyListeners();
    return results;
  }

  Character _pullSingle() {
    _player.pityCounter++;
    _player.srPityCounter++;

    // Hard pity SSR at 90
    if (_player.pityCounter >= _ssrPityAt) {
      _player.pityCounter = 0;
      _player.srPityCounter = 0;
      return _pickRandom(ssrPool);
    }

    // Guaranteed SR at 10
    if (_player.srPityCounter >= _srPityAt) {
      _player.srPityCounter = 0;
      final roll = _random.nextDouble();
      if (roll < _ssrRate) {
        _player.pityCounter = 0;
        return _pickRandom(ssrPool);
      }
      return _pickRandom(srPool);
    }

    final roll = _random.nextDouble();
    if (roll < _ssrRate) {
      _player.pityCounter = 0;
      _player.srPityCounter = 0;
      return _pickRandom(ssrPool);
    } else if (roll < _ssrRate + _srRate) {
      _player.srPityCounter = 0;
      return _pickRandom(srPool);
    } else {
      return _pickRandom(rPool);
    }
  }

  Character _pickRandom(List<Character> pool) {
    return pool[_random.nextInt(pool.length)];
  }

  void _addCharacter(String id) {
    if (_player.ownedCharacterIds.contains(id)) {
      _player.characterCopies[id] = (_player.characterCopies[id] ?? 1) + 1;
    } else {
      _player.ownedCharacterIds.add(id);
      _player.characterLevels[id] = 1;
      _player.characterExp[id] = 0;
      _player.characterCopies[id] = 1;
    }
  }

  // ─── Story ───

  List<Chapter> get chapters => storyChapters;

  int get currentChapterIndex => _player.storyProgress ~/ 3;
  int get currentStageInChapter => _player.storyProgress % 3;

  bool isStageCompleted(String stageId) => _player.completedMissions.contains(stageId);

  bool isStageUnlocked(int chapterIndex, int stageIndex) {
    if (chapterIndex == 0 && stageIndex == 0) return true;
    final prevStageId = chapterIndex == 0 && stageIndex > 0
        ? '${chapterIndex + 1}-${stageIndex}'
        : null;
    if (prevStageId != null) {
      return isStageCompleted(prevStageId);
    }
    // Stage is unlocked if previous stage in same chapter is done
    if (stageIndex > 0) {
      final prev = '${chapterIndex + 1}-$stageIndex';
      return isStageCompleted(prev);
    }
    // First stage of chapter: previous chapter's last stage must be done
    if (chapterIndex > 0) {
      final prevChapter = storyChapters[chapterIndex - 1];
      final lastStage = prevChapter.stages.last;
      return isStageCompleted(lastStage.id);
    }
    return false;
  }

  // ─── Battle ───

  BattleState? createBattle(Stage stage) {
    final team = teamCharacters;
    if (team.isEmpty) return null;

    final enemies = <Enemy>[];
    for (final stageEnemy in stage.enemies) {
      for (int i = 0; i < stageEnemy.count; i++) {
        enemies.add(createEnemy(stageEnemy.enemyId));
      }
    }

    return BattleState(
      playerTeam: team.map((c) => BattleCharacter(ownedChar: c)).toList(),
      enemies: enemies,
    );
  }

  void completeBattle(Stage stage, bool victory) {
    if (!victory) return;

    _player.completedMissions.add(stage.id);
    _player.gems += stage.gemReward;
    _player.gold += stage.goldReward;

    // Give exp to all team members
    for (final owned in teamCharacters) {
      _player.characterExp[owned.character.id] =
          (_player.characterExp[owned.character.id] ?? 0) + stage.expReward;

      // Level up if enough exp
      int level = _player.characterLevels[owned.character.id] ?? 1;
      int exp = _player.characterExp[owned.character.id] ?? 0;
      while (exp >= level * 100 && level < 100) {
        exp -= level * 100;
        level++;
      }
      _player.characterLevels[owned.character.id] = level;
      _player.characterExp[owned.character.id] = exp;
    }

    // Update story progress
    final stageNum = int.tryParse(stage.id.split('-').last) ?? 1;
    final chapterNum = int.tryParse(stage.id.split('-').first) ?? 1;
    final progress = (chapterNum - 1) * 3 + stageNum;
    if (progress > _player.storyProgress) {
      _player.storyProgress = progress;
    }

    saveGame();
    notifyListeners();
  }

  // ─── Shop ───

  bool buyGems(int gemAmount, int cost) {
    // Simulated gem purchase (no real IAP in this demo)
    _player.gems += gemAmount;
    saveGame();
    notifyListeners();
    return true;
  }

  // ─── Dev helper (remove in production) ───
  void addGemsDebug(int amount) {
    _player.gems += amount;
    saveGame();
    notifyListeners();
  }
}
