import io

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import parsing
import preshot

st.set_page_config(page_title="Pre-Shot Situation", layout="wide")


# Nur das Einlesen wird gecacht. Alles Weitere kostet zusammen unter 0.2 s und
# steckt in preshot.py und parsing.py - deren Änderungen erkennt st.cache_data
# nicht, gecachte Zwischenergebnisse wären dort also still veraltet.
@st.cache_data
def read_match_csv(file_bytes):
    return pd.read_csv(io.BytesIO(file_bytes))


st.title("Pre-Shot Situation")

uploaded = st.file_uploader("Match-CSV", type="csv")

if uploaded is None:
    st.info("Lade ein ganzes Spiel-CSV hoch, um die Szenarien zu parsen.")
    st.stop()

data = parsing.filter_powerplay(read_match_csv(uploaded.getvalue()))
shots = parsing.list_shots(data)

if not shots:
    st.warning(
        "Keine Powerplay-Schüsse gefunden "
        f"({' / '.join(parsing.POWERPLAY_STRENGTHS)})."
    )
    st.stop()

labels = {
    shot_index: parsing.scenario_label(number, data.loc[shot_index])
    for number, shot_index in enumerate(shots, start=1)
}

st.sidebar.header("Szenario")

shot_index = st.sidebar.selectbox(
    "Schuss",
    options=shots,
    format_func=labels.get,
    key="shot_index"
)

n_seconds = st.sidebar.slider(
    "Sekunden vor dem Schuss",
    min_value=1,
    max_value=15,
    value=5,
    step=1
)

pre_shot_df = preshot.prepare_shot_data(
    parsing.scenario_window(data, shot_index, n_seconds)
)

goalies = preshot.detect_goalies(preshot.prepare_shot_data(data))

attacking_team, defending_team = preshot.get_powerplay_teams(
    pre_shot_df.iloc[0]["strength_type_state"]
)

attacking_goalie_ids = goalies.get(attacking_team, set())
defending_goalie_ids = goalies.get(defending_team, set())

# Das Fenster wird an einem Faceoff oder BluelineCrossing abgeschnitten,
# die tatsächliche Länge kann darum kürzer als der Regler sein
covered_seconds = int(
    pre_shot_df["MatchClock"].max() - pre_shot_df["MatchClock"].min()
)

window_text = f"{covered_seconds} s"

if covered_seconds < n_seconds:
    window_text += f" (von {n_seconds} s, am Strukturbruch gekürzt)"

st.caption(
    f"{uploaded.name} – {len(shots)} Powerplay-Schüsse – "
    f"Fenster {window_text}, {len(pre_shot_df)} Events"
)

if not defending_goalie_ids:
    st.warning(
        "Für das verteidigende Team wurde kein Torhüter erkannt. "
        "Die Polygone bleiben leer, wenn dadurch mehr als vier Spieler übrig bleiben."
    )

# --------------------------------------------
# Toggle Buttons für Visualisierung
# --------------------------------------------
st.sidebar.header("Anzeige")

show_passes = st.sidebar.checkbox("Passes", value=True)
show_puck_control = st.sidebar.checkbox("PuckControl", value=True)
show_attacker_trails = st.sidebar.checkbox("Attacker trails", value=True)
show_defender_trails = st.sidebar.checkbox("Defender trails", value=True)
show_initial_polygon = st.sidebar.checkbox("Start polygon", value=True)
show_final_polygon = st.sidebar.checkbox("Shot polygon", value=True)

# --------------------------------------------
# Slider für sichtbaren Spielerverlauf
# --------------------------------------------
st.sidebar.header("Frames")

min_frame = int(pre_shot_df.index.min())
max_frame = int(pre_shot_df.index.max())

# Der Frame-Bereich hängt an der Fensterlänge, darum ein eigener
# Slider-State je Schuss und Sekundeneinstellung
slider_suffix = f"{shot_index}_{n_seconds}"

attacker_frame = st.sidebar.slider(
    "Attacker frame",
    min_value=min_frame,
    max_value=max_frame,
    value=max_frame,
    step=1,
    key=f"attacker_frame_{slider_suffix}"
)

defender_frame = st.sidebar.slider(
    "Defender frame",
    min_value=min_frame,
    max_value=max_frame,
    value=max_frame,
    step=1,
    key=f"defender_frame_{slider_suffix}"
)

fig = preshot.plot_pre_shot_summary(
    pre_shot_df=pre_shot_df,
    attacking_goalie_ids=attacking_goalie_ids,
    defending_goalie_ids=defending_goalie_ids,
    show_passes=show_passes,
    show_puck_control=show_puck_control,
    show_attacker_trails=show_attacker_trails,
    show_defender_trails=show_defender_trails,
    show_initial_polygon=show_initial_polygon,
    show_final_polygon=show_final_polygon,
    attacker_frame=attacker_frame,
    defender_frame=defender_frame
)

st.pyplot(fig)

png = io.BytesIO()
# ohne bbox_inches wird die ausserhalb der Achse platzierte Legende abgeschnitten
fig.savefig(png, format="png", dpi=300, bbox_inches="tight")
plt.close(fig)

st.download_button(
    label="Grafik als PNG",
    data=png,
    file_name=f"preshot_{shot_index}.png",
    mime="image/png",
    icon=":material/download:"
)

with st.expander("Debug"):
    display_range, rotation, event_position = preshot.get_rink_view(pre_shot_df)

    st.write(
        {
            "Shot index": shot_index,
            "EventPosition": event_position,
            "Display range": display_range,
            "Rotation": rotation,
            "Attacking team": attacking_team,
            "Defending team": defending_team,
            "Attacking goalies": sorted(attacking_goalie_ids),
            "Defending goalies": sorted(defending_goalie_ids),
        }
    )

    st.dataframe(pre_shot_df)

    st.download_button(
        "Szenario als CSV",
        data=pre_shot_df.to_csv().encode("utf-8"),
        file_name=f"shotData_{shot_index}.csv",
        mime="text/csv"
    )
