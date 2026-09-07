import pandas as pd
import streamlit as st
import hockey_rink as hr
import matplotlib.pyplot as plt
import io
import datetime

start_time = datetime.datetime.now()

###############################################
################ Utils
###############################################
@st.cache_data
def import_prep_data(file, player_list):
    """

    :param file: input file (excel)
    :param player_list: list of defensive players (1 to 12) / list of which players movements to retrieve
    :return: df with play items.
    """

    structure_df = pd.read_csv(file)

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

## plot
@st.cache_data
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

scenario_df = import_prep_data("autoparse_csv/canada_v_hcd_shotData1.csv", [1,2,3,4,5])

###############################################
################ Streamlit Display
###############################################

st.markdown("""
            # Finding Hockey Strategies with Data
            Authors: **Enrique Rüfenacht & Benjamin Jud**  
              
            Sports Data Analytics - FS2026    
            Instructor: **Martin Rumo**  
            Hochschule Luzern  
            2026-09-04 :blue-badge[Update prior to submission]  
            
            [GitHub Repo](https://github.com/ruefeenr/hockey-data) - run interactive Streamlit app with `streamlit run streamlit/app.py` from project directory.
            
            -----
            ### Background + Objective:  
""") ## Intro Page up to glossary

with st.expander("Glossary / Terms"):
    st.markdown("""
    - **Structure:** A structure, as defined in this project, refers to moments when the offensive team has established control in the offensive zone, and puck control remains uncontested by the opponent.
         - Conditions: 
            - A powerplay is occuring
            - The puck is in the offensive zone for continous duration of at least 5 seconds, without leaving the zone.
            - If the play is stopped and a faceoff occurs, the five-second duration is reset.
    - **General Ice Hockey Terminology:** Wikipedia: [Glossary of ice hockey terms](https://en.wikipedia.org/wiki/Glossary_of_ice_hockey_terms)
    """) ## glossary expander

st.markdown("""
            ### Objective:
            The objective of this project is to provide a non-technical analysis tool for use by coaches or team analysts.
            The primary focus is to identify defensive structures during a powerplay, and what offensive structures were used to create quality goal-scoring opportunities.
            Additional sub-objectives include data processing and a scenario detection algorithm to decrease time or manual effort required to detect scenarios with useful information. 

            #### Defensive structures (provided by HC Davos):
            HC Davos provided three different primary penalty kill defensive structure which is in use throughout the National League. These structures can be visualized through the analysis tool.
            - **Box:** the box structure is the classic penalty kill defensive structure historically used. It aims to protect inside ice between the faceoff dots from attacks, and forces attackers to play from the outside.
            As plays move to the left or right of the ice, the entire box structure moves in unison.
""") ## md box defensive structure
st.image("images/pk_box_crop.png", caption="A traditional box penalty kill formation")

st.markdown("""
            - **Diamond:** the diamond structure works very similar to the box structure in principal. The goal is to protect the center of the ice from cross-ice passes or direct attacks.
            The structure additionally places players near prime shooting locations, and has a dedicated player in front of the net to clear rebounds. 
            While only two teams employed this strategy in the previous season, it is proven enormously successful and is likely to be the leading penalty kill structure this season.
""") ## md diamond defensive structure
st.image("images/pk_diamond_crop.png", caption="A diamond penalty kill formation")

st.markdown("""
            - **Pushdown Triangle:** this formation places a triangle to protect the inside, with a floating point man to chase the puck and give pressure to offensive playmakers.
            The floating player rotates with the play, and the top player within the triangle pushes up and takes the role of the floating player. In the '25/'26 season, this was the most used structure with teams throughout the National League.
""") ## md 3+1 defensive structure
st.image("images/pk_pushdown_crop.png", caption="A triangular pushdown or 3+1 formation.")


st.markdown("""
            -----
            ## Data Preprocessing 
            Data is generated from the Wisesport through their [Wisehockey platform](https://wisesport.com/hockey/), and provided to this project for use by [HC Davos](https://www.hcd.ch/de/hockey-club-davos-startseite).
            A CSV file contains each action which occurs throughout the game, in a log style format. Data is ingested using a Pandas DataFrame object.   
""")# Data preprocessing

st.code("""
sample_data_df = pd.read_csv("csv/canada_v_hcd/canada_v_hcd.csv")
sample_data_df[0:20]
""")
sample_data_df = pd.read_csv("csv/canada_v_hcd/canada_v_hcd.csv")
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
            """) #filtering md

st.code("""
data = csv_full[
    (csv_full["TeamStrengthType"] == "AwayPowerplay") | 
    (csv_full["TeamStrengthType"] == "HomePowerplay")
    ]
""") #filtering code

st.markdown("""
            Next, we select the rows within our dataset which correspond to shots - these for the basis of our analysis, and act as a way to search for events which would be useful for viewers to gain insight from.
            Ideally, we would only analyze moments of structure which result in a goal, however, in the three match datasets which we have access to, this scenario does not occur.
""")

st.code("""
shot_rows = data[data["EventType"] == "Shot"]
shot_rows = shot_rows.index
shot_rows = shot_rows.tolist()
""") #shot rows

st.markdown("""
    Next, we define a series of adjustable parameters:
    - `n_seconds` defines how many seconds from the occurance of a shot the current structure goes. 
    - `scenario_number` defines a starting value when exporting scenarios as a csv. 
    - `game_name` defines a prefix to the scenario number when saving scenarios as csv.
    
    The below code snipped will process each shot to see whether it fits the scenario, and if it does, export it to csv format.
    """) # params md

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
""") # code parsing full game

st.markdown("""
        ## Initial Visualisation
        Throughout this project, we project player data using the `hockey_rink` package. A rink is easily displayed using:
""") ## md inital viz

st.code("""
rink = hockey_rink.IIHFRink()
rink.draw()
plt.show()
""") #code inital viz

rink = hr.IIHFRink()
ax = rink.draw()
st.pyplot(ax.figure)

st.markdown("""
        ### Basic Visualisation
        We can now import a scenario, clean it, then project it on our rink plot. This scenario is from the Canada vs. HC Davos game at the 2024 Spengler Cup.
""") # basic visualization

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
    s=140
)

st.pyplot(ax.figure)

st.markdown("""
Next, we plot defensive players (as dots on the ice), passes (as straight lines) and puck movement (as wavy lines).
This is the same scenario as above, just with additional data.
""") #md describe more advanced plot with people on it. Maybe find a better scenario? or make the people bigger?

@st.cache_data
def img_plot_more_players():
    img = plot_basic(scenario_df, [1, 2, 3, 4, 5])
    return img

st.pyplot(img_plot_more_players())

st.markdown("""
        ### Intermediate Data Visualization
        :red-badge[TODO] More advanced viz with box structure & such.
""") # More advanced viz with box & such

st.markdown("""
        ## Feedback from HC Davos
""") #md feedback from HC Davos

st.markdown("""
        ## Final Data Visualization
        :red-badge[TODO] Can import the code from App or take the screenshots.
""") # Final Data Visualization

st.markdown("""
        ## Incorrect Steps
        Throughout this project, several times, we persued avenues which we later found were incorrect steps. 
        These scenarios helped us further develop our model, our method, and ways in which we present analysis of a single scenario.
        
        ### Scenario Discovery Algorithm
        One of the key targets of this project was to develop an automated method to turn the event model of an entire game into indiviual structured events which are useful for a coach to review for their teams' performance.
        The definition of when a structure is achieved did not change, but the methodology did.  
        
        We knew that a structure could only occur when the play was in the attacking zone. The `EventType` parameter includes the event `BluelineCrossing`, which occurs whenever the puck crosses the blueline. 
        To develop the model, it was assumed that data occuring between the blueline could be counted as "bookends", and that events that occured between blueline crossings could be counted as structure. 
        After testing, edge cases were found where the model selected incorrect data. 
        Edge cases that were found included when a powerplay ends while the attacking team is in the zone, or when a stoppage of play occurs (such as when the puck goes out of bounds or is stopped by the goaltender).
        
        ### Mass Player Plotting
        In an attempt to visualize the defensive structures (Diamond, Box, Pushdown triangle), early plots incorporated the positions of each defensive player, during each event frame.
        The goal was to show the viewer where players were positioned, what formation they took up, and how the offensive team was able to work against the structure to take a shot.

""") ## incorrect steps
st.image("images/mass_player_plotting.png", caption="An early attempt at plotting a structure scenario, including all defensive players.")

st.markdown("""
         As is visible in the above example, and in particular across longer events, there are too many points for a reader to follow which structure is employed by the defensive team.
         As the puck and play shifts from one side of the ice to the other, the entire defensive structure moves along with it. As a result, this plotting method resulted in overlapping points, which do not tell a conlcusive story.
         The method outlined to solve this issue is multifold: 
         - A light opacity polygon connects all defensive players, to outline the defensive structure. It can show both the structure at the start and end of the play.
         - Player positioning dots are connected using solid lines, in increasing opacity, which effectively plots an additional time dimension. The audience, as a result of this, can now see how the play developed over time through the movement of the puck and players.
""") ## md mass player plotting 2


st.markdown("""
        ### Directional Arrows
        During the intermediate stage of the project, we felt that adding directional arrows to player movements would give an additional dimmension of details about the actions players took throughout the play. 
        Once implemented, the team came to the conclusion that the arrows did not add addititional useful information to the scenario, but rather added to clutter and disorganization that made the diagram harder to read.
        Additionally, if a player stood still or multiple lines are captured for a single moment, arrows for a player would overlap. On occasion, some data points did not include directional data for some or all players, leading to a unconsistent visual.
        
        Example:   
        """) ## md directional arrows

st.image(
 "images/improvements-arrows.png",
"Scenario with the inclusion of directional arrows for each player"
) ## arrows image

st.markdown("""
        ## Unknowns & Future Steps :red-badge[ToDo]
""")

st.markdown("""
        ## Conclusion :red-badge[ToDo]
""")



st.markdown("""
            ### AI Disclosure:
            Throughout this project, artificial intelligence was used for the purposes of code troubleshooting and code completion. 
            AI was also used to converting existing (handwritten) code from the interactive Jupyter format into the interactive Streamlit format. 
            Lastly, AI was used to automatically generate a ReadMe file for the GitHub repo.
""")

st.markdown("""
        ------
        ## Sections to write
        - Background / Objectives :green-badge[Done]
        - preprocessing steps :red-badge[TODO]
            - filtering :green-badge[Done]
            - seperating coords & converting into ft, player name & number (as variable) :red-badge[TODO]
        - Initial data vis :green-badge[Done]
            - rink package :green-badge[Done]
        - Feedback from HcDavos :red-badge[TODO]
        - Final data viz :red-badge[TODO]
            - gallery with plots
            - tactical explaination of what happened, how this can be used for exaimination.
        - steps which we took which were incorrect (thought process) :yellow-badge[In-Progress]
            - weird preprocessing method (with between blueline filtering) :green-badge[Done]
            - How we attempted positions without history (mass defence plots) :green-badge[Done]
            - Puckcontrol vs. pass
            - directions :green-badge[Done]
        - Unknowns and future steps :red-badge[TODO]
        - Conclusion :red-badge[TODO]

""")

load_time = datetime.datetime.now() - start_time
f"Load time: {load_time.seconds}s"