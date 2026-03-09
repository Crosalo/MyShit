import '../models/character.dart';

// ─── Realm Chronicles ─── Original Anime Characters ───
// Fully original characters inspired by classic anime archetypes:
// Dragon Knights, Holy Warriors, Shadow Assassins, Elemental Mages, Beast Fighters...

const List<Character> allCharacters = [
  // ═══════════════════════════════════════
  // SSR – LEGENDÄRE CHARAKTERE
  // ═══════════════════════════════════════

  Character(
    id: 'ryuken',
    name: 'Ryuken',
    title: 'Klingenprinz des Infernos',
    lore:
        'Ryuken ist ein Drachenprinz, der einst von einem feuerspeienden Uralten Drachen verschluckt wurde. '
        'Statt zu sterben, schmolz seine Seele mit der Kraft des Drachen zusammen. '
        'Er trägt nun ein glühendes Flammenschwert und kann die Hitze eines Vulkans aus seiner Klinge entfesseln. '
        'Sein Haar ist weiß wie Asche, seine Augen leuchten in feurigem Rotgold.',
    rarity: Rarity.ssr,
    element: Element.fire,
    characterClass: CharacterClass.warrior,
    stats: CharacterStats(hp: 9200, atk: 980, def: 520, spd: 72),
    emoji: '🔥',
    normalSkill: Skill(
      name: 'Flammensturz',
      description: 'Springt in die Luft und schlägt mit einer flammenden Klinge nieder: 220% ATK.',
      damage: 220,
      cooldown: 3,
    ),
    ultimateSkill: Skill(
      name: 'Drachenseele: Inferno',
      description: 'Erweckt die Drachenseele in sich: Klinge explodiert in einem Feuermeer — 450% ATK Schaden.',
      damage: 450,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'seraphiel',
    name: 'Seraphiel',
    title: 'Heiliger Wächter des Lichts',
    lore:
        'Seraphiel ist ein Erzengel-Krieger, der von den Göttern selbst entsandt wurde. '
        'Seine silberne Rüstung leuchtet mit göttlichem Licht, sein Schwert aus reinem Mondstahl '
        'kann Dunkelheit zerschneiden wie Papier. Er spricht wenig, aber wenn er kämpft, '
        'verstummt selbst die Zeit.',
    rarity: Rarity.ssr,
    element: Element.light,
    characterClass: CharacterClass.warrior,
    stats: CharacterStats(hp: 8000, atk: 1150, def: 450, spd: 68),
    emoji: '☀️',
    normalSkill: Skill(
      name: 'Heilige Klinge',
      description: 'Schlägt mit göttlicher Kraft zu: 240% ATK Lichtschaden.',
      damage: 240,
      cooldown: 3,
    ),
    ultimateSkill: Skill(
      name: 'Urteil der Götter',
      description: 'Ein Strahl göttlichen Lichts durchbohrt alles: 500% ATK Lichtschaden.',
      damage: 500,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'kurai',
    name: 'Kurai',
    title: 'Phantom des Abgrunds',
    lore:
        'Kurai ist ein Geisterjäger, der durch einen Fluch zur Hälfte in die Schattenwelt gezogen wurde. '
        'Er kann sich in reinen Schatten verwandeln, teleportieren und Klingen aus konzentrierter '
        'Dunkelheit erschaffen. Niemand weiß sein wahres Gesicht — er trägt immer eine Maske '
        'aus schwarzem Glas.',
    rarity: Rarity.ssr,
    element: Element.dark,
    characterClass: CharacterClass.rogue,
    stats: CharacterStats(hp: 7200, atk: 1050, def: 360, spd: 95),
    emoji: '🌑',
    normalSkill: Skill(
      name: 'Schattendurchbruch',
      description: 'Teleportiert hinter den Feind und schlägt mit einer Dunkelheitklinge zu: 200% ATK.',
      damage: 200,
      cooldown: 2,
    ),
    ultimateSkill: Skill(
      name: 'Abgrund-Resonanz',
      description: 'Öffnet einen Spalt in die Schattenwelt: dreifacher Angriff aus dem Nichts — 480% ATK.',
      damage: 480,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'varuga',
    name: 'Varuga',
    title: 'Bestienkaiser der Wildnis',
    lore:
        'Varuga ist der letzte lebende Berserkerkönig eines ausgestorbenen Kriegervolkes. '
        'In seiner Kampfrage nimmt er halb-tierische Gestalt an — seine Knochen werden zu Klingen, '
        'sein Fell zu Stahl. Er isst, trinkt und schläft auf dem Schlachtfeld. '
        'Kein Angriff kann ihn aufhalten, nur er selbst.',
    rarity: Rarity.ssr,
    element: Element.earth,
    characterClass: CharacterClass.beast,
    stats: CharacterStats(hp: 12000, atk: 860, def: 680, spd: 55),
    emoji: '🐺',
    normalSkill: Skill(
      name: 'Reißende Bestie',
      description: 'Wilder Biss-Angriff: 190% ATK. Heilt sich für 15% des verursachten Schadens.',
      damage: 190,
      cooldown: 3,
    ),
    ultimateSkill: Skill(
      name: 'Berserkermodus: Entfesselt',
      description: 'Verwandelt sich in einen Urzeit-Berserker: 380% ATK. Heilt 30% des Schadens zurück.',
      damage: 380,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'hyouga',
    name: 'Hyouga',
    title: 'Schwertkämpfer des ewigen Frosts',
    lore:
        'Hyouga ist ein einsamer Wanderer aus dem Polarreich. Sein Katana wurde in einem See '
        'eingefroren, der nie taut — als er es heraus zog, gefroren seine Emotionen mit. '
        'Er kämpft mit eiskalter Präzision, jede Bewegung ist berechnet und tödlich.',
    rarity: Rarity.ssr,
    element: Element.water,
    characterClass: CharacterClass.warrior,
    stats: CharacterStats(hp: 8800, atk: 920, def: 590, spd: 65),
    emoji: '❄️',
    normalSkill: Skill(
      name: 'Eisklingensturm',
      description: 'Entfesselt eiskristallene Schockwellen: 210% ATK Kälteschaden.',
      damage: 210,
      cooldown: 3,
    ),
    ultimateSkill: Skill(
      name: 'Absolute Eiszeit',
      description: 'Die Welt gefriert: 460% ATK Kälteschaden. Feind verliert seine nächste Runde.',
      damage: 460,
      cooldown: 0,
    ),
  ),

  // ═══════════════════════════════════════
  // SR – STARKE CHARAKTERE
  // ═══════════════════════════════════════

  Character(
    id: 'aria_mage',
    name: 'Aria',
    title: 'Geistmagierin der Winde',
    lore:
        'Aria wurde in einer Sturmnacht geboren — ihr erster Schrei ließ die Fenster zerbersten. '
        'Sie ist eine Prodigy-Magierin der Windakademie und kann Klangschwingungen in '
        'tödliche Windklingen umwandeln. Ihr langes lilafarbenes Haar tanzt ständig in einem '
        'unsichtbaren Wind.',
    rarity: Rarity.sr,
    element: Element.wind,
    characterClass: CharacterClass.mage,
    stats: CharacterStats(hp: 6800, atk: 820, def: 310, spd: 80),
    emoji: '🌸',
    normalSkill: Skill(
      name: 'Windklang-Resonanz',
      description: 'Konzentrierte Windmagie als scharfe Klangschwingungen: 190% ATK.',
      damage: 190,
      cooldown: 3,
    ),
    ultimateSkill: Skill(
      name: 'Sturm-Symphonie',
      description: 'Eine magische Windexplosion aus reiner Klangkraft: 400% ATK Schaden.',
      damage: 400,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'rexar',
    name: 'Rexar',
    title: 'Söldner der goldenen Klinge',
    lore:
        'Rexar ist ein legendärer Söldner und Schatzjäger. Sein Körper ist mit magischen '
        'Tätowierungen bedeckt — jede erzählt von einem anderen Dungeon, den er überlebt hat. '
        'Er kämpft mit doppelten vergoldeten Pistolenschwertern und lacht mitten im Gefecht.',
    rarity: Rarity.sr,
    element: Element.earth,
    characterClass: CharacterClass.rogue,
    stats: CharacterStats(hp: 7000, atk: 780, def: 380, spd: 85),
    emoji: '💰',
    normalSkill: Skill(
      name: 'Goldener Wirbelwind',
      description: 'Rotierender Angriff mit beiden Klingen: 180% ATK Schaden.',
      damage: 180,
      cooldown: 2,
    ),
    ultimateSkill: Skill(
      name: 'Söldners Todesstoß',
      description: 'Entfesselt alle angesammelten Angriffskraft: 370% ATK Schaden.',
      damage: 370,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'sylphia',
    name: 'Sylphia',
    title: 'Heilige Elfenmagierin',
    lore:
        'Sylphia ist eine Elfenprinzessin, die ihre Heimat verlassen hat um die Welt zu heilen. '
        'Sie trägt ein leuchtendes Stab aus dem Herzholz eines 1000-jährigen Baums. '
        'Ihre Heilmagie kann selbst tödliche Wunden schließen, und ihr Windtanz im Kampf '
        'ist so anmutig wie tödlich.',
    rarity: Rarity.sr,
    element: Element.wind,
    characterClass: CharacterClass.healer,
    stats: CharacterStats(hp: 7500, atk: 650, def: 420, spd: 90),
    emoji: '🧚',
    normalSkill: Skill(
      name: 'Naturheilung',
      description: 'Heilende Energie der Natur: Stellt 180% ATK als HP wieder her.',
      damage: 180,
      cooldown: 3,
      isHeal: true,
    ),
    ultimateSkill: Skill(
      name: 'Elfentanz: Geist des Waldes',
      description: 'Beschwört die Kraft des Urwalds: 350% ATK Naturschaden.',
      damage: 350,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'raizen',
    name: 'Raizen',
    title: 'Blitzmagier der Sturmakademie',
    lore:
        'Raizen war ein brillanter Schüler der Sturmakademie — bis ihn ein Blitz beim Experiment '
        'traf und dauerhaft sein Nervensystem mit elektrischer Energie auflud. '
        'Er kann nun Blitze aus dem Nichts rufen. Seine blauen Augen leuchten bei jeder Entladung.',
    rarity: Rarity.sr,
    element: Element.wind,
    characterClass: CharacterClass.mage,
    stats: CharacterStats(hp: 6200, atk: 860, def: 280, spd: 88),
    emoji: '⚡',
    normalSkill: Skill(
      name: 'Blitzpfeil',
      description: 'Ein präziser gebündelter Blitzstrahl: 200% ATK Blitzschaden.',
      damage: 200,
      cooldown: 2,
    ),
    ultimateSkill: Skill(
      name: 'Donnersturm-Apokalypse',
      description: 'Ruft einen verheerenden Gewittersturm herauf: 420% ATK Blitzschaden.',
      damage: 420,
      cooldown: 0,
    ),
  ),

  // ═══════════════════════════════════════
  // R – ANFÄNGER-CHARAKTERE
  // ═══════════════════════════════════════

  Character(
    id: 'ignis',
    name: 'Ignis',
    title: 'Feuernostalgie-Kämpfer',
    lore:
        'Ignis ist ein junger Kämpfer aus einem Dorf, das von einem Drachen verwüstet wurde. '
        'Er hat sich selbst das Feuerkampfschwingen beigebracht und träumt davon, '
        'stark genug zu werden um sein Dorf zu rächen. Sein Wille brennt heller als seine Flammen.',
    rarity: Rarity.r,
    element: Element.fire,
    characterClass: CharacterClass.warrior,
    stats: CharacterStats(hp: 5500, atk: 580, def: 320, spd: 70),
    emoji: '🔸',
    normalSkill: Skill(
      name: 'Feuerhieb',
      description: 'Ein entschlossener Schwertschwung mit Feuerenergie: 160% ATK.',
      damage: 160,
      cooldown: 3,
    ),
    ultimateSkill: Skill(
      name: 'Willen des Infernos',
      description: 'Kämpft mit brennendem Willen: 320% ATK Feuerschaden.',
      damage: 320,
      cooldown: 0,
    ),
  ),

  Character(
    id: 'marina',
    name: 'Marina',
    title: 'Heilerin der Meeresfluten',
    lore:
        'Marina ist eine junge Heilmagierin, aufgewachsen auf einem Fischerboot inmitten des Ozeans. '
        'Die Wasserspiriten haben ihr ihre Magie geschenkt, als sie als Kind fast ertrunken ist. '
        'Sie heilt mit dem Wasser des Lebens selbst.',
    rarity: Rarity.r,
    element: Element.water,
    characterClass: CharacterClass.healer,
    stats: CharacterStats(hp: 6000, atk: 480, def: 350, spd: 75),
    emoji: '💧',
    normalSkill: Skill(
      name: 'Meeresheilung',
      description: 'Heilendes Meerwasser: Stellt 160% ATK als HP wieder her.',
      damage: 160,
      cooldown: 3,
      isHeal: true,
    ),
    ultimateSkill: Skill(
      name: 'Ozean-Segen',
      description: 'Die Kraft des Ozeans heilt: Stellt 300% ATK als HP wieder her.',
      damage: 300,
      cooldown: 0,
      isHeal: true,
    ),
  ),

  Character(
    id: 'stonefang',
    name: 'Stonefang',
    title: 'Erdfaust-Krieger',
    lore:
        'Stonefang ist ein Bergkämper aus dem Hochland. Seine Fäuste sind so hart wie Fels — '
        'bildlich und wörtlich, da seine Erdenmagie seine Knochen zu Stein verdichten kann. '
        'Er kämpft langsam, aber sein Schlag kann einen Berghang einreißen.',
    rarity: Rarity.r,
    element: Element.earth,
    characterClass: CharacterClass.warrior,
    stats: CharacterStats(hp: 7000, atk: 520, def: 480, spd: 50),
    emoji: '🪨',
    normalSkill: Skill(
      name: 'Felsfaust',
      description: 'Ein mächtiger Erdschlag: 150% ATK Erdschaden.',
      damage: 150,
      cooldown: 3,
    ),
    ultimateSkill: Skill(
      name: 'Erdbeben-Stampede',
      description: 'Erschüttert die Erde mit einem Urknall-Stampfen: 310% ATK Erdschaden.',
      damage: 310,
      cooldown: 0,
    ),
  ),
];

Character? findCharacterById(String id) {
  try {
    return allCharacters.firstWhere((c) => c.id == id);
  } catch (_) {
    return null;
  }
}

// Gacha pools by rarity
List<Character> get ssrPool => allCharacters.where((c) => c.rarity == Rarity.ssr).toList();
List<Character> get srPool => allCharacters.where((c) => c.rarity == Rarity.sr).toList();
List<Character> get rPool => allCharacters.where((c) => c.rarity == Rarity.r).toList();
