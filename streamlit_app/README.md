# Pre-Shot Situation

Streamlit-App zur Analyse der Sekunden vor einem Powerplay-Schuss. Aus einem
Spiel-CSV werden alle Schüsse in Überzahl (5v4 / 4v5) extrahiert; für einen
ausgewählten Schuss zeichnet die App die Laufwege beider Teams, die
Puck-Aktionen und die Verteidigungsstruktur auf ein NHL-Rink.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit pandas numpy matplotlib hockey_rink
```

Entwickelt mit Streamlit 1.63, pandas 3.0, matplotlib 3.11, numpy 2.5 und
hockey_rink 1.1.

## Starten

```bash
cd streamlit_app
streamlit run app.py
```

`parsing.py` und `preshot.py` werden als lokale Module importiert, die App muss
darum aus dem Ordner `streamlit_app/` gestartet werden.

## Bedienung

1. Match-CSV über den Uploader laden.
2. In der Sidebar unter **Szenario** einen Powerplay-Schuss wählen. Das Label
   zeigt Periode, Spielzeit, Schütze und Ergebnis.
3. **Sekunden vor dem Schuss** legt die Fensterlänge fest (1–15 s). Liegt im
   Fenster ein `Faceoff` oder `BluelineCrossing`, beginnt es direkt danach –
   das ausgewertete Fenster kann darum kürzer sein als der Regler. Die Caption
   über der Grafik weist darauf hin.
4. Unter **Anzeige** einzelne Ebenen ein- und ausschalten: Pässe,
   Puck-Kontrolle, Laufwege beider Teams, Start- und Schuss-Polygon.
5. Unter **Frames** lassen sich die Laufwege von Angriff und Verteidigung
   unabhängig voneinander bis zu einem Zeitpunkt abspielen. Die Endposition
   jedes Spielers bleibt immer sichtbar.
6. Die Grafik lässt sich als PNG herunterladen, im Debug-Bereich zusätzlich das
   Szenario als CSV.

## Datenformat

Erwartet wird ein Event-CSV mit einer Zeile pro Event. Relevante Spalten:

| Spalte | Bedeutung |
|---|---|
| `Period`, `MatchClock`, `Timestamp` | Zeitachse; `MatchClock` in Sekunden, aufwärts zählend |
| `EventType` | `Shot`, `Pass`, `PuckControl`, `Faceoff`, `Clear`, `BluelineCrossing` |
| `TeamStrength` | Filter auf `5v4` / `4v5` |
| `TeamStrengthType` | `HomePowerplay` / `AwayPowerplay`, bestimmt die Teamrollen |
| `EventPosition` | `HomeTeamZone` / `AwayTeamZone` / `NeutralZone`, richtet das Rink aus |
| `EventStartCoordinate`, `EventEndCoordinate` | `"x,y"` in Metern |
| `StartPlayerCoordinates1`–`12` | Spielerpositionen `"x,y"` in Metern |
| `StartPlayerId1`–`12`, `StartPlayerName1`–`12`, `StartPlayerTeam1`–`12` | Spielerzuordnung, Team ist `Home` oder `Away` |
| `ShotResult`, `EventPrimaryPlayerName` | Für Label und Legende |

Alle Koordinaten werden intern von Metern in Feet umgerechnet, weil
`hockey_rink` in Feet arbeitet. Leere oder unvollständige Koordinaten werden zu
`NaN` und fallen aus der Visualisierung heraus, ohne die App abzubrechen.

Beispieldaten liegen unter `../csv/<match>/<n>.csv`.

## Module

| Datei | Aufgabe |
|---|---|
| `app.py` | Streamlit-UI, Widgets, Caching, Downloads |
| `parsing.py` | Powerplay-Filter, Schussliste, Zeitfenster, Dropdown-Labels |
| `preshot.py` | Koordinaten-Aufbereitung, Torhüter-Erkennung, Matplotlib-Plot |

## Torhüter-Erkennung

Torhüter werden nicht aus den Daten gelesen, sondern über die mediane Distanz
zum eigenen Tor bestimmt (Grenze: 12 ft, `preshot.GOALIE_DISTANCE_FT`). Das
läuft bewusst über den gesamten Powerplay-Datensatz statt über ein einzelnes
Szenario, weil wenige Frames für eine stabile Erkennung nicht reichen. Ergebnis
ist eine Menge pro Team, damit Torhüterwechsel im Spielverlauf abgedeckt sind.

Erkannte Torhüter werden aus den Laufwegen und Polygonen herausgefiltert. Wird
für das verteidigende Team keiner erkannt, bleiben die Polygone leer, weil
`draw_structure_polygon` genau vier Spieler pro Frame erwartet – die App zeigt
in diesem Fall eine Warnung.

## Performance

Ein Rerun kostete ursprünglich rund 780 ms, wovon der Plot den grössten Teil
ausmachte. Drei Stellen sind dafür angepasst:

- **`preshot.skip_patch_limits`**: `rink.draw` legt rund 70 Polygone mit je
  einigen hundert Vertices an, für die matplotlib in `add_patch` die
  Bezier-Extrema auflöst, um `dataLim` zu aktualisieren. Diese Grenzen
  überschreibt `hockey_rink` danach selbst per `set_xlim`/`set_ylim`. Der
  Context-Manager schaltet die Berechnung für den Draw ab: 290 ms → 25 ms bei
  pixelidentischem Ergebnis.
- **Ein PNG statt zwei**: `st.pyplot` rendert intern selbst ein PNG. Die App
  erzeugt das Bild jetzt einmal in `render_scenario_png` und nutzt es für
  Anzeige (`st.image`) und Download-Button gemeinsam.
- **`@st.fragment` auf `render_visualisation`**: Checkboxen und Frame-Regler
  lösen nur einen Fragment-Rerun aus, das Parsen der Datei und die
  Torhütererkennung laufen dabei nicht erneut.

Gecacht wird das CSV-Einlesen, die Torhütererkennung und das gerenderte PNG.
`st.cache_data` hasht nur den Bytecode der dekorierten Funktion, nicht den von
`parsing.py` und `preshot.py`. Damit Änderungen dort trotzdem greifen, gibt
`module_stamp()` den Zeitstempel beider Module als Cache-Key mit – gecachte
Ergebnisse verfallen also automatisch beim Speichern.
