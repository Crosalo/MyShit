import '../models/battle_state.dart';
import '../models/quest.dart';

// ─── Realm Chronicles – Story Data ───
// All enemies and chapters for the main story

final Map<String, Enemy Function()> enemyFactories = {
  'goblin': () => Enemy(
        id: 'goblin',
        name: 'Goblin-Räuber',
        emoji: '👺',
        maxHp: 800,
        atk: 120,
        def: 80,
        spd: 60,
        expReward: 50,
        goldReward: 30,
      ),
  'goblin_chief': () => Enemy(
        id: 'goblin_chief',
        name: 'Goblin-Anführer',
        emoji: '👹',
        maxHp: 2200,
        atk: 280,
        def: 160,
        spd: 55,
        expReward: 150,
        goldReward: 100,
      ),
  'bandit': () => Enemy(
        id: 'bandit',
        name: 'Räuber',
        emoji: '🗡️',
        maxHp: 1400,
        atk: 220,
        def: 140,
        spd: 70,
        expReward: 90,
        goldReward: 60,
      ),
  'bandit_boss': () => Enemy(
        id: 'bandit_boss',
        name: 'Räuber-Boss',
        emoji: '💀',
        maxHp: 4500,
        atk: 420,
        def: 250,
        spd: 65,
        expReward: 300,
        goldReward: 250,
      ),
  'forest_wolf': () => Enemy(
        id: 'forest_wolf',
        name: 'Waldwolf',
        emoji: '🐺',
        maxHp: 1800,
        atk: 300,
        def: 120,
        spd: 85,
        expReward: 110,
        goldReward: 70,
      ),
  'dark_knight': () => Enemy(
        id: 'dark_knight',
        name: 'Dunkelritter',
        emoji: '🖤',
        maxHp: 3500,
        atk: 480,
        def: 380,
        spd: 60,
        expReward: 220,
        goldReward: 180,
      ),
  'fire_elemental': () => Enemy(
        id: 'fire_elemental',
        name: 'Feuerelementar',
        emoji: '🌋',
        maxHp: 2800,
        atk: 550,
        def: 200,
        spd: 75,
        expReward: 200,
        goldReward: 160,
      ),
  'ice_golem': () => Enemy(
        id: 'ice_golem',
        name: 'Eisgolem',
        emoji: '🧊',
        maxHp: 6000,
        atk: 380,
        def: 600,
        spd: 40,
        expReward: 280,
        goldReward: 220,
      ),
  'shadow_demon': () => Enemy(
        id: 'shadow_demon',
        name: 'Schattendämon',
        emoji: '👾',
        maxHp: 4200,
        atk: 620,
        def: 300,
        spd: 90,
        expReward: 350,
        goldReward: 300,
      ),
  'corrupted_warrior': () => Enemy(
        id: 'corrupted_warrior',
        name: 'Verfluchter Krieger',
        emoji: '⚔️',
        maxHp: 7000,
        atk: 750,
        def: 450,
        spd: 80,
        expReward: 500,
        goldReward: 420,
      ),
  'ancient_dragon': () => Enemy(
        id: 'ancient_dragon',
        name: 'Ururdrache Ignaros',
        emoji: '🐉',
        maxHp: 15000,
        atk: 950,
        def: 600,
        spd: 70,
        expReward: 1000,
        goldReward: 800,
      ),
  'demon_lord': () => Enemy(
        id: 'demon_lord',
        name: 'Dämonenlord Moros',
        emoji: '😈',
        maxHp: 25000,
        atk: 1200,
        def: 750,
        spd: 85,
        expReward: 2000,
        goldReward: 1500,
      ),
};

Enemy createEnemy(String id) {
  final factory = enemyFactories[id];
  if (factory == null) throw Exception('Unknown enemy: $id');
  return factory();
}

// ─── Story Chapters ───

const List<Chapter> storyChapters = [
  Chapter(
    id: 1,
    title: 'Kapitel 1: Das Erwachen',
    description: 'Goblin-Räuber überfallen das Grenzdorf Ashenveil. Werde zum Helden!',
    storyText:
        'Das Königreich Veraldia – einst ein Reich des Friedens und der Magie.\n\n'
        'Doch im Grenzgebiet häufen sich Überfälle. Das Dorf Ashenveil steht in Flammen.\n\n'
        '"Bitte hilf uns!" fleht eine alte Frau. "Die Goblins kommen jede Nacht!"\n\n'
        'Als junger Krieger mit unbekannter Vergangenheit nimmst du das Schwert in die Hand.\n\n'
        'Deine Reise hat begonnen.',
    stages: [
      Stage(
        id: '1-1',
        name: '1-1: Erste Begegnung',
        description: 'Ein Goblin-Räuber lauert im Dunkeln.',
        enemies: [StageEnemy(enemyId: 'goblin', count: 1)],
        gemReward: 5,
        goldReward: 100,
        expReward: 50,
        recommendedPower: 200,
      ),
      Stage(
        id: '1-2',
        name: '1-2: Goblin-Lager',
        description: 'Zwei Goblins verteidigen ihr Lager.',
        enemies: [StageEnemy(enemyId: 'goblin', count: 2)],
        gemReward: 5,
        goldReward: 150,
        expReward: 80,
        recommendedPower: 350,
      ),
      Stage(
        id: '1-3',
        name: '1-3: Häuptling Grugg',
        description: 'Der Goblin-Häuptling stellt sich zum Kampf!',
        enemies: [StageEnemy(enemyId: 'goblin_chief', count: 1)],
        gemReward: 15,
        goldReward: 300,
        expReward: 150,
        recommendedPower: 500,
      ),
    ],
  ),

  Chapter(
    id: 2,
    title: 'Kapitel 2: Schatten auf den Straßen',
    description: 'Räuberbanden terrorisieren die Handelswege. Steckt jemand dahinter?',
    storyText:
        'Dein Sieg in Ashenveil hat sich herumgesprochen. Abenteurer und Händler sprechen deinen Namen.\n\n'
        'Doch Freude währt kurz. Alle Handelswege nach Norden sind gesperrt — '
        'Räuberbanden mit magisch verstärkten Waffen greifen jeden an, der passiert.\n\n'
        '"Diese Waffen..." murmelt Rexar, ein Söldner den du triffst. '
        '"Das ist keine normale Schmiedekunst. Jemand versorgt sie."\n\n'
        'Du folgst der Spur. Sie führt tief in den Schwarzwald.',
    stages: [
      Stage(
        id: '2-1',
        name: '2-1: Gesperrter Pfad',
        description: 'Räuber blockieren die Straße.',
        enemies: [StageEnemy(enemyId: 'bandit', count: 1)],
        gemReward: 8,
        goldReward: 200,
        expReward: 100,
        recommendedPower: 700,
      ),
      Stage(
        id: '2-2',
        name: '2-2: Wolfshöhle',
        description: 'Räuber und wilde Wölfe im Wald.',
        enemies: [
          StageEnemy(enemyId: 'bandit', count: 1),
          StageEnemy(enemyId: 'forest_wolf', count: 1),
        ],
        gemReward: 8,
        goldReward: 250,
        expReward: 130,
        recommendedPower: 900,
      ),
      Stage(
        id: '2-3',
        name: '2-3: Boss Scarface',
        description: 'Der Räuber-Boss mit narbenübersätem Gesicht!',
        enemies: [StageEnemy(enemyId: 'bandit_boss', count: 1)],
        gemReward: 20,
        goldReward: 500,
        expReward: 300,
        recommendedPower: 1200,
      ),
    ],
  ),

  Chapter(
    id: 3,
    title: 'Kapitel 3: Die Feuerhöhlen',
    description: 'Im Inneren des Vulkans verbergen sich Elementarwesen und Dunkelritter.',
    storyText:
        'Scarfaces letzter Atemzug verrät den Treffpunkt: "Die... Feuerhöhlen... des Nordens."\n\n'
        'Dort, im Bauch eines alten Vulkans, hat jemand ein Ritual begonnen. '
        'Feuerelementare und Dunkelritter bewachen den Weg.\n\n'
        '"Das Ritual beschwört etwas Uraltes," erklärt Aria, '
        'die Windmagierin die sich deiner Gruppe angeschlossen hat.\n\n'
        '"Wenn es vollendet wird... kein Zauber der Welt kann es stoppen."',
    stages: [
      Stage(
        id: '3-1',
        name: '3-1: Vulkantor',
        description: 'Feuerelementare versperren den Vulkan-Eingang.',
        enemies: [StageEnemy(enemyId: 'fire_elemental', count: 1)],
        gemReward: 10,
        goldReward: 350,
        expReward: 200,
        recommendedPower: 1500,
      ),
      Stage(
        id: '3-2',
        name: '3-2: Kältekammer',
        description: 'Ein Eisgolem bewacht die Tiefkammer.',
        enemies: [StageEnemy(enemyId: 'ice_golem', count: 1)],
        gemReward: 10,
        goldReward: 400,
        expReward: 250,
        recommendedPower: 1800,
      ),
      Stage(
        id: '3-3',
        name: '3-3: Der Ritualraum',
        description: 'Dunkelritter bewachen das Ritual!',
        enemies: [
          StageEnemy(enemyId: 'dark_knight', count: 1),
          StageEnemy(enemyId: 'fire_elemental', count: 1),
        ],
        gemReward: 25,
        goldReward: 700,
        expReward: 400,
        recommendedPower: 2200,
      ),
    ],
  ),

  Chapter(
    id: 4,
    title: 'Kapitel 4: Verfluchte Legenden',
    description: 'Uralte Krieger wurden durch ein Fluch korrumpiert. Befreie ihre Seelen!',
    storyText:
        'Das Ritual hat Früchte getragen. Uralte Krieger — Legenden des Reichs — erwachen unter '
        'dem Bann eines Dämonenfluches.\n\n'
        'Ihre Augen leuchten in giftigem Lila. Ihre Kraft übersteigt alles, was du bisher gesehen hast.\n\n'
        '"Sie leiden," flüstert Sylphia mit Tränen in den Augen. '
        '"Ihr wahres Ich kämpft von innen gegen den Fluch. Wir müssen sie besiegen um sie zu befreien."\n\n'
        'Manchmal ist Kämpfen der einzige Weg zur Erlösung.',
    stages: [
      Stage(
        id: '4-1',
        name: '4-1: Schattenpfad',
        description: 'Ein Schattendämon des Fluches erscheint!',
        enemies: [StageEnemy(enemyId: 'shadow_demon', count: 1)],
        gemReward: 15,
        goldReward: 600,
        expReward: 350,
        recommendedPower: 2800,
      ),
      Stage(
        id: '4-2',
        name: '4-2: Gefallene Krieger',
        description: 'Verfluchte Krieger greifen an!',
        enemies: [
          StageEnemy(enemyId: 'corrupted_warrior', count: 1),
          StageEnemy(enemyId: 'dark_knight', count: 1),
        ],
        gemReward: 15,
        goldReward: 700,
        expReward: 500,
        recommendedPower: 3500,
      ),
      Stage(
        id: '4-3',
        name: '4-3: Ururdrache Ignaros',
        description: 'Der uralte Drache erwacht durch den Fluch!',
        enemies: [StageEnemy(enemyId: 'ancient_dragon', count: 1)],
        gemReward: 40,
        goldReward: 1200,
        expReward: 800,
        recommendedPower: 4500,
      ),
    ],
  ),

  Chapter(
    id: 5,
    title: 'Kapitel 5: Chronik der Gefallenen',
    description: 'Dämonenlord Moros betritt die Welt. Alles endet hier.',
    storyText:
        'Das letzte Siegel ist gebrochen.\n\n'
        'Dämonenlord Moros – ein Wesen aus einer anderen Dimension, älter als das Reich selbst – '
        'steht nun in der Welt der Lebenden.\n\n'
        'Der Himmel über der Hauptstadt färbt sich blutrot.\n\n'
        '"Das war sein Plan von Anfang an," sagt Ryuken leise, seine Klinge in Flammen. '
        '"Die Räuber, das Ritual, die gefallenen Krieger — alles war er."\n\n'
        'Du schaust in die Augen deiner Gefährten. Kurai. Aria. Sylphia. Rexar. Alle nicken.\n\n'
        '"Gemeinsam," sagst du. "Wir beenden das hier heute."',
    stages: [
      Stage(
        id: '5-1',
        name: '5-1: Invasionsfront',
        description: 'Dämoneninvasion beginnt!',
        enemies: [
          StageEnemy(enemyId: 'shadow_demon', count: 1),
          StageEnemy(enemyId: 'corrupted_warrior', count: 1),
        ],
        gemReward: 20,
        goldReward: 1000,
        expReward: 700,
        recommendedPower: 5000,
      ),
      Stage(
        id: '5-2',
        name: '5-2: Moros\' Elitestreitmacht',
        description: 'Stärkste Diener des Dämonenlords!',
        enemies: [StageEnemy(enemyId: 'corrupted_warrior', count: 2)],
        gemReward: 20,
        goldReward: 1200,
        expReward: 900,
        recommendedPower: 6000,
      ),
      Stage(
        id: '5-3',
        name: '5-3: Dämonenlord Moros',
        description: 'Der Endgegner. Kein Zurück mehr.',
        enemies: [StageEnemy(enemyId: 'demon_lord', count: 1)],
        gemReward: 100,
        goldReward: 3000,
        expReward: 2000,
        recommendedPower: 8000,
      ),
    ],
  ),
];
