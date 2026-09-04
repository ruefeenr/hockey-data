import pandas as pd

POWERPLAY_STRENGTHS = ("5v4", "4v5")

# Events, die eine zusammenhängende Angriffsstruktur unterbrechen
BREAKING_EVENTS = ("BluelineCrossing", "Faceoff")


def filter_powerplay(csv_full):
    return csv_full[csv_full["TeamStrength"].isin(POWERPLAY_STRENGTHS)]


def list_shots(data):
    """Alle Powerplay-Schüsse. Die Liste hängt nicht von der Fensterlänge ab."""

    return data[data["EventType"] == "Shot"].index.tolist()


def scenario_window(data, shot_index, n_seconds):
    """
    Fenster der n Sekunden vor einem Schuss.

    Liegt darin ein Faceoff oder BluelineCrossing, beginnt das Fenster
    direkt danach, statt weiter zurückzureichen.
    """

    clock_at_shot = data.loc[shot_index, "MatchClock"]
    period = data.loc[shot_index, "Period"]

    window = data[
        (data["MatchClock"] >= clock_at_shot - n_seconds)
        & (data["MatchClock"] <= clock_at_shot)
        & (data["Period"] == period)
    ]

    # Nur Brüche vor dem Schuss sind relevant, das Fenster kann durch die
    # Sekundenauflösung der MatchClock auch Zeilen danach enthalten
    before_shot = window.iloc[:window.index.get_loc(shot_index)]

    breaks = before_shot[before_shot["EventType"].isin(BREAKING_EVENTS)]

    if not breaks.empty:
        last_break = before_shot.index.get_loc(breaks.index[-1])
        window = window.iloc[last_break + 1:]

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
