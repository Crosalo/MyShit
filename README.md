# Aether Chronicles – 3D-Anime-Gacha (Unity, Android & iOS)

## Öffnen
1. Unity Hub → *Add project from disk* → diesen Ordner wählen (Unity 6, 6000.0 LTS oder neuer, Module Android/iOS).
2. Leere Szene öffnen und **Play** drücken – das Spiel startet sich selbst (`GameApp`), keine Prefabs nötig.
3. Build: File → Build Profiles → Android/iOS (iOS braucht einen Mac mit Xcode).

## Inhalt
- Rundenkampf mit Fähigkeitskarten: 3 Aktionen pro Runde, gleiche Nachbarkarten verschmelzen (Rang 1→3),
  Verschieben kostet eine Aktion (Slot gesperrt), Ultimativ-Leiste, Elemente, Wellen, Bosse.
- 12 eigene Helden, Gacha mit Pity (90) und 50/50, Story: Prolog + 3 Kapitel, geführtes Tutorial.
- Spiellogik: `Assets/_Game/Scripts/Core` (ohne Unity testbar: `dotnet test Tools/CoreTests`).
- Eigene 3D-Modelle (z. B. VRoid + UniVRM) als Prefab unter `Assets/_Game/Resources/Characters/<id>` ersetzen die Platzhalter.
