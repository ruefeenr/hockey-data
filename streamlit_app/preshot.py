# Standard Library
import contextlib
import re
# hockey_rink nutzt urllib.request/urllib.error, ohne sie selbst zu importieren
import urllib.error
import urllib.request

# Data
import numpy as np
import pandas as pd

# Visualisierung
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

# Hockey rink
from hockey_rink import NHLRink

# Setup
rink = NHLRink()

# Attacker Colors
attacker_color = "m"

# Defender Colors
defender_color = "seagreen"
initial_polygon_color = "seagreen"
final_polygon_color = "seagreen"

# Event Colors
puck_control_color = "black"
pass_color = "black"

# Koordinaten von Metern in Feet umrechnen
M_TO_FT = 3.280839895


def coordinates_to_feet(series):
    coords = (
        series
        .astype("string")
        .str.split(",", n=1, expand=True)
        # damit leere Koordinaten nicht zum absturz führen
        .reindex(columns=[0, 1])
    )

    x = pd.to_numeric(coords[0], errors="coerce") * M_TO_FT
    y = pd.to_numeric(coords[1], errors="coerce") * M_TO_FT
    return x, y


def prepare_shot_data(df):
    """
    Bereitet die Rohdaten einer Shot-Situation auf.

    Die Feet-Umrechnung muss vor dem Frame-Index passieren,
    sonst fehlen den nachgelagerten Funktionen die _ft-Spalten.
    """

    # df kann ein Slice eines grösseren DataFrames sein
    df = df.copy()

    df["strength_type_state"] = df["TeamStrengthType"].ffill()

    # Event-Koordinaten in Feet umrechnen
    df["EventStartX_ft"], df["EventStartY_ft"] = coordinates_to_feet(
        df["EventStartCoordinate"]
    )
    df["EventEndX_ft"], df["EventEndY_ft"] = coordinates_to_feet(
        df["EventEndCoordinate"]
    )

    # Spielerkoordinaten in Feet umrechnen
    for i in range(1, 13):
        coord_col = f"StartPlayerCoordinates{i}"
        if coord_col not in df.columns:
            continue

        x, y = coordinates_to_feet(df[coord_col])

        df[f"StartPlayerX{i}_ft"] = x
        df[f"StartPlayerY{i}_ft"] = y

    # Jede Event-Zeile bekommt einen fortlaufenden Frame-Index
    return df.reset_index(drop=True)


def load_shot_data(csv_path):
    return prepare_shot_data(pd.read_csv(csv_path))


# Prüft ob PuckControl und Pass denselben weg haben (Versuch)
def is_redundant_puck_control(
    previous_row,
    current_row,
    coordinate_tolerance_ft=1.0,
    time_tolerance_ms=150
):

    if not (
        previous_row["EventType"] == "Pass"
        and current_row["EventType"] == "PuckControl"
    ):
        return False

    coordinate_columns = [
        "EventStartX_ft",
        "EventStartY_ft",
        "EventEndX_ft",
        "EventEndY_ft"
    ]

    if (
        previous_row[coordinate_columns].isna().any()
        or current_row[coordinate_columns].isna().any()
    ):
        return False

    time_difference = abs(
        current_row["Timestamp"]
        - previous_row["Timestamp"]
    )

    if time_difference > time_tolerance_ms:
        return False

    start_distance = np.hypot(
        current_row["EventStartX_ft"]
        - previous_row["EventStartX_ft"],
        current_row["EventStartY_ft"]
        - previous_row["EventStartY_ft"]
    )

    end_distance = np.hypot(
        current_row["EventEndX_ft"]
        - previous_row["EventEndX_ft"],
        current_row["EventEndY_ft"]
        - previous_row["EventEndY_ft"]
    )

    return (
        start_distance <= coordinate_tolerance_ft
        and end_distance <= coordinate_tolerance_ft
    )


# Spielernummer aus Namen wie "#11 Danny Nelson" extrahieren
def extract_player_number(name):
    if pd.isna(name):
        return ""

    match = re.match(r"#(\d+)", str(name).strip())
    return match.group(1) if match else str(name)


POSITION_COLUMNS = [
    "frame",
    "player_id",
    "player_name",
    "player_number",
    "x",
    "y"
]


def collect_team_positions(pre_shot_df, target_team):
    team_positions = []

    for frame_idx, row in pre_shot_df.iterrows():

        for i in range(1, 13):
            team = row.get(f"StartPlayerTeam{i}")
            player_id = row.get(f"StartPlayerId{i}")
            player_name = row.get(f"StartPlayerName{i}")

            x = row.get(f"StartPlayerX{i}_ft")
            y = row.get(f"StartPlayerY{i}_ft")

            if (
                team != target_team
                or pd.isna(player_id)
                or pd.isna(player_name)
                or pd.isna(x)
                or pd.isna(y)
            ):
                continue

            team_positions.append({
                "frame": frame_idx,
                "player_id": player_id,
                "player_name": player_name,
                "player_number": extract_player_number(player_name),
                "x": x,
                "y": y
            })

    # Spalten explizit setzen, damit auch ein leeres Ergebnis filterbar bleibt
    return pd.DataFrame(team_positions, columns=POSITION_COLUMNS)


# Torhüter liegen im Median 3 bis 6 ft vom eigenen Tor entfernt, der
# nächstbeste Feldspieler rund 20 ft. Die Grenze liegt dazwischen.
GOALIE_DISTANCE_FT = 12


def detect_goalie_ids(
    df,
    team,
    goal_x_ft=89,
    max_goalie_distance_ft=GOALIE_DISTANCE_FT
):
    """
    Alle Torhüter eines Teams, erkannt an der medianen Distanz zum eigenen Tor.

    Bewusst eine Menge statt eines einzelnen Spielers: Teams wechseln im Lauf
    eines Spiels den Goalie, dann steht in manchen Szenarien der eine und in
    anderen der andere im Tor.
    """

    if team == "Home":
        own_goal_x = -goal_x_ft

    elif team == "Away":
        own_goal_x = goal_x_ft

    else:
        return set()

    team_positions = collect_team_positions(
        pre_shot_df=df,
        target_team=team
    )

    if team_positions.empty:
        return set()

    team_positions = team_positions.copy()

    # --------------------------------------------
    # Distanz zum eigenen Tor
    # --------------------------------------------
    team_positions["goal_distance"] = np.hypot(
        team_positions["x"] - own_goal_x,
        team_positions["y"]
    )

    # --------------------------------------------
    # Median-Distanz je Spieler
    # --------------------------------------------
    player_distances = (
        team_positions
        .groupby("player_id")
        .agg(
            median_goal_distance=("goal_distance", "median"),
            frames=("frame", "nunique")
        )
    )

    # Einzelne Frames direkt vor dem Tor sollen keinen Feldspieler
    # zum Goalie machen
    min_frames = max(
        1,
        int(0.05 * team_positions["frame"].nunique())
    )

    goalies = player_distances[
        (player_distances["frames"] >= min_frames)
        & (player_distances["median_goal_distance"] <= max_goalie_distance_ft)
    ]

    return set(goalies.index)


def detect_goalies(df):
    """
    Torhüter je Team, bestimmt auf dem gesamten übergebenen DataFrame.

    Ein einzelnes Szenario umfasst oft nur wenige Zeilen, das reicht für eine
    stabile Erkennung nicht. Über alle Powerplay-Zeilen eines Spiels schon.
    """

    return {
        team: detect_goalie_ids(df, team)
        for team in ("Home", "Away")
    }


def _as_id_set(goalie_ids):
    if goalie_ids is None:
        return set()

    if not hasattr(goalie_ids, "__iter__"):
        return {goalie_ids}

    return set(goalie_ids)


def draw_team_trails(
    ax,
    team_df,
    color,
    visible_until_frame=None,
    show_final_number=True
):
    if team_df.empty:
        return

    final_frame = team_df["frame"].max()

    for player_id, full_player_df in team_df.groupby("player_id"):

        full_player_df = (
            full_player_df
            .sort_values("frame")
            .reset_index(drop=True)
            .copy()
        )

        # Finale Position des Spielers
        final_row = full_player_df.iloc[-1]

        final_plot_x, final_plot_y = rink.convert_xy(
            [final_row["x"]],
            [final_row["y"]],
            ax=ax
        )

        final_plot_x = final_plot_x[0]
        final_plot_y = final_plot_y[0]

        # --------------------------------------------
        # Historie bis zum ausgewählten Slider-Frame
        # --------------------------------------------
        if visible_until_frame is None:
            history_df = full_player_df.copy()
        else:
            history_df = full_player_df[
                full_player_df["frame"] <= visible_until_frame
            ].copy()

        # Finale Position wird separat gezeichnet
        history_df = history_df[
            history_df["frame"] < final_frame
        ].copy()

        if not history_df.empty:

            plot_x, plot_y = rink.convert_xy(
                history_df["x"].to_numpy(),
                history_df["y"].to_numpy(),
                ax=ax
            )

            plot_x = np.asarray(plot_x)
            plot_y = np.asarray(plot_y)

            n_positions = len(history_df)

            alphas = np.linspace(
                0.2,
                0.9,
                n_positions
            )

            # Bewegungslinien
            for i in range(n_positions - 1):
                ax.plot(
                    [plot_x[i], plot_x[i + 1]],
                    [plot_y[i], plot_y[i + 1]],
                    color=color,
                    linewidth=2.0,
                    alpha=alphas[i + 1],
                    zorder=3
                )

            # Frühere Positionen
            for i in range(n_positions):
                ax.scatter(
                    plot_x[i],
                    plot_y[i],
                    s=50,
                    color=color,
                    edgecolors="black",
                    linewidth=0.7,
                    alpha=alphas[i],
                    zorder=4
                )

            # Nur wenn die Historie tatsächlich bis direkt
            # vor den finalen Frame reicht, verbinden
            last_history_frame = history_df.iloc[-1]["frame"]

            if last_history_frame == final_frame - 1:
                ax.plot(
                    [plot_x[-1], final_plot_x],
                    [plot_y[-1], final_plot_y],
                    color=color,
                    linewidth=2.0,
                    alpha=1.0,
                    zorder=3
                )

        # --------------------------------------------
        # Finale Position bleibt immer sichtbar
        # --------------------------------------------
        player_number = final_row["player_number"]

        ax.scatter(
            final_plot_x,
            final_plot_y,
            s=150,
            color=color,
            edgecolors="black",
            linewidth=1.2,
            alpha=1.0,
            zorder=50
        )

        if show_final_number:
            ax.text(
                final_plot_x,
                final_plot_y,
                str(player_number),
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                color="white",
                zorder=100,
                clip_on=False
            )


def get_powerplay_teams(strength_type):
    if strength_type == "HomePowerplay":
        return "Home", "Away"

    if strength_type == "AwayPowerplay":
        return "Away", "Home"

    return None, None


# Verteidigungs-Polygon -> Verbindet die vier Spielerpositionen eines Frames zu einem Polygon
def draw_structure_polygon(
    ax,
    frame_df,
    color,
    alpha=0.15,
    linewidth=2,
    linestyle="-"
):

    if len(frame_df) != 4:
        return

    plot_x, plot_y = rink.convert_xy(
        frame_df["x"].to_numpy(),
        frame_df["y"].to_numpy(),
        ax=ax
    )

    center_x = np.mean(plot_x)
    center_y = np.mean(plot_y)

    # Punkte um den Mittelpunkt sortieren
    angles = np.arctan2(
        plot_y - center_y,
        plot_x - center_x
    )

    order = np.argsort(angles)

    polygon_coordinates = [
        (plot_x[i], plot_y[i])
        for i in order
    ]

    polygon = Polygon(
        polygon_coordinates,
        closed=True,
        facecolor=color,
        edgecolor=color,
        alpha=alpha,
        linewidth=linewidth,
        linestyle=linestyle,
        zorder=2
    )

    ax.add_patch(polygon)


# Angriffzone immer Oben
def get_rink_view(pre_shot_df):

    # Schuss als Referenz suchen
    shot_rows = pre_shot_df[
        pre_shot_df["EventType"] == "Shot"
    ]

    if not shot_rows.empty:
        reference_row = shot_rows.iloc[-1]
    else:
        reference_row = pre_shot_df.iloc[-1]

    event_position = reference_row.get("EventPosition")

    # HomeTeamZone
    if event_position == "HomeTeamZone":
        display_range = "defence"
        rotation = 270

    # AwayTeamZone
    elif event_position == "AwayTeamZone":
        display_range = "offence"
        rotation = 90

    # Neutral Zone (evtl unnötig -> Abhängig von Input Daten)
    elif event_position == "NeutralZone":
        display_range = "full"
        rotation = 90

    # Fallback
    else:
        display_range = "full"
        rotation = 90

    return display_range, rotation, event_position


@contextlib.contextmanager
def skip_patch_limits():
    """
    Schaltet die Datengrenzen-Berechnung von matplotlib für Patches ab.

    rink.draw legt rund 70 Polygone mit je einigen hundert Vertices an und
    matplotlib löst für jedes davon in add_patch die Bezier-Extrema auf, um
    dataLim zu aktualisieren - insgesamt etwa 60'000 Segmente. Die Grenzen
    setzt hockey_rink danach per set_xlim/set_ylim ohnehin selbst, das
    Ergebnis ist pixelidentisch und der Draw etwa zehnmal schneller.
    """

    original = getattr(Axes, "_update_patch_limits", None)

    # Private API. Wird sie irgendwann umbenannt, zeichnen wir eben wieder
    # langsam, statt die App mit einem AttributeError abzubrechen.
    if original is None:
        yield
        return

    Axes._update_patch_limits = lambda self, patch: None

    try:
        yield
    finally:
        Axes._update_patch_limits = original


def plot_pre_shot_summary(
    pre_shot_df,
    attacking_goalie_ids=None,
    defending_goalie_ids=None,
    show_passes=True,
    show_puck_control=True,
    show_attacker_trails=True,
    show_defender_trails=True,
    show_initial_polygon=True,
    show_final_polygon=True,
    attacker_frame=None,
    defender_frame=None
):
    fig, ax = plt.subplots(figsize=(11, 8))

    # --------------------------------------------
    # Rink automatisch ausrichten
    # --------------------------------------------
    display_range, rotation, event_position = get_rink_view(
        pre_shot_df
    )

    with skip_patch_limits():
        rink.draw(
            display_range=display_range,
            rotation=rotation,
            ax=ax
        )

    # --------------------------------------------
    # Teams bestimmen
    # --------------------------------------------
    first_row = pre_shot_df.iloc[0]

    attacking_team, defending_team = get_powerplay_teams(
        first_row["strength_type_state"]
    )

    # --------------------------------------------
    # Events zeichnen
    # --------------------------------------------
    for i in range(len(pre_shot_df)):

        row = pre_shot_df.iloc[i]
        event_df = pre_shot_df.iloc[[i]]

        if (
            show_passes
            and row["EventType"] == "PuckControl"
            and i > 0
        ):
            previous_row = pre_shot_df.iloc[i - 1]

            if is_redundant_puck_control(
                previous_row,
                row
            ):
                continue

        # PuckControl
        if (
            show_puck_control
            and row["EventType"] == "PuckControl"
        ):
            rink.wavy_arrow(
                data=event_df,
                x="EventStartX_ft",
                y="EventStartY_ft",
                x2="EventEndX_ft",
                y2="EventEndY_ft",
                head_width=2,
                length_includes_head=True,
                color=puck_control_color,
                alpha=0.75,
                ax=ax
            )

        # Pass
        elif (
            show_passes
            and row["EventType"] == "Pass"
        ):
            rink.arrow(
                data=event_df,
                x="EventStartX_ft",
                y="EventStartY_ft",
                x2="EventEndX_ft",
                y2="EventEndY_ft",
                head_width=0,
                length_includes_head=True,
                color=pass_color,
                alpha=1,
                ax=ax
            )

        # Shot
        elif row["EventType"] == "Shot":
            rink.scatter(
                data=event_df,
                x="EventStartX_ft",
                y="EventStartY_ft",
                s=260,
                marker="*",
                color="gold",
                edgecolors="black",
                zorder=7,
                ax=ax
            )

    # --------------------------------------------
    # Spielerpositionen sammeln
    # --------------------------------------------
    attacking_positions_df = collect_team_positions(
        pre_shot_df=pre_shot_df,
        target_team=attacking_team
    )

    defending_positions_df = collect_team_positions(
        pre_shot_df=pre_shot_df,
        target_team=defending_team
    )

    # --------------------------------------------
    # Goalies herausfiltern
    # --------------------------------------------
    attacking_positions_df = attacking_positions_df[
        ~attacking_positions_df["player_id"].isin(
            _as_id_set(attacking_goalie_ids)
        )
    ].copy()

    defending_positions_df = defending_positions_df[
        ~defending_positions_df["player_id"].isin(
            _as_id_set(defending_goalie_ids)
        )
    ].copy()

    # --------------------------------------------
    # Trails zeichnen
    # --------------------------------------------
    if show_attacker_trails:
        draw_team_trails(
            ax=ax,
            team_df=attacking_positions_df,
            color=attacker_color,
            visible_until_frame=attacker_frame
        )

    if show_defender_trails:
        draw_team_trails(
            ax=ax,
            team_df=defending_positions_df,
            color=defender_color,
            visible_until_frame=defender_frame
        )

    # --------------------------------------------
    # Start- und Endpolygon
    # --------------------------------------------
    first_frame = defending_positions_df["frame"].min()
    last_frame = defending_positions_df["frame"].max()

    initial_defenders = defending_positions_df[
        defending_positions_df["frame"] == first_frame
    ]

    final_defenders = defending_positions_df[
        defending_positions_df["frame"] == last_frame
    ]

    if show_initial_polygon:
        draw_structure_polygon(
            ax=ax,
            frame_df=initial_defenders,
            color=initial_polygon_color,
            alpha=0.1,
            linewidth=1.5,
            linestyle="--"
        )

    if show_final_polygon:
        draw_structure_polygon(
            ax=ax,
            frame_df=final_defenders,
            color=final_polygon_color,
            alpha=0.25,
            linewidth=2.5,
            linestyle="-"
        )

    # --------------------------------------------
    # Shot bestimmen
    # --------------------------------------------
    shot_rows = pre_shot_df[
        pre_shot_df["EventType"] == "Shot"
    ]

    shot_row = (
        shot_rows.iloc[-1]
        if not shot_rows.empty
        else pre_shot_df.iloc[-1]
    )

    shooter = shot_row.get(
        "EventPrimaryPlayerName",
        "Unknown shooter"
    )

    shot_result = shot_row.get(
        "ShotResult",
        "Unknown result"
    )

    if pd.isna(shot_result):
        shot_result = "Unknown result"

    # --------------------------------------------
    # Legende
    # --------------------------------------------
    legend_elements = [
        Line2D(
            [0], [0],
            color=attacker_color,
            linewidth=2.5,
            label="Attacker movement / puck actions"
        ),
        Line2D(
            [0], [0],
            color=defender_color,
            linewidth=2.5,
            label="Defender movement"
        ),
        Line2D(
            [0], [0],
            marker="*",
            linestyle="None",
            markerfacecolor="gold",
            markeredgecolor="black",
            markersize=14,
            label=f"Shot – {shot_result}"
        )
    ]

    ax.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        title="Legend"
    )

    # --------------------------------------------
    # Titel
    # --------------------------------------------
    ax.set_title(
        f"Pre-shot sequence | "
        f"Frames {pre_shot_df.index.min()}–{pre_shot_df.index.max()} | "
        f"Shooter: {shooter} | "
        f"{event_position}"
    )

    return fig
