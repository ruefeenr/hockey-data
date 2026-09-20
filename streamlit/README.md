# Pre-Shot Situation

> **Note:** This README is an **AI-generated summary** of the project. It
> describes the current state of the code, but it does not replace a manual
> review.

Streamlit app for analysing the seconds before a power-play shot. From a match
CSV it extracts every shot on a man advantage (5v4 / 4v5); for a selected shot
the app draws both teams' skating paths, puck actions, and the defensive
structure on an IIHF rink.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit pandas numpy matplotlib hockey_rink
```

Developed with Streamlit 1.63, pandas 3.0, matplotlib 3.11, numpy 2.5, and
hockey_rink 1.1.

## Running

```bash
cd streamlit
streamlit run app.py
```

`parsing.py` and `preshot.py` are imported as local modules, so the app must be
started from the `streamlit/` directory.

Project documentation (objectives, preprocessing, visualisation steps, and
known mistakes) lives in `report.py`, itself a Streamlit app:

```bash
cd streamlit
streamlit run report.py
```

If `app.py` is already running on port 8501, use another port:

```bash
streamlit run report.py --server.port 8502
```

## Usage

1. Load a match CSV via the uploader.
2. In the sidebar under **Szenario**, pick a power-play shot. The label shows
   period, game time, shooter, and result. Only shots by the team on the
   power play are listed – shorthanded counters travel the other way and do
   not match the visualisation roles.
3. **Sekunden vor dem Schuss** sets the window length (1–15 s). If the window
   contains a `Faceoff`, a `BluelineCrossing`, or a puck recovery by the
   power-play team, it starts there – so the evaluated window can be shorter
   than the slider. The caption above the plot notes this. The window always
   ends at the shot, even though `MatchClock` only resolves to seconds and
   rebounds can still follow in the same second.
4. Under **Anzeige**, toggle individual layers: passes, puck control, skating
   paths of both teams, start polygon, and shot polygon.
5. Under **Frames**, the attacking and defending skating paths can be played
   independently up to a chosen frame. Each player's final position stays
   visible.
6. The plot can be downloaded as a PNG; in the debug section the scenario can
   also be downloaded as CSV.

## Data format

An event CSV with one row per event is expected. Relevant columns:

| Column | Meaning |
|---|---|
| `Period`, `MatchClock`, `Timestamp` | Timeline; `MatchClock` in seconds, counting up |
| `EventType` | `Shot`, `Pass`, `PuckControl`, `Faceoff`, `Clear`, `BluelineCrossing` |
| `EventPrimaryTeam` | `Home` / `Away`; limits the shot list to the team on the power play |
| `PuckControlState` | `HomeControl` / `AwayControl` / `Loose` / `Contested`; cuts the window at the last possession change |
| `TeamStrength` | Filter on `5v4` / `4v5` |
| `TeamStrengthType` | `HomePowerplay` / `AwayPowerplay`, determines team roles |
| `EventPosition` | `HomeTeamZone` / `AwayTeamZone` / `NeutralZone`, orients the rink |
| `EventStartCoordinate`, `EventEndCoordinate` | `"x,y"` in metres |
| `StartPlayerCoordinates1`–`12` | Player positions `"x,y"` in metres |
| `StartPlayerId1`–`12`, `StartPlayerName1`–`12`, `StartPlayerTeam1`–`12` | Player assignment; team is `Home` or `Away` |
| `ShotResult`, `EventPrimaryPlayerName` | For label and legend |

All coordinates are converted from metres to feet internally because
`hockey_rink` works in feet. Empty or incomplete coordinates become `NaN` and
drop out of the visualisation without crashing the app.

Sample data lives under `../csv/<match>/<n>.csv`.

## Modules

| File | Role |
|---|---|
| `app.py` | Streamlit UI, widgets, caching, downloads |
| `parsing.py` | Power-play filter, shot list, time window, dropdown labels |
| `preshot.py` | Coordinate prep, goalie detection, Matplotlib plot |
| `report.py` | Written project documentation as a Streamlit report |

## Goalie detection

Goalies are not read from the data. They are identified by median distance to
their own net (threshold: 12 ft, `preshot.GOALIE_DISTANCE_FT`). This runs over
the full power-play dataset rather than a single scenario, because a few frames
are not enough for a stable detection. The result is a set per team, so goalie
changes during the game are covered.

Detected goalies are filtered out of skating paths and polygons. If none is
detected for the defending team, the polygons stay empty because
`draw_structure_polygon` expects exactly four players per frame – the app shows
a warning in that case.

## Performance

A rerun originally cost around 780 ms, most of it in the plot. Three places
were adjusted:

- **`preshot.skip_patch_limits`**: `rink.draw` creates about 70 polygons with a
  few hundred vertices each. In `add_patch`, matplotlib resolves Bezier extrema
  to update `dataLim`. `hockey_rink` then overwrites those limits itself via
  `set_xlim`/`set_ylim`. The context manager turns that calculation off for the
  draw: 290 ms → 25 ms with a pixel-identical result.
- **One PNG instead of two**: `st.pyplot` internally renders a PNG of its own.
  The app now produces the image once in `render_scenario_png` and reuses it
  for display (`st.image`) and the download button.
- **`@st.fragment` on `render_visualisation`**: Checkboxes and frame sliders
  only trigger a fragment rerun; parsing the file and detecting goalies do not
  run again.

CSV reading, goalie detection, and the rendered PNG are cached. `st.cache_data`
hashes only the bytecode of the decorated function, not that of `parsing.py`
and `preshot.py`. So that changes there still take effect, `module_stamp()`
passes both modules' timestamps as a cache key – cached results therefore
expire automatically on save.
