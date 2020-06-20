import os
import dash
import pathlib
import requests
import pandas as pd
import plotly.graph_objs as go
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_daq as daq
from datetime import datetime


# Load the data from DSSG_PT (Thanks!)
data = pd.read_csv('https://raw.githubusercontent.com/dssg-pt/covid19pt-data/master/data.csv', usecols=[
    'data', 'confirmados', 'recuperados', 'obitos', 'suspeitos', 'lab', 'internados', 'internados_uci'],
    skiprows=range(1, 5)).fillna(0).rename(columns={
        'data': 'Date',
        'confirmados': 'Confirmed Cases',
        'recuperados': 'Recovered Cases',
        'obitos': 'Reported Deaths',
        'suspeitos': 'Suspect Cases'})

data['Date'] = [datetime.strptime(date, '%d-%m-%Y').strftime('%Y-%m-%d') for date in data['Date']]
data['Non-Confirmed Cases'] = data['Suspect Cases'] - data['Confirmed Cases'] - data['lab']

prt_confirmed = data['Confirmed Cases'].iloc[-1]
prt_deaths = data['Reported Deaths'].iloc[-1]
prt_recovered = data['Recovered Cases'].iloc[-1]
active_cases = data['Confirmed Cases'].iloc[-1] - data['Reported Deaths'].iloc[-1] - data['Recovered Cases'].iloc[-1]
active_cases_daily = active_cases - (
    data['Confirmed Cases'].iloc[-2] - data['Reported Deaths'].iloc[-2] - data['Recovered Cases'].iloc[-2])
hospitalized = data['internados'].iloc[-1]
hospitalized_daily = hospitalized - data['internados'].iloc[-2]
intensive_care_unit = data['internados_uci'].iloc[-1]
icu_daily = intensive_care_unit - data['internados_uci'].iloc[-2]

data = data.drop(['lab', 'internados', 'internados_uci'], axis=1)
length_data = len(data)

# Grab the number of tested samples
samples_prt = pd.read_csv('https://raw.githubusercontent.com/dssg-pt/covid19pt-data/master/amostras.csv').iloc[-1]
total_samples = samples_prt['amostras']
new_samples = samples_prt['amostras_novas']

"""
Metrics calculation
The death rate is calculated with the equation CFR = deaths at day.x / cases at day.x-{T}
where T = average time period from case confirmation to death, in our case T = 7
(Source: https://www.worldometers.info/coronavirus/coronavirus-death-rate/)
"""
death_rate = round((data['Reported Deaths'].iloc[-1] / data['Confirmed Cases'].iloc[-8]) * 100, 2)

# Confirmed cases by city in Portugal
confirmed_cases_portugal_cities = pd.read_csv(
    "https://raw.githubusercontent.com/dssg-pt/covid19pt-data/master/data_concelhos.csv").fillna(
    method='ffill').fillna(method='bfill').dropna(axis=1)
pt_cities = confirmed_cases_portugal_cities.drop(columns='data')

DATA_PATH = pathlib.Path(__file__).parent.joinpath("data")

cities_coordinates = pd.read_csv(DATA_PATH.joinpath('pt_regions.csv'), usecols=['city', 'latitude', 'longitude'])
cities_coordinates['city'] = cities_coordinates['city'].str.upper()

data_cities = cities_coordinates[cities_coordinates['city'].isin(pt_cities.columns)]
data_cities = data_cities.assign(
    current_cases=[pt_cities[city].iloc[-1] for _, city in enumerate(data_cities['city'])],
    max_cases=[pt_cities[city].max() for _, city in enumerate(data_cities['city'])],
    daily_diff=[pt_cities[city].iloc[-1] - pt_cities[city].iloc[-2] for _, city in enumerate(data_cities['city'])]
)

def get_current_country_data():

    # This function assumes a 200 response.
    # This needs to be reworked in the future in case the API call fails.
    url = 'https://www.trackcorona.live/api/countries'
    countries_data = requests.get(url).json()
    countries = pd.DataFrame(countries_data['data'])

    # Location correction for Togo, Congo and Georgia
    countries.loc[countries['location'] == 'Togo', ['latitude', 'longitude']] = 8.619543, 0.824782
    countries.loc[countries['location'] == 'Congo', ['latitude', 'longitude']] = -0.228021, 15.827659
    countries.loc[countries['location'] == 'Georgia', ['latitude', 'longitude']] = 42.315407, 43.356892

    countries = countries[countries['location'] != 'Portugal']  # Remove PRT from map. Data from PRT has own source.

    return countries


countries = get_current_country_data()
world_confirmed = countries['confirmed'].sum()
world_recovered = countries['recovered'].sum()
world_deaths = countries['dead'].sum()
world_active = world_confirmed - world_recovered - world_deaths

# Initialize the app
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ]
)

app.title = 'COVID-19 Dashboard PT'
server = app.server

data_dropdown = dcc.Dropdown(
    id="data_dropdown_component",
    options=[{'label': i, 'value': i} for i in data.columns.values[1:]],
    clearable=False,
    searchable=False,
    value="Confirmed Cases"
)

time_dropdown = dcc.Dropdown(
    id="time_dropdown_component",
    options=[
        {'label': 'Weekly', 'value': 'Weekly'},
        {'label': 'Daily', 'value': 'Daily'}
    ],
    clearable=False,
    searchable=False,
    value="Weekly"
)

time_window_dropdown = dcc.Dropdown(
    id="time_window_dropdown_component",
    options=[
        {'label': 'All Data', 'value': 'All Data'},
        {'label': 'Last 30 days', 'value': 'Last 30 days'},
        {'label': 'Last 15 days', 'value': 'Last 15 days'},
        {'label': 'Last 7 days', 'value': 'Last 7 days'},
    ],
    clearable=False,
    searchable=False,
    value="All Data"
)

app_title = html.P(id="app_title", children=["COVID-19", html.Br(), "Portugal Dashboard"])
app_update_date = html.P(id="update_date", children=[f"Status as of {data['Date'].iloc[-1]}"])
app_dropdown_text = html.H1(id="app_dropdown_text", children="")
app_body = html.P(className="app_body", id="app_body", children=[""])

side_panel_layout = html.Div(
    id="panel_side",
    children=[
        app_title,
        app_update_date,
        html.Div(id="info_dropdown",
                 children=[data_dropdown, time_dropdown, time_window_dropdown]),
        html.Div(id="panel_side_text",
                 children=[app_dropdown_text, app_body])
    ]
)

figure_1_scale_toggle = daq.ToggleSwitch(
    id="graph_1_scale_toggle",
    value=True,
    label=["Linear", "Logarithmic"],
    color="#ffe102",
    style={"color": "#black"}
)

figure_2_scale_toggle = daq.ToggleSwitch(
    id="graph_2_scale_toggle",
    value=False,
    label=["Linear", "Logarithmic"],
    color="#ffe102",
    style={"color": "#black"}
)

figure_3_scale_toggle = daq.ToggleSwitch(
    id="graph_3_scale_toggle",
    value=False,
    label=["Linear", "Logarithmic"],
    color="#ffe102",
    style={"color": "#black"}
)

figure_1_layout = {
    "showlegend": False,
    "autosize": True,
    "paper_bgcolor": "#1e1e1e",
    "plot_bgcolor": "#1e1e1e",
    "margin": {"t": 0, "r": 0, "b": 0, "l": 0}
}

graph_1 = html.Div(
    id="graph_1_wrapper",
    children=[
        figure_1_scale_toggle,
        dcc.Graph(
            id="graph_1",
            figure={"layout": figure_1_layout},
            config={"displayModeBar": False, "scrollZoom": False}
        )
    ]
)

graph_2 = html.Div(
    id="graph_2_container",
    children=[
        html.Div(
            id="graph_2_header",
            children=[
                html.H1(
                    id="graph_2_title", children=[""]
                ),
                figure_2_scale_toggle
            ]
        ),
        dcc.Graph(
            id="graph_2",
            config={"displayModeBar": False}
        )
    ]
)

# Map graph
color_scale = ['#FFFAFA', '#F4C2C2', '#FF6961', '#FF5C5C', '#FF1C00', '#FF0800', '#FF0000', '#CD5C5C', '#E34234',
               '#D73B3E', '#CE1620', '#CC0000', '#B22222', '#B31B1B', '#A40000', '#800000', '#701C1C', '#321414']

fig = go.Figure()

fig.add_trace(
    go.Scattermapbox(
        lat=data_cities['latitude'],
        lon=data_cities['longitude'],
        hovertemplate="<b>%{hovertext}</b><br><br>"
        "Current confirmed cases: %{marker.color}<br>"
        "Peak confirmed cases: %{customdata}<br>"
        "New cases since yesterday: %{text}"
        "<extra></extra>",
        customdata=data_cities['max_cases'],
        hovertext=data_cities['city'],
        text=data_cities['daily_diff'],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=data_cities['current_cases'],
            color=data_cities['current_cases'],
            sizemode='area',
            sizeref=.7,
            colorscale=color_scale
        )
    )
)

fig.add_trace(
    go.Scattermapbox(
        lat=countries['latitude'],
        lon=countries['longitude'],
        hovertemplate="<b>%{hovertext}</b><br><br>"
        "Confirmed cases: %{marker.color}<br>"
        "Reported deaths: %{customdata}<br>"
        "Recovered cases: %{text}"
        "<extra></extra>",
        customdata=countries['dead'],
        hovertext=countries['location'],
        text=countries['recovered'],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=countries['confirmed'],
            color=countries['confirmed'],
            sizemode='area',
            sizeref=30,
            colorscale=color_scale
        )
    )
)

MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')

fig.update_layout(
    autosize=True,
    hovermode='closest',
    showlegend=False,
    clickmode='event+select',
    margin={'b': 0, 'l': 0, 'r': 0, 't': 0},
    mapbox=dict(
        accesstoken=MAPBOX_ACCESS_TOKEN,
        center=dict(
            lat=39.55,
            lon=-8.18
        ),
        zoom=6,
        style='dark'
    )
)

map_graph = html.Div(
    id="world_map_wrapper",
    children=[
        dcc.Graph(
            id="world_map",
            figure=fig,
            config={"displayModeBar": False, "scrollZoom": True},
        ),
    ],
)

graph_3 = html.Div(
    id="graph_3_container",
    children=[
        html.Div(
            id="graph_3_header",
            children=[
                html.H1(
                    id="graph_3_title", children=[""]
                ),
                figure_3_scale_toggle
            ]
        ),
        dcc.Graph(
            id="graph_3",
            figure={"layout": {
                "showlegend": False,
                "autosize": True,
                "paper_bgcolor": "#2b2b2b",
                "plot_bgcolor": "2b2b2b",
            }},
            config={"displayModeBar": False}
        )
    ]
)

main_panel_layout = html.Div(
    id="panel_upper_lower",
    children=[
        html.Div(
            [
                html.Div(
                    [
                        html.H6(f'{prt_confirmed:,}'.replace(',', ' '), style={'color': '#e0f7fa'}),
                        dcc.Markdown(f"*+{prt_confirmed - data['Confirmed Cases'].iloc[-2]}*",
                                     style={'color': '#e0f7fa'}),
                        html.P(children=["Confirmed Cases", html.Br(), "Portugal"])
                    ],
                    id="confirmed_cases_prt",
                    className="container_confirmed_cases",
                ),
                html.Div(
                    [
                        html.H6(f'{prt_deaths:,}'.replace(',', ' '), style={'color': '#f44336'}),
                        dcc.Markdown(f"*+{prt_deaths - data['Reported Deaths'].iloc[-2]}*",
                                     style={'color': '#f44336'}),
                        html.P(children=["Reported Deaths", html.Br(), "Portugal"])
                    ],
                    id="reported_deaths_prt",
                    className="container_reported_deaths",
                ),
                html.Div(
                    [
                        html.H6(f'{prt_recovered:,}'.replace(',', ' '), style={'color': '#66bb6a'}),
                        dcc.Markdown(f"*+{prt_recovered - data['Recovered Cases'].iloc[-2]}*",
                                     style={'color': '#66bb6a'}),
                        html.P(children=["Recovered Cases", html.Br(), "Portugal"])
                    ],
                    id="recovered_cases_prt",
                    className="container_recovered_cases",
                ),
                html.Div(
                    [
                        html.H6(f'{active_cases:,}'.replace(',', ' '), style={'color': '#FFA500'}),
                        dcc.Markdown(f'*+{active_cases_daily}*' if active_cases_daily > 0 else f'*{active_cases_daily}*',
                                     style={'color': '#FFA500'}),
                        html.P(children=["Active Cases", html.Br(), "Portugal"])
                    ],
                    id="active_cases_prt",
                    className="container_active_cases",
                )
            ],
            className="row container-display",
        ),
        graph_1,
        html.Div(
            [
                html.Div(
                    [
                        html.H6(f'{int(hospitalized)}', style={'color': '#FFA500'}),
                        dcc.Markdown(f'*+{int(hospitalized_daily)}*' if hospitalized_daily > 0 else f'*{int(hospitalized_daily)}*',
                                     style={'color': '#FFA500'}),
                        html.P(children=["Hospitalized Cases", html.Br(), "Portugal"])
                    ],
                    id="hospitalized_cases_prt",
                    className="container_hospitalized_cases",
                ),
                html.Div(
                    [
                        html.H6(f'{int(intensive_care_unit)}', style={'color': '#B22222'}),
                        dcc.Markdown(f'*+{int(icu_daily)}*' if icu_daily > 0 else f'*{int(icu_daily)}*',
                                     style={'color': '#B22222'}),
                        html.P(children=["Intensive Care Unit", html.Br(), "Portugal"])
                    ],
                    id="icu_cases_prt",
                    className="container_icu_cases",
                ),
                html.Div(
                    [
                        html.H6(f'{int(total_samples):,}'.replace(',', ' '), style={'color': '#4db6ac'}),
                        dcc.Markdown(f'*+{int(new_samples):,}*'.replace(',', ' '), style={'color': '#4db6ac'}),
                        html.P(children=["Tested Samples", html.Br(), "Portugal"])
                    ],
                    id="samples_prt",
                    className="container_samples_prt",
                ),
                html.Div(
                    [
                        html.H6(f'{death_rate}', style={'color': '#eb3434'}),
                        dcc.Markdown(f'-'),
                        html.P(children=["Fatality Rate (%)", html.Br(), "Portugal"])
                    ],
                    id="death_rate_prt",
                    className="container_death_rate",
                )
            ],
            className="row container-display",
        ),
        html.Div(
            id="panel",
            children=[
                graph_2
            ]
        ),
        map_graph,
        html.Div(
            id="panel_graph_3",
            children=[
                graph_3
            ]
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H5(f'{world_confirmed:,}'.replace(',', ' '), style={'color': '#e0f7fa'}),
                        html.P(children=["Confirmed Cases", html.Br(), "Worldwide"])
                    ],
                    id="confirmed_cases_world",
                    className="container_confirmed_cases_world",
                ),
                html.Div(
                    [
                        html.H5(f'{world_deaths:,}'.replace(',', ' '), style={'color': '#f44336'}),
                        html.P(children=["Reported Deaths", html.Br(), "Worldwide"])
                    ],
                    id="reported_deaths_world",
                    className="container_reported_deaths_world",
                ),
                html.Div(
                    [
                        html.H5(f'{world_recovered:,}'.replace(',', ' '), style={'color': '#66bb6a'}),
                        html.P(children=["Recoverd Cases", html.Br(), "Worldwide"])
                    ],
                    id="recovered_cases_world",
                    className="container_recovered_cases_world",
                ),
                html.Div(
                    [
                        html.H5(f'{world_active:,}'.replace(',', ' '), style={'color': '#FFA500'}),
                        html.P(children=["Active Cases", html.Br(), "Worldwide"])
                    ],
                    id="active_cases_world",
                    className="container_active_cases_world",
                )
            ],
            className="row container-display",
        )
    ]
)

root_layout = html.Div(
    id="root",
    children=[
        side_panel_layout,
        main_panel_layout
    ]
)

app.layout = root_layout


@app.callback(
    Output("app_dropdown_text", "children"),
    [Input("data_dropdown_component", "value"),
     Input("time_window_dropdown_component", "value")],
)
def update_app_name(val, val_last_time):
    return f"SARS-CoV-2\n{val} ({val_last_time})"


@app.callback(
    Output("app_body", "children"),
    [Input("data_dropdown_component", "value"),
     Input("time_dropdown_component", "value")]
)
def update_data_description(val, val_time):
    if val_time == 'Weekly':
        time_window = 'week'
    else:
        time_window = 'day'

    text = dcc.Markdown(
        f'''
            The interactive graph displayed to the right shows the trajectory of the number of new **{val}** by
            *SARS-CoV-2* in the past {time_window} as a function of the total number of **{val}**. If viewed with a
            weekly rate of change, the exponential behaviour is observed as a straight line and, in case the disease
            is being beaten, the curve with start to round off at the top and will start to travel with a downwards
            trend that will be visible as a sudden drop. Note that the graph is not plotted over time, but instead over
            the total number of **{val}**, therefore, it plots the rate of change over the last {time_window}. Time is
            shown in each data point with the corresponding day. Below the main figure, the data over time is also
            present. Hover over the graphs for more information. For more information concerning statistics and
            research about *COVID-19* please visit this [page](https://ourworldindata.org/coronavirus). Sources:
            Portugal data from [*Data Science for Social Good Portugal*](https://github.com/dssg-pt/covid19pt-data).
            Country level data from [*TrackCorona*](https://www.trackcorona.live/) and
            [*Our World in Data*](https://github.com/owid/covid-19-data/tree/master/public/data).
            Application's [source code](https://github.com/dvpinho/covid19dashboard).
            '''
    )
    return text


@app.callback(
    Output('graph_2_title', 'children'),
    [Input('data_dropdown_component', 'value'),
     Input('time_dropdown_component', 'value'),
     Input('time_window_dropdown_component', 'value')]
)
def update_graph_2_labels(graph_title, val_time, last_data):

    if val_time == 'Weekly':
        return f'Average number of new {graph_title} per day in the previous week ({last_data})'
    else:
        return f'Cumulative {graph_title} ({last_data})'


@app.callback(
    Output('graph_2', 'figure'),
    [Input('data_dropdown_component', 'value'),
     Input('time_dropdown_component', 'value'),
     Input('time_window_dropdown_component', 'value'),
     Input('graph_2_scale_toggle', 'value')]
)
def update_graph_2_data(data_source, time_frame, last_data, toggle):

    if data_source == 'Confirmed Cases':
        index = 1
    elif data_source == 'Reported Deaths':
        index = 16
    elif data_source == 'Suspect Cases':
        index = 0
    elif data_source == 'Recovered Cases':
        index = 13
    elif data_source == 'Non-Confirmed Cases':
        index = 0

    if time_frame == 'Weekly':
        time = 7
    else:
        time = 1

    if last_data == 'All Data':
        t = 0
    elif last_data == 'Last 30 days':
        t = length_data - 30 - time - index
    elif last_data == 'Last 15 days':
        t = length_data - 15 - time - index
    else:
        t = length_data - 7 - time - index

    if time_frame == 'Daily':
        data_x = data['Date'].iloc[index:]
        data_y = data[data_source].iloc[index:]
        increment = [(data_y.iloc[cases] / data_y.iloc[cases - 1]) * 100 - 100 for cases in range(1, len(data_y))]

        data_x_axis = data_x[t + 1:]
        data_y_axis = data_y[t + 1:]
        marker_labels = increment[t:]

    else:

        data_x = data['Date'].iloc[time:]
        data_y = data[data_source]
        data_y = [(data_y.iloc[cases] - data_y.iloc[cases - time]) / 7 for cases in range(time, len(data_y))]
        increment = [(data_y[cases] / data_y[cases - 1]) * 100 - 100 for cases in range(1, len(data_y))]

        if last_data == 'All Data':
            offset = 0
            if data_source == 'Reported Deaths':
                offset = 8
            elif data_source == 'Recovered Cases':
                offset = 5
        elif last_data == 'Last 30 days':
            offset = length_data - 31 - time
        elif last_data == 'Last 15 days':
            offset = length_data - 16 - time
        else:
            offset = length_data - 8 - time

        data_x_axis = data_x[offset + 1:]
        data_y_axis = data_y[offset + 1:]
        marker_labels = increment[offset:]

    return {
        'data': [dict(
            x=data_x_axis,
            y=data_y_axis,
            name=data_source,
            mode='lines+markers',
            hovertemplate='%{y:.0f}<br>' + '<b>Increase: %{text:.1f}%</b>',
            text=marker_labels,
            marker={
                'size': 8,
                'opacity': 0.8
            }
        )],
        'layout': dict(
            margin={"t": 30, "r": 35, "b": 50, "l": 80},
            xaxis={
                'zeroline': False
            },
            yaxis={
                'title': f'{data_source}',
                'type': 'log' if toggle else 'linear',
                'zeroline': False
            },
            plot_bgcolor='#2b2b2b',
            paper_bgcolor='#2b2b2b',
            font={
                'color': '#a1a1a1',
                'family': 'Arial',
                'size': 13
            }
        )
    }


@app.callback(
    Output('graph_1', 'figure'),
    [Input('data_dropdown_component', 'value'),
     Input('time_dropdown_component', 'value'),
     Input('time_window_dropdown_component', 'value'),
     Input('graph_1_scale_toggle', 'value')]
)
def update_graph_1_data(data_source, time_frame, last_data, toggle):
    if time_frame == 'Weekly':
        time = 7
        y_axis_time = 'week'
    else:
        time = 1
        y_axis_time = 'day'

    if last_data == 'All Data':
        t = 0
    elif last_data == 'Last 30 days':
        t = length_data - 30 - time
    elif last_data == 'Last 15 days':
        t = length_data - 15 - time
    else:
        t = length_data - 7 - time

    source = data[data_source]
    weekly_daily_source = [source[cases] - source[cases - time]
                           for cases in range(time, len(source))]

    x_data_time = source.iloc[time:]
    x_data = x_data_time.iloc[t:]
    y_data = weekly_daily_source[t:]
    text_data = data['Date'].iloc[t + time:]

    return {
        'data': [dict(
            x=x_data,
            y=y_data,
            hovertemplate='Total %{customdata[0]}: %{x:.0f}' +
            '<br><b>%{customdata[1]} %{customdata[0]}</b>: %{y:.0f}' +
            '<br><b>%{text}</b>',
            text='Date: ' + text_data,
            customdata=[[data_source, time_frame]] * len(text_data),
            name=data_source,
            mode='lines+markers',
            marker={
                'size': 7,
                'opacity': 0.8
            }
        )],
        'layout': dict(
            xaxis={
                'title': f'Total number of {data_source}',
                'type': 'log' if toggle else 'linear',
                'zeroline': False
            },
            yaxis={
                'title': f'New {data_source} (in the past {y_axis_time})',
                'type': 'log' if toggle else 'linear',
                'zeroline': False
            },
            plot_bgcolor='#1e1e1e',
            paper_bgcolor='#1e1e1e',
            margin={'r': 5, 't': 10},
            hovermode='closest',
            font={
                'color': 'gray',
                'family': 'Arial',
                'size': 13
            }
        )
    }


@app.callback(
    Output('graph_3_title', 'children'),
    [Input('world_map', 'clickData')]
)
def update_graph_3_title(click_data):
    if click_data is not None:
        click_name = click_data['points'][0]['hovertext']
        return f'Confirmed cases in {click_name}'
    else:
        return 'Click on a map region to show the confirmed cases over time'


confirmed_cases_country = pd.read_csv(
    'https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv',
    usecols=['location', 'date', 'total_cases']
)

confirmed_cases_portugal_cities['data'] = [datetime.strptime(
    date, '%d-%m-%Y').strftime('%Y-%m-%d') for date in confirmed_cases_portugal_cities['data']]
stacked_portugal_cities_confirmed = pd.concat([pd.DataFrame(
    {
        'location': [city] * len(confirmed_cases_portugal_cities),
        'date': confirmed_cases_portugal_cities['data'],
        'total_cases': confirmed_cases_portugal_cities[city]
    }) for city in confirmed_cases_portugal_cities.columns.values[1:]], ignore_index=True
)

world_pt_confirmed_cases = pd.concat([confirmed_cases_country, stacked_portugal_cities_confirmed], ignore_index=True)


@app.callback(
    Output('graph_3', 'figure'),
    [Input('world_map', 'clickData'),
     Input('graph_3_scale_toggle', 'value')])
def display_click_data(click_data, toggle):

    if click_data is not None:

        region_name = click_data['points'][0]['hovertext']
        cases_country = world_pt_confirmed_cases[world_pt_confirmed_cases['location'] == region_name]

        return {
            'data': [dict(
                x=cases_country['date'],
                y=cases_country['total_cases'],
                mode='lines+markers',
                marker={
                    'size': 8,
                    'opacity': 0.8
                }
            )],
            'layout': dict(
                margin={"t": 30, "r": 35, "b": 50, "l": 80},
                xaxis={
                    'zeroline': False
                },
                yaxis={
                    'title': 'Confirmed Cases',
                    'type': 'log' if toggle else 'linear',
                    'zeroline': False
                },
                plot_bgcolor='#2b2b2b',
                paper_bgcolor='#2b2b2b',
                font={
                    'color': '#a1a1a1',
                    'family': 'Arial',
                    'size': 13
                }
            )
        }

    else:

        return {
            'data': [dict(
                x=[1], y=[1],
                mode='markers',
                hoverinfo='skip',
                marker={
                    'size': 1,
                    'opacity': 0
                }
            )],
            'layout': dict(
                xaxis={'zeroline': False, 'showgrid': False},
                yaxis={'zeroline': False, 'showgrid': False},
                plot_bgcolor='#2b2b2b',
                paper_bgcolor='#2b2b2b',
                font={'color': '#2b2b2b'}
            )
        }


if __name__ == "__main__":
    app.run_server(debug=False)
