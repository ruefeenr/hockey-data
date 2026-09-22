import pandas as pd
import streamlit as st
import hockey_rink as hr
import matplotlib.pyplot as plt
import io
import datetime
from pathlib import Path

start_time = datetime.datetime.now()

# report.py lives in streamlit/; match CSVs, images and scenario exports
# sit at the repo root (data/, images/, work/autoparse_csv/).
ROOT = Path(__file__).resolve().parent.parent

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

scenario_df = import_prep_data(ROOT / "work/autoparse_csv/canada_v_hcd_shotData1.csv", [1,2,3,4,5])

###############################################
################ Streamlit Display
###############################################

## streamlit sidebar
st.sidebar.markdown("""
    **Table of Contents**
    - [Objective](#objective)
        - [Defensive Structures](#defensive-structures-provided-by-hc-davos)
    - [Data Preprocessing](#data-preprocessing)
        - [Filtering](#filtering)
    - [Visualization](##visualisation)
        - [Basic Visualization](#basic-visualisation)
        - [Advanced Visuals](#advanced-visuals)
        - [Incorporation of Interactive Elements](#incorporation-of-interactive-elements)
        - [Feedback from HC Davos](#feedback-from-hc-davos)
    - [Incorrect Steps](#incorrect-steps)
        - [Scenario Discovery Algorithm](#scenario-discovery-algorithm)
        - [Mass Player Plotting](#mass-player-plotting)
        - [Directional Arrows](#directional-arrows)
    - [Future Steps](#future-steps)
    - [Conclusion](#conclusion)
    - [AI Disclosure](#ai-disclosure)
        
        
    
""")

st.markdown("""
            # Finding Hockey Strategies with Data
            Authors: **Enrique Rüfenacht & Benjamin Jud**  
              
            Sports Data Analytics - FS2026    
            Instructor: **Martin Rumo**  
            Hochschule Luzern  
            2026-09-22 
            
            [GitHub Repo](https://github.com/ruefeenr/hockey-data) - run interactive Streamlit app with `streamlit run streamlit/app.py` from project directory.  
            [Web App](https://hockey-data-ekm32rc9v2uxnnnpg23vly.streamlit.app/)
            
            -----
            
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
st.image(str(ROOT / "images/pk_box_crop.png"), caption="A traditional box penalty kill formation")

st.markdown("""
            - **Diamond:** the diamond structure works very similar to the box structure in principal. The goal is to protect the center of the ice from cross-ice passes or direct attacks.
            The structure additionally places players near prime shooting locations, and has a dedicated player in front of the net to clear rebounds. 
            While only two teams employed this strategy in the previous season, it is proven enormously successful and is likely to be the leading penalty kill structure this season.
""") ## md diamond defensive structure
st.image(str(ROOT / "images/pk_diamond_crop.png"), caption="A diamond penalty kill formation")

st.markdown("""
            - **Pushdown Triangle:** this formation places a triangle to protect the inside, with a floating point man to chase the puck and give pressure to offensive playmakers.
            The floating player rotates with the play, and the top player within the triangle pushes up and takes the role of the floating player. In the '25/'26 season, this was the most used structure with teams throughout the National League.
""") ## md 3+1 defensive structure
st.image(str(ROOT / "images/pk_pushdown_crop.png"), caption="A triangular pushdown or 3+1 formation.")


st.markdown("""
            -----
            ## Data Preprocessing 
            Data is generated from the Wisesport through their [Wisehockey platform](https://wisesport.com/hockey/), and provided to this project for use by [HC Davos](https://www.hcd.ch/de/hockey-club-davos-startseite).
            A CSV file contains each action which occurs throughout the game, in a log style format. Data is ingested using a Pandas DataFrame object.   
""")# Data preprocessing

st.code("""
sample_data_df = pd.read_csv("data/canada_v_hcd.csv")
sample_data_df[0:20]
""")
# <<<<<<< Updated upstream
sample_data_df = pd.read_csv(ROOT / "data/canada_v_hcd.csv")
#=======
sample_data_df = pd.read_csv("data/canada_v_hcd.csv")
#>>>>>>> Stashed changes
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
        ## Visualisations
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
        ### Advanced Visuals
        Developments in the visualization progressed well, to a point where the team felt that the visualizations were able to provide an informative overview of any single play. Several new, key elements include:
        - **Differentiation between passing and puck movements:** Puck movements are shown in a wavy black arrow, while passes are displayed in solid black lines. Initially, both passes were in a red color, but this was changed to avoid confusion against ice markings.
        - **Shot Location:** The location of the where the shot was taken is marked on the map with a yellow star. Additionally, the legend of the visual provides information on what the result of that shot was - a goal, a save, block, or a miss.
        - **Player Tracks:** Player tracks were added to add an element of time to the visual. For all players, the initial location is plotted with a low opacity (light colored), and as the play progressed, subsequent locations were plotted in with higher opacity values.
            Players are color coded to their team (either purple or green, chosen to avoid clashing against other colored elements of the visual).
            Showing the movements of the players and the puck alike allows the viewer to visually identify how the play evolved, and how players shifted their positions.
        - **Structure Shading:** Shading was implemented to highlight and visually identify the structure of the defensive team for the viewer. Like the player tracks, the shading is time dependant, highlighting the first event frame in the lightest color and the last event frame in the darkest color.
                Plotting the structures from multiple time moments additionally gives the benefit of showing overlapping areas in darker colors, as those are locations which have been under continuous control by the defensive team. This is well shown in example 2.
                This structure was challenging to implement, as the algorithm had to be able to identify which players were relevant to the scenario as the goaltender is always to be excluded.         
        
        **Scenario 1**  
        Scenario 1 shows the defending team likely running a 3+1 pushdown structure. At the start of the sequence, you can see :green[players 24], :green[3], and :green[19] in a triangle formation, with :green[player 86] playing up high. As the sequence evolves, the puck shifts from the left side of the ice to the right. 
        :green[Player 19] takes up the high spot, while :green[86] slides to the right to cover the high center.   
        
""") # Intermediate (final?) dataviz

st.image(str(ROOT / "images/scenario1.jpeg"), caption='Scenario 1')

st.markdown("""
        From the visual, we can also see an interesting opportunity for the offensive team, if :violet[player 46] had not chosen to shoot. Focusing on the left side at the play, attacking :violet[player 44] makes the pass to the point, before slowly sliding into the top of the circle.
        As the puck is moved to the right-hand side of the ice, the :green[defensive] players covering the left side of the ice follow into the center. As we come to the last frame of the play, :violet[player 44] is nicely positioned in a prime shooting location at the top of the circle, with a clear line to receive
        a pass from teammate, :violet[player 46], for a one-timer attempt. Attacking :violet[player 65] is standing by near the goaltender, in a prime position to quickly get to any loose rebounds.  
        
        **Scenario 2:**   
        Scenario 2 shows the defensive team playing a tight box formation. In this scenario, the puck is moved from attacking :violet[player 96] down in the corner to :violet[16], in the point position. :violet[Player 16] skates for several strides, before shooting the puck to the front of the net.
        From analyzing the locations of the players throughout this structure set-up, we can see why :violet[player 16] chose to shoot: attacking :violet[player 19] moves from beside the net to the front of the net, likely screening the goaltenders view.
        At this time, defensive :green[player 90] leaves his spot by the net, moving to the right faceoff point, leaving :violet[19] alone in front of the net.
        Likely, :violet[player 16] noticed this, and chose to take the shot, as there is a high likelihood that teammate :violet[19] could gain access to the rebound as the only player in front of the net, creating a good scoring opportunity.
""")

st.image(str(ROOT / "images/scenario2.jpeg"), caption='Scenario 2')

st.markdown("""
        ### Incorporation of Interactive Elements
        The app includes several interactive elements which aid the user in manipulating the scenario to display the appropriate information. 
        The goal of the interactive elements is such that the viewer can chose which visual elements are important to analyze the current scenario. Additionally, it allows for the rapid selection of scenarios for analysis.
        
        **Interactive Workflow**  
        Firstly, the user is prompted to upload their game events file, in CSV format. The app automatically sorts through all events, and picks out a list of powerplay scenarios which fit the definition from earlier.   
        Next, the user can use the following interactive elements to change the visual:  
        
        - **Scenario Selector:** A drop down menu allows the user to select the scenario. Each item row contains the period, match-clock, and player who shot the puck. Additionally, it shows the outcome of the shot.  
        - **Seconds Prior to Shot:** This slider allows the user to select how many seconds prior to the shot should be displayed.
        - **Passes, Puck Control:** Allows the user to select whether the pases and puck control arrows are shown.
        - **Attacker, Defender Trails:** Allows the user to toggle whether players and their trails (where they were located) are shown.
        - **Start, End Polygons:** The polygons represent the structure areas in control by the defence team. Toggling these allows for showing or hiding the structure.
        - **Attacker, Defender Frames:** The frames sliders can allow the user to toggle how many frames of movement they wish to see from the attackers or defenders.      
""") ## interactive elements

_interactive_img = ROOT / "images/interactive_elements.jpg"
if _interactive_img.exists():
    st.image(str(_interactive_img), caption="Interactive elements which the user can toggle. Panel 1 shows the scenario selection panel being closed, and Panel 2 shows it being open.")

st.markdown("""
        ### Feedback from HC Davos
        Unfortunately, we were unable to receive feedback from HC Davos for the purposes of this submission in time.
""") #md feedback from HC Davos


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
st.image(str(ROOT / "images/mass_player_plotting.png"), caption="An early attempt at plotting a structure scenario, including all defensive players.")

st.markdown("""
         As is visible in the above example, and in particular across longer events, there are too many points for a reader to follow which structure is employed by the defensive team.
         As the puck and play shifts from one side of the ice to the other, the entire defensive structure moves along with it. As a result, this plotting method resulted in overlapping points, which do not tell a conlcusive story.
         The method outlined to solve this issue is multifold: 
         - A light opacity polygon connects all defensive players, to outline the defensive structure. It can show both the structure at the start and end of the play.
         - Player positioning dots are connected using solid lines, in increasing opacity, which effectively plots an additional time dimension. The audience, as a result of this, can now see how the play developed over time through the movement of the puck and players.
         
         Through developing the mass player plots, we realized that in this case, it is ideal to minimize the amount of information which is presented to the user, which still allows for the transmission of information.
""") ## md mass player plotting 2


st.markdown("""
        ### Directional Arrows
        During the intermediate stage of the project, we felt that adding directional arrows to player movements would give an additional dimension of details about the actions players took throughout the play. 
        Once implemented, the team came to the conclusion that the arrows did not add additional useful information to the scenario, but rather added to clutter and disorganization that made the diagram harder to read.
        Additionally, if a player stood still or multiple lines are captured for a single moment, arrows for a player would overlap. On occasion, some data points did not include directional data for some or all players, leading to a unconsistent visual.
        
        Example:   
        """) ## md directional arrows

st.image(
 str(ROOT / "images/improvements-arrows.png"),
"Scenario with the inclusion of directional arrows for each player"
) ## arrows image

st.markdown("""
        ## Future Steps 
        Unfortunately, as mentioned above, we were unable to receive timely feedback from HC Davos to inform our future steps for this project. Even without this feedback, there are several areas which we would like to further investigate in the future. Primarily, this would rely on being able to access additional data.
        At present, we only had access to three game-datasets, which did allow us to create a framework and technical application for the display and analysis for a coaching member, but it did not allow us to fulfil the goals of the project as outlined by HC Davos.
        Under ideal circumstances, such as if we were able to access the event logs of each game within the National League, there are a number of potential avenues to review, such as:
        - **Creating Play Heatmaps:** An increased amount of data could be used to compile additional statistical maps, such as where primary and secondary assists come from, based on the location of a shot.
        - **Automatic Structure Detection:** Automatically detecting and labeling plays where defensive structures occur, through machine learning models. Data could be used in aggregate for coaches to dictate powerplay strategy, or as individual scenarios to coach players.
        - **Critical Moments Detection:** Create models which could automatically identify and label 'critical moments', which could be used as examples during coaching sessions.
        - **Enhanced Game Strategy:** Automatic strategic analysis of opponents playing styles, weaknesses, and strengths to inform coaches and players of key information prior to games. This would likely encompass several of the above ideas and would require integration of different external data sources.  
        
        We realize that while this project has limited applications at the moment, there is significant potential with this data. From integrating game-data into helping coaches be more effective, describing game statistics in greater detail, and augmenting the fan experience through real-time interactive elements, this data has the power to significantly impact how ice hockey is played and enjoyed, alike.
""") #future steps

st.markdown("""
        ## Conclusion 
        At the start of the project, the request that came from HC Davos was to use analytics and statistics to better inform them of where other teams were vulnerable, and how HC Davos could adjust their powerplay strategy to stay competitive in the league. Unfortunately, due to the limited amounts of data provided, we were unable to directly fulfil this request.
        Despite this, we were able to develop an analytics platform that we belive has the value to deliver on valuable insights for any team which were to employ it. The platform allows any coach to upload a game's event dataset, and within seconds, they are able to analyze their teams performance throughout the game.
        One of the strengths of this platform is that it removes all technical understanding to be able to access the data, allowing it to be used by any coach or player to quickly access new insights and which may not be accessible through traditional video platforms.
        
        Hockey is a very fast moving game, where plays develop extremely quickly and with fluidity. Coming into this project, and particularly once we knew that there would only be limited data access, we knew that a successful project would hinge on developing a platform rather than trying to draw insights from only three games. 
        The platform approach allowed us to prepare the infrastructure, while a coach is able to apply their deep understanding and knowledge of hockey on top of the data. Ultimately, it is not just about building an insights platform, but also opening access to those who have the ability to turn interactive plots into real, game-ready insights.     
        
        Lastly, we want to provide a large thank you to HC Davos, in particular to Dylan Stanley and Martin Zöllner for providing the project topic, sample data, and expertise.
""") #conclusion



st.markdown("""
           ------
           
            ### AI Disclosure:
            Throughout this project, artificial intelligence was used for the purposes of code troubleshooting and code completion. 
            AI was also used to converting existing (handwritten) code from the interactive Jupyter format into the interactive Streamlit format. 
            Lastly, AI was used to automatically generate a ReadMe file for the GitHub repo.
""") # ai disclosure


load_time = datetime.datetime.now() - start_time
f"Load time: {load_time.seconds}s"