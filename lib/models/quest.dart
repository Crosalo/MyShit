import 'battle_state.dart';

class StageEnemy {
  final String enemyId;
  final int count;
  const StageEnemy({required this.enemyId, required this.count});
}

class Stage {
  final String id;
  final String name;
  final String description;
  final List<StageEnemy> enemies;
  final int gemReward;
  final int goldReward;
  final int expReward;
  final int recommendedPower;

  const Stage({
    required this.id,
    required this.name,
    required this.description,
    required this.enemies,
    required this.gemReward,
    required this.goldReward,
    required this.expReward,
    required this.recommendedPower,
  });
}

class Chapter {
  final int id;
  final String title;
  final String description;
  final String storyText;
  final List<Stage> stages;

  const Chapter({
    required this.id,
    required this.title,
    required this.description,
    required this.storyText,
    required this.stages,
  });
}
