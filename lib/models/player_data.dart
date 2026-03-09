class PlayerData {
  String playerName;
  int gems;
  int gold;
  int pityCounter; // Guaranteed SSR at 90
  int srPityCounter; // Guaranteed SR at 10
  List<String> ownedCharacterIds;
  Map<String, int> characterLevels;
  Map<String, int> characterCopies;
  Map<String, int> characterExp;
  int storyProgress; // Current chapter index
  Set<String> completedMissions;
  int totalPulls;
  DateTime? lastDailyLogin;
  int consecutiveDays;

  PlayerData({
    this.playerName = 'Held',
    this.gems = 300,
    this.gold = 5000,
    this.pityCounter = 0,
    this.srPityCounter = 0,
    List<String>? ownedCharacterIds,
    Map<String, int>? characterLevels,
    Map<String, int>? characterCopies,
    Map<String, int>? characterExp,
    this.storyProgress = 0,
    Set<String>? completedMissions,
    this.totalPulls = 0,
    this.lastDailyLogin,
    this.consecutiveDays = 0,
  })  : ownedCharacterIds = ownedCharacterIds ?? [],
        characterLevels = characterLevels ?? {},
        characterCopies = characterCopies ?? {},
        characterExp = characterExp ?? {},
        completedMissions = completedMissions ?? {};

  bool get canClaimDailyLogin {
    if (lastDailyLogin == null) return true;
    final now = DateTime.now();
    final last = lastDailyLogin!;
    return now.year != last.year || now.month != last.month || now.day != last.day;
  }

  Map<String, dynamic> toJson() => {
        'playerName': playerName,
        'gems': gems,
        'gold': gold,
        'pityCounter': pityCounter,
        'srPityCounter': srPityCounter,
        'ownedCharacterIds': ownedCharacterIds,
        'characterLevels': characterLevels,
        'characterCopies': characterCopies,
        'characterExp': characterExp,
        'storyProgress': storyProgress,
        'completedMissions': completedMissions.toList(),
        'totalPulls': totalPulls,
        'lastDailyLogin': lastDailyLogin?.toIso8601String(),
        'consecutiveDays': consecutiveDays,
      };

  factory PlayerData.fromJson(Map<String, dynamic> json) {
    return PlayerData(
      playerName: json['playerName'] ?? 'Held',
      gems: json['gems'] ?? 300,
      gold: json['gold'] ?? 5000,
      pityCounter: json['pityCounter'] ?? 0,
      srPityCounter: json['srPityCounter'] ?? 0,
      ownedCharacterIds: List<String>.from(json['ownedCharacterIds'] ?? []),
      characterLevels: Map<String, int>.from(json['characterLevels'] ?? {}),
      characterCopies: Map<String, int>.from(json['characterCopies'] ?? {}),
      characterExp: Map<String, int>.from(json['characterExp'] ?? {}),
      storyProgress: json['storyProgress'] ?? 0,
      completedMissions: Set<String>.from(json['completedMissions'] ?? []),
      totalPulls: json['totalPulls'] ?? 0,
      lastDailyLogin: json['lastDailyLogin'] != null
          ? DateTime.parse(json['lastDailyLogin'])
          : null,
      consecutiveDays: json['consecutiveDays'] ?? 0,
    );
  }
}
