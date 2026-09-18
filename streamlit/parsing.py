import pandas as pd

POWERPLAY_STRENGTHS = ("5v4", "4v5")

# Team, das beim jeweiligen TeamStrengthType in Überzahl spielt
POWERPLAY_TEAMS = {
    "HomePowerplay": "Home",
    "AwayPowerplay": "Away"
}

# Events, die eine zusammenhängende Angriffsstruktur unterbrechen
BREAKING_EVENTS = ("BluelineCrossing", "Faceoff")

# PuckControlState-Werte, bei denen ein Team den Puck wirklich führt.
# "Loose" und "Contested" sind Zweikämpfe innerhalb eines Angriffs.
TEAM_CONTROL_STATES = ("HomeControl", "AwayControl")


def filter_powerplay(csv_full):
    return csv_full[csv_full["TeamStrength"].isin(POWERPLAY_STRENGTHS)]


def list_shots(data):
    """
    Alle Powerplay-Schüsse des Teams in Überzahl.

    Auch das Unterzahl-Team schiesst, im Testspiel immerhin bei sechs von 26
    Schüssen. Solche Konter laufen in die andere Richtung und passen nicht zu
    den Rollen, die die Visualisierung dem Powerplay-Team zuweist.

    Die Liste hängt nicht von der Fensterlänge ab.
    """

    shots = data[data["EventType"] == "Shot"]

    powerplay_team = shots["TeamStrengthType"].map(POWERPLAY_TEAMS)

    return shots[shots["EventPrimaryTeam"] == powerplay_team].index.tolist()


def last_possession_gain(window, powerplay_team):
    """
    Position der letzten Puckeroberung des Teams in Überzahl.

    Ein Angriff beginnt dort, wo das Powerplay-Team den Puck vom Gegner
    zurückholt. Lose und umkämpfte Pucks zählen bewusst nicht als Wechsel,
    sonst würde jeder Abpraller im eigenen Cycle das Fenster abschneiden.

    None, wenn im Fenster kein Wechsel zu sehen ist. Der Zustand vor dem
    Fenster ist unbekannt, die erste Besitzzeile gilt darum nie als Eroberung.
    """

    control = window["PuckControlState"]
    control = control.where(control.isin(TEAM_CONTROL_STATES))

    own_control = f"{powerplay_team}Control"

    # Besitz steht nur auf PuckControl-Zeilen, dazwischen liegen Pässe und
    # Crossings. Der vorherige Zustand kommt darum von der letzten Zeile, die
    # überhaupt einen Besitz ausweist, nicht von der direkten Vorzeile.
    previous = control.ffill().shift()

    gains = (
        (control == own_control)
        & previous.notna()
        & (previous != own_control)
    )

    if not gains.any():
        return None

    return window.index.get_loc(gains[gains].index[-1])


def scenario_window(data, shot_index, n_seconds):
    """
    Fenster der n Sekunden vor einem Schuss.

    Liegt darin ein Faceoff, ein BluelineCrossing oder eine Puckeroberung des
    Powerplay-Teams, beginnt das Fenster direkt dort, statt weiter
    zurückzureichen.
    """

    clock_at_shot = data.loc[shot_index, "MatchClock"]
    period = data.loc[shot_index, "Period"]

    powerplay_team = POWERPLAY_TEAMS.get(
        data.loc[shot_index, "TeamStrengthType"]
    )

    window = data[
        (data["MatchClock"] >= clock_at_shot - n_seconds)
        & (data["MatchClock"] <= clock_at_shot)
        & (data["Period"] == period)
    ]

    # MatchClock zählt in ganzen Sekunden. Ohne diesen Schnitt reicht das
    # Fenster bis ans Ende der Schusssekunde und nimmt Abpraller und
    # Puckübernahmen mit, die dann die Endpositionen und das Schuss-Polygon
    # bestimmen.
    window = window.iloc[:window.index.get_loc(shot_index) + 1]

    # Der Schuss selbst kann kein Bruch sein
    before_shot = window.iloc[:-1]

    breaks = before_shot[before_shot["EventType"].isin(BREAKING_EVENTS)]

    if not breaks.empty:
        last_break = before_shot.index.get_loc(breaks.index[-1])
        window = window.iloc[last_break + 1:]

    # Nach dem Strukturbruch, damit von beiden Grenzen die spätere gewinnt
    if powerplay_team is not None:
        gain = last_possession_gain(
            window.iloc[:-1],
            powerplay_team
        )

        if gain is not None:
            window = window.iloc[gain:]

    return window


def scenario_label(number, shot_row):
    """Baut ein Dropdown-Label wie '3. P2 17:20 - #19 Jesper Olofsson - Blocked'."""

    period = shot_row.get("Period")
    period_text = f"P{int(period)}" if pd.notna(period) else "P?"

    clock = shot_row.get("MatchClock")
    if pd.notna(clock):
        clock = int(clock)
        clock_text = f"{clock // 60:02d}:{clock % 60:02d}"
    else:
        clock_text = "--:--"

    shooter = shot_row.get("EventPrimaryPlayerName")
    if pd.isna(shooter):
        shooter = "Unknown shooter"

    shot_result = shot_row.get("ShotResult")
    if pd.isna(shot_result):
        shot_result = "Unknown result"

    return f"{number}. {period_text} {clock_text} - {shooter} - {shot_result}"
