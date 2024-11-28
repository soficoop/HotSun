import json
import sys

from imports import *
import period_strategy
from df_objects import *
from manager import Manager
import hourly_strategy
from post_processor import PostProcessor
from pages.laod_display import get_parameter_wrapper, get_display

logging.info("Start application")

cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheLongCallbackManager(cache)
application = Dash("Hot Sun", use_pages=True,
                   external_stylesheets=[dbc.themes.BOOTSTRAP,
                                         dbc.icons.BOOTSTRAP,
                                         'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css'],
                   suppress_callback_exceptions=True, background_callback_manager=background_callback_manager,
                   )

application._favicon = "logo.ico"

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Start", href="/start")),
        dbc.NavItem(dbc.NavLink("Display Result", href="/display-result")),
        dbc.NavItem(dbc.NavLink("About Us", href="/about-us"))
    ],
    brand="Hot Sun",
    brand_href="/",
    color="transparent",
    dark=True,
    style={"height": "80px",
           "backgroundImage": "linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0))",
           "WebkitFilter": "drop-shadow(5px 5px 5px #333333)",
           "filter": "drop-shadow(5px 5px 5px #333333)"}
)

application.layout = html.Div([dbc.Carousel(
    items=[
        {"key": "1", "src": "/assets/back3.jpg"},
        {"key": "2", "src": "/assets/back4.jpg"},
        {"key": "3", "src": "/assets/back4.jpeg"}
    ],
    controls=False,
    indicators=False,
    interval=3000,
    ride="carousel",
    className="carousel-fade",
    style={"zIndex": "-1", "overflow": "hidden", "position": "absolute", "margin": "auto", "padding": "auto", "height": "100vh", "width": "100vw"}
),
    navbar,
    dash.page_container,
    html.Div([html.Div([html.H3("Loading...", id="loading-label"),
                        dbc.Progress(id="progress_bar",
                                     style={'width': '300px', 'height': '20px'})],
                       style={"position": "absolute", "left": "50%", "top": "50%",
                              "marginTop": "-50px",
                              "marginLeft": "-150px"})],
             id="loading", style={"display": "none"}, className="text-center"),
    dcc.Store(id="config", storage_type="session", data=json.load(open("config.json"))),
    html.Div(style={"overflow": "hidden", "height": "100vh",
                    "backgroundImage": "linear-gradient(rgba(0,0,0,0), rgba(0,0,0,0), rgba(0,0,0,0), rgba(0,0,0,0), rgba(0,0,0,0.1))",
                    })
], style={"overflow": "hidden", "height": "100vh"})
ConfigGetter.load_data()


@application.long_callback(
    Output("paramerts", "children"),
    Output("df_energy", "data"),
    Output("df_finance", "data"),
    Output("display", "children"),
    Input("run", "n_clicks"),
    State("config", "data"),
    manager=background_callback_manager,
    running=[
        (Output("run", "disabled"), True, False),
        (Output("cancel", "disabled"), False, True),
        (Output("loading", "style"), {"display": 'block', 'position': 'absolute',
                                      'top': '8%', 'left': '25%',
                                      'textAlign': "center", 'width': "75%", "height": "92%",
                                      "background": "rgba(255,255,255,0)", "backgroundSize": "cover"}
         , {"display": "none"})
    ],
    cancel=[Input("cancel", "n_clicks"), Input("location", "href")],
    progress=[Output("progress_bar", "value"), Output("progress_bar", "max"), Output("loading-label", "children"),
              Output("progress_bar", "label")],
    prevent_intial_call=True
)
def main(set_progress, n, config):
    """
    Main function of the application. It is called when the user clicks on the run button.
    :param set_progress: function to update the progress bar
    :param n: number of clicks on the run button
    :param config: configuration of the application
    :return: parameters of the simulation, energy dataframe, finance and pollution dataframe, display of the results
    """
    set_progress(("0", "1", "Gathering Data...", "100%"))
    # demand_hourly = DemandHourlyCityData(config['LOCATION']['name'])
    demand_hourly = DemandHourlyCustomYearlyFile('highschool_consumption.csv', 1.028, config['END_YEAR'])

    if config["solar"]["datasource"] == "PVGIS":
        solar_rad_hourly = SolarProductionHourlyDataPVGIS(config['LOCATION']['longitude'],
                                                          config['LOCATION']['latitude'],
                                                          config['solar']['peakpower'],
                                                          config['solar']['loss'])
    else:
        solar_rad_hourly = SolarRadiationHourlyMonthData()
    print("setting progress")
    set_progress(("1", "1", "Gathering Data...", "100%"))

    manager = Manager(demand_hourly, [],
                      solar_rad_hourly,
                      hourly_strategy.GreedyDailyStrategy(), config)
    output_energy = manager.run_simulator(set_progress)
    post_processor = PostProcessor(output_energy, config)
    output_post_processor = post_processor.run_post_processor(set_progress)

    set_progress(("1", "1", "Displaying results... Note: This operation may take a while. Be patient.", "100%"))

    return get_parameter_wrapper(config), output_energy.to_dict('records'), output_post_processor.to_dict('records'), \
           get_display(config, output_energy, output_post_processor)


if __name__ == '__main__':
    application.run_server(debug=True)
