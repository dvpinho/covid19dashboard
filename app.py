import dash
import pandas as pd
import requests
from bs4 import BeautifulSoup
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_daq as daq
from datetime import datetime


# Load the data from DSSG_PT (Thanks!)
data = pd.read_csv('https://raw.githubusercontent.com/dssg-pt/covid19pt-data/master/data.csv',
                   usecols=['data', 'confirmados', 'recuperados', 'obitos', 'suspeitos', 'lab'],
                   skiprows=range(1, 5)).fillna(0).rename(columns={
                       'data': 'Date',
                       'confirmados': 'Confirmed Cases',
                       'recuperados': 'Recovered Cases',
                       'obitos': 'Reported Deaths',
                       'suspeitos': 'Suspect Cases'})
data['Date'] = [datetime.strptime(date, '%d-%m-%Y').strftime('%Y-%m-%d') for date in data['Date']]
data['Non-Confirmed Cases'] = data['Suspect Cases'] - data['Confirmed Cases'] - data['lab']
data['Active Cases'] = data['Confirmed Cases'] - data['Reported Deaths'] - data['Recovered Cases']
data = data.drop('lab', axis=1)
length_data = len(data)


# Grab the number of tested samples
samples_prt = pd.read_csv('https://raw.githubusercontent.com/dssg-pt/covid19pt-data/master/amostras.csv',
                          usecols=['amostras']).iloc[-1]
print(f'The current number of samples is {samples_prt}')

# Grab the current population of Portugal
page_source_code = requests.get('https://www.worldometers.info/world-population/portugal-population/').text
soup = BeautifulSoup(page_source_code, 'lxml')

try:
    info_main_block = soup.find('div', class_=['col-md-8 country-pop-description'])
    population_pt = int(info_main_block.find_all('strong')[2].text.replace(',', ''))
except Exception:
    population_pt = 10.2e6
print(f'The current population of Portugal is {population_pt}')

"""
Metrics calculation
The death rate is calculated with the equation CFR = deaths at day.x / cases at day.x-{T}
where T = average time period from case confirmation to death, in our case T = 7
(Source: https://www.worldometers.info/coronavirus/coronavirus-death-rate/)
"""
death_rate = round((data['Reported Deaths'].iloc[-1] / data['Confirmed Cases'].iloc[-8]) * 100, 2)
recovery_rate = 100 - death_rate
deaths_1m_people = round(data['Reported Deaths'].iloc[-1] / population_pt * 1e6, 0)
cases_1m_people = round(data['Confirmed Cases'].iloc[-1] / population_pt * 1e6, 0)
samples_1m_people = round(samples_prt / population_pt * 1e6, 0)


# Initialize the app
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ]
)

app.title = 'Covid-19 Dashboard PT'
server = app.server

data_dropdown = dcc.Dropdown(
    id="data_dropdown_component",
    options=[{'label': i, 'value': i} for i in data.columns.values[1:]],
    clearable=False,
    value="Confirmed Cases"
)

time_dropdown = dcc.Dropdown(
    id="time_dropdown_component",
    options=[
        {'label': 'Weekly', 'value': 'Weekly'},
        {'label': 'Daily', 'value': 'Daily'}
    ],
    clearable=False,
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
    value="All Data"
)

fatality_rate_display = html.Div(
    id="fatality_rate_display",
    children=[
        daq.LEDDisplay(
            value=death_rate,
            label="Case-Fatality Rate (%)",
            size=20,
            color="#eb3434",
            style={"color": "#black"},
            backgroundColor="#2b2b2b",
        )
    ]
)

recovery_rate_display = html.Div(
    id="recovery_rate_display",
    children=[
        daq.LEDDisplay(
            value=recovery_rate,
            label="Recovery Rate (%)",
            size=20,
            color="#2e8b57",
            style={"color": "#black"},
            backgroundColor="#2b2b2b",
        )
    ]
)

tested_samples_display = html.Div(
    id="tested_samples_display",
    children=[
        daq.LEDDisplay(
            value=samples_prt,
            label="Tested Samples",
            size=20,
            color="white",
            style={"color": "#black"},
            backgroundColor="#2b2b2b",
        )
    ]
)

cases_1m_display = html.Div(
    id="cases_1m_display",
    children=[
        daq.LEDDisplay(
            value=cases_1m_people,
            label="Cases / 1M People",
            size=20,
            color="#FFA500",
            style={"color": "#black"},
            backgroundColor="#2b2b2b",
        )
    ]
)

deaths_1m_display = html.Div(
    id="deaths_1m_display",
    children=[
        daq.LEDDisplay(
            value=deaths_1m_people,
            label="Deaths / 1M People",
            size=20,
            color="#B22222",
            style={"color": "#black"},
            backgroundColor="#2b2b2b",
        )
    ]
)

samples_1m_display = html.Div(
    id="samples_1m_display",
    children=[
        daq.LEDDisplay(
            value=samples_1m_people,
            label="Samples / 1M People",
            size=20,
            color="white",
            style={"color": "#black"},
            backgroundColor="#2b2b2b",
        )
    ]
)

app_title = html.P(id="app_title", children=["COVID-19", html.Br(), " Portugal Dashboard"])
app_dropdown_text = html.H1(id="app_dropdown_text", children="")
app_body = html.P(className="app_body", id="app_body", children=[""])

side_panel_layout = html.Div(
    id="panel_side",
    children=[
        app_title,
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

metrics = html.Div(
    id="metrics_container",
    children=[
        html.Div(
            id="metrics_header",
            children=[
                html.H1(
                    id="metrics_title", children=[f"Status as of {data['Date'].iloc[-1]}"]
                )
            ]
        )
    ]
)

main_panel_layout = html.Div(
    id="panel_upper_lower",
    children=[
        graph_1,
        html.Div(
            id="panel",
            children=[
                graph_2,
                html.Div(
                    id='panel_metrics',
                    children=[
                        metrics,
                        html.Div(
                            children=[
                                fatality_rate_display,
                                recovery_rate_display,
                                tested_samples_display,
                                cases_1m_display,
                                deaths_1m_display,
                                samples_1m_display
                            ]
                        )
                    ]
                )
            ]
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
def update_satellite_name(val, val_last_time):
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
            *SARS-CoV-2* in the past {time_window} as a function of the total number of **{val}** (Data from DGS daily
            reports). If viewed with a weekly rate of change, the exponential behaviour is viewed as a straight line
            and, in case the disease is being beaten, the curve with start to round off at the top and will start to
            travel with a downwards trend that will be visible as a sudden drop. Note that the graph is not plotted
            over time, but instead the total number of **{val}**, therefore, it plots the rate of change over the last
            {time_window}. Time is shown in each data point with the corresponding day. Below the main figure, the data
            over time is also present. Hover over the graph for more information. Drag the mouse to zoom in and
            doubleclick to zoom back out. For more information concerning statistics and research about *COVID-19*
            please visit this [page](https://ourworldindata.org/coronavirus). Sources: data from *Data Science for
            Social Good Portugal* [GitHub](https://github.com/dssg-pt/covid19pt-data), current population of Portugal
            from *Worldometers* country [page](https://www.worldometers.info/world-population/portugal-population/).
            Application's source code [here](https://github.com/dvpinho/covid19dashboard).
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
    elif data_source == 'Active Cases':
        index = 1

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
                'size': 10,
                'opacity': 0.8
            }
        )],
        'layout': dict(
            margin={"t": 30, "r": 35, "b": 80, "l": 80},
            xaxis={
                'title': 'Time',
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
                'size': 10,
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
            margin={'r': 25},
            hovermode='closest',
            font={
                'color': 'gray',
                'family': 'Arial',
                'size': 13
            }
        )
    }


if __name__ == "__main__":
    app.run_server(debug=False)
