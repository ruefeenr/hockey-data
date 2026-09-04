import pandas as pd
import streamlit as st
import hockey_rink as hr
import matplotlib.pyplot as plt
import io



###############################################
################ Utils
###############################################

def import_prep_data(file, player_list):
    """

    :param file: input file (excel)
    :param player_list: list of defensive players (1 to 12) / list of which players movements to retrieve
    :return: df with play items.
    """

    structure_df = pd.read_csv(f"./Input Materials/csv/{file}")

    #structure_df= structure_df[-10:]

    #Split Start, End coords of event
    structure_df[['EventStartX', 'EventStartY']] = (structure_df['EventStartCoordinate'].str.split(',', expand=True).astype(float))
    structure_df[['EventEndX', 'EventEndY']] = (structure_df['EventEndCoordinate'].str.split(',', expand=True).astype(float))
    ## convert coords into feet
    structure_df[['EventEndX']] = structure_df[['EventEndX']]*3.28084
    structure_df[['EventEndY']] = structure_df[['EventEndY']]*3.28084
    structure_df[['EventStartX']] = structure_df[['EventStartX']]*3.28084
    structure_df[['EventStartY']] = structure_df[['EventStartY']]*3.28084

    # split defensive player coords (home team is defence in this scenario - players 7 to 11)

    for i in player_list:
        structure_df[[f'Player{i}X', f'Player{i}Y']] = (structure_df[f'StartPlayerCoordinates{i}'].str.split(',', expand=True).astype(float))
    # convert player coords into feet
    for i in player_list:
        structure_df[[f'Player{i}X']] = structure_df[[f'Player{i}X']]*3.28084
        structure_df[[f'Player{i}Y']] = structure_df[[f'Player{i}Y']]*3.28084

    return structure_df


scenario_df = import_prep_data("canada_v_hcd/1.csv", [1,2,3,4,5])

## plot
def plot_basic(structure_df, players):
    """
    :param structure_df:
    :param players: list of players on the defensive side. usually 7-11
    :param orientation: either "defence" or "offence"
    :return:
    """

    rink = hr.IIHFRink()
    ax = rink.draw(
        #display_range=orientation,
        figsize=(20, 8))

    rink.wavy_arrow(
        data=structure_df[structure_df["EventType"] == "PuckControl"],
        x="EventStartX",
        y="EventStartY",

        x2="EventEndX",
        y2="EventEndY",
        # facecolor="purple", edgecolor="black",
        head_width=2, length_includes_head=True,
    )

    rink.arrow(
        data=structure_df[structure_df["EventType"] == "Pass"],
        x="EventStartX",
        y="EventStartY",

        x2="EventEndX",
        y2="EventEndY",
        # facecolor="purple", edgecolor="black",
        head_width=2, length_includes_head=True,
    )

    rink.scatter(
        data=structure_df[structure_df["EventType"] == "Shot"],
        x="EventStartX",
        y="EventStartY",
        color="yellow",
        s=100,
        edgecolor="black"
    )
    # plot defensive players
    for i in players:
        rink.scatter(
            data=structure_df,
            x=f'Player{i}X',
            y=f'Player{i}Y'
        )

    return ax.figure


###############################################
################ Streamlit Display
###############################################

st.markdown("""
            # Finding Hockey Strategies with Data
            Authors: **Enrique Rüfenacht & Benjamin Jud**  
              
            Sports Data Science  
            Hochschule Luzern
            2026-09-04  
            
            [GitHub Repo](https://github.com/ruefeenr/hockey-data)  
            
            AI Disclosure:
            -----
            ### Background + Objective:  
            
            -----
            ## Data Preprocessing
            Data is generated from the Wisesport through their [Wisehockey platform](https://wisesport.com/hockey/), and provided to use by [HC Davos](https://www.hcd.ch/de/hockey-club-davos-startseite).
            A CSV file contains each action which occurs throughout the game, in a log style format. Data is ingested using a Pandas DataFrame object.          
""")
st.code("""
        csv_full = pd.read_csv("rawData/rawData/canada_v_hcd.csv")
""")

sample_data_df = pd.read_csv("./Input Materials/rawData/canada_v_hcd.csv")
sample_data_df[0:20]

st.markdown("""
            The events data file details what type of event occured, timestamps, event location details, and information on all players on the ice at the time of the event.
            
            ### Filtering
            In particular, this project aims to extract valuable insights which occur during the Powerplay (when one team commits a foul, and has to play with one player fewer), 
            and in scenarios where a 'structure' has been setup.     
            
            In the context of this project, a structure is defined as a series of plays when the following occurs:
            - A powerplay is occuring
            - The puck is in the offensive zone for continous duration of at least 5 seconds, without leaving the zone.
            - If the play is stopped and a faceoff occurs, the five-second duration is reset.
            
            First, the raw CSV event file is filtered to contain only events occuring during a powerplay. Note that events for a Home and Away team powerplay are seperately listed.
            """)

st.code("""
data = csv_full[
    (csv_full["TeamStrengthType"] == "AwayPowerplay") | 
    (csv_full["TeamStrengthType"] == "HomePowerplay")
    ]
""")

st.markdown("""
            Next, we select the rows within our dataset which correspond to shots - these for the basis of our analysis, and act as a way to search for events which would be useful for viewers to gain insight from.
            Ideally, we would only analyze moments of structure which result in a goal, however, in the three match datasets which we have access to, this scenario does not occur.
""")

st.code("""
shot_rows = data[data["EventType"] == "Shot"]
shot_rows = shot_rows.index
shot_rows = shot_rows.tolist()
""")

st.markdown(
    """
    Next, we define a series of adjustable parameters:
    - `n_seconds` defines how many seconds from the occurance of a shot the current structure goes. 
    - `scenario_number` defines a starting value when exporting scenarios as a csv. 
    - `game_name` defines a prefix to the scenario number when saving scenarios as csv.
    
    The below code snipped will process each shot to see whether it fits the scenario, and if it does, export it to csv format.
    """
)

st.code("""
for single_shot in shot_rows:       # reviews each shot which occurs during powerplay.
    clock_at_shot = data.loc[single_shot, "MatchClock"]
    period = data.loc[single_shot, "Period"]
    play_data = data[(data["MatchClock"] >= clock_at_shot - n_seconds) & (data["MatchClock"] <= clock_at_shot) & (data["Period"] == period)] #accesses data which occurs n_seconds prior to shot event.

    if ("BluelineCrossing" in play_data["EventType"].values) | ("Faceoff" in play_data["EventType"].values): #removes scenarios which break structure rules.
        print("found BluelineCrossing or Faceoff. No export")
        continue

    else:
        play_data.to_csv(f"autoparse_csv/{game_name}_shotData{scenario_number}.csv") #exports scenarios which fit structure rules.
        print(f"Exported Scenario {scenario_number} to CSV")
        scenario_number = scenario_number+1
""")

st.markdown(
    """
        ## Initial Visualisation
        Throughout this project, we project player data using the `hockey_rink` package. A rink is easily displayed using:
""")

st.code("""
rink = hockey_rink.IIHFRink()
rink.draw()
plt.show()
""")

rink = hr.IIHFRink()
ax = rink.draw()
st.pyplot(ax.figure)

st.markdown(
    """
        ### Basic Visualisation
        We can now import a scenario, clean it, then project it on our rink plot. This scenario is from the Canada vs. HC Davos game at the 2024 Spengler Cup.
""")

ax = rink.draw(
    #display_range="defence", rotation=90
    )

rink.arrow(
    data=scenario_df[scenario_df["EventType"] == "PuckControl"],
    x="EventStartX",
    y="EventStartY",

    x2="EventEndX",
    y2="EventEndY",
    # facecolor="purple", edgecolor="black",
    head_width=2, length_includes_head=True,
)
rink.scatter(
    data=scenario_df[scenario_df["EventType"] == "Shot"],
    x="EventStartX",
    y="EventStartY",
    color = "purple",
    s=100
)
png = io.BytesIO()
ax.figure.savefig(png, format="png", dpi=300)

st.pyplot(ax.figure)

st.markdown("""
Next, we plot defensive players (as dots on the ice), passes (as straight lines) and puck movement (as wavy lines).
This is the same scenario as above, just with additional data.
""")

img = plot_basic(scenario_df, [1,2,3,4,5])
st.pyplot(img)




st.markdown("""
        ------
        ## Sections to write
        - preprocessing steps
            - filtering
            - seperating coords & converting into ft, player name & number (as variable)
        - Initial data vis
            - rink package
        - Feedback from HcDavos
        - Final data viz
            - gallery with plots
            - tactical explaination of what happened, how this can be used for exaimination.
        - steps which we took which were incorrect (thought process)
            - weird preprocessing method (with between blueline filtering)
            - How we attempted positions without history (mass defence plots)
            - Puckcontrol vs. pass
            - directions
        - Unknowns and future steps
        - Conclusion 

""")


uploaded_file = st.file_uploader("Choose a file")
if uploaded_file is not None:
    dataframe = pd.read_csv(uploaded_file)
    st.write(dataframe)

st.download_button(
    label="Download Image",
    data=png,
    file_name="figure.png",
    mime="image/png",
    icon=":material/download:",
)