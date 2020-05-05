# [Dashboard](https://covid19dashboardpt.herokuapp.com/) COVID-19 Portugal 🇵🇹
### About the dashboard
This dashboard displays the trends for different figures, i.e., `confirmed cases`, `reported deaths`, `recovered cases`, `suspect cases`, `non-confirmed cases` and `active cases`. The weekly and daily rate of change for all figures are presented not only over time but also over the figure itself. This analysis was inspired from the one performed by [aatish](https://github.com/aatishb/covidtrends). He plotted both `confirmed cases` and `reported deaths` for several countries, but since I wanted to check the behaviour for the rest of the information provided by the Portuguese Health System, I decided to make my own dashboard as a personal challenge.

The dashboard was created with *[Dash](https://dash.plotly.com/)* from *[Plotly](https://plotly.com/)*. The application layout itself was adapted from the *Dash* sample apps, concretely the [Dash DAQ Satellite Dashboard](https://github.com/plotly/dash-sample-apps/tree/master/apps/dash-daq-satellite-dashboard). Several changes were made to better suit the purpose of this app.

### Data sources
This dashboard uses the data from the good people at *Data Science for Social Good Portugal*. For more information on how the data is handled and which sources are used, please visit their GitHub page [here](https://github.com/dssg-pt/covid19pt-data). Portugal's population is used to calculate the figures which are normalized to the country's current population. A small scrapper was constructed to that end and extracts the information from *Worldometers* [here](https://www.worldometers.info/world-population/portugal-population/).

### Run locally
To run the app locally, clone the repository and run `pip install -r requirements.txt` to install the dependencies. Or, alternatively, if you use conda, clone the environment with the command `conda env create -f environment.yaml`. To run the app type `python app.py` in the terminal within the folder where the repo was cloned.
