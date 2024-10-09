import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd

# Load the dataset
excel = 'VisualAmended_v6.xlsx'
data_sheet = 'CleanedDataset'
df = pd.read_excel(excel, sheet_name=data_sheet)

# Process dataset for stacked bar chart: APT and Platforms
df_expanded = df.assign(platform=df['platforms'].str.split(',')).explode('platform')
df_expanded['platform'] = df_expanded['platform'].str.strip()

# Identify the top 5 vulnerable platforms
platform_counts = df_expanded['platform'].value_counts()
top_5_platforms = platform_counts.head(5).index.tolist()

# Filter the data to include only the top 5 platforms
df_top_platforms = df_expanded[df_expanded['platform'].isin(top_5_platforms)]

# Group the data by APT and platform
apt_platform_counts = df_top_platforms.groupby(['APT', 'platform']).size().reset_index(name='count')

# Function to create the stacked bar chart
def create_stacked_bar_chart(data):
    fig = px.bar(
        data,
        x='APT',
        y='count',
        color='platform',
        title='Platforms Matched with APTs',
        labels={'count': 'Number of Occurrences', 'APT': 'APT Groups'},
        barmode='stack'
    )
    return fig

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the dashboard
app.layout = html.Div([

    # Title
    html.H1("APT and Vulnerability Dashboard", style={'textAlign': 'center'}),

    # Create tabs
    dcc.Tabs([
        dcc.Tab(label='APT and Platforms', children=[
            html.Div([

                # Filters and Controls (Left Panel)
                html.Div([
                    html.H3("Filters"),
                    dcc.Dropdown(
                        id="apt-filter",
                        options=[{'label': apt, 'value': apt} for apt in df['APT'].unique()],
                        multi=True,
                        placeholder="Select APT"
                    ),
                    dcc.Dropdown(
                        id="platform-filter",
                        options=[{'label': platform, 'value': platform} for platform in df_expanded['platform'].unique()],
                        multi=True,
                        placeholder="Select Platform"
                    ),
                    dcc.Slider(
                        id="cvss-slider",
                        min=0,
                        max=10,
                        step=0.1,
                        value=5,
                        marks={i: str(i) for i in range(11)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Button('Apply Filters', id='apply-filters', n_clicks=0)
                ], style={'width': '20%', 'float': 'left', 'padding': '20px'}),

                # Main Graph Area (Right Panel)
                html.Div([
                    dcc.Graph(id="apt-platform-stacked-bar-chart",
                              figure=create_stacked_bar_chart(apt_platform_counts)),
                ], style={'width': '75%', 'float': 'right', 'padding': '20px'})
            ])
        ]),
        dcc.Tab(label='Algorithm', children=[
            html.Div([
                html.H3("Analysis Inputs"),
                
                # Dropdown for APT name
                html.Label("Select APT Name:"),
                dcc.Dropdown(
                    id='apt-dropdown',
                    options=[{'label': apt, 'value': apt} for apt in df['APT'].unique()],
                    placeholder="Select APT"
                ),
                
                # Input field for No. of Techniques
                html.Label("Number of Technique(s):"),
                dcc.Input(
                    id='technique-input',
                    type='number',
                    placeholder='Enter number of techniques',
                    min=0,
                    step=1
                ),

                # Input field for No. of Platforms
                html.Label("Number of Platform(s):"),
                dcc.Input(
                    id='platform-input',
                    type='number',
                    placeholder='Enter number of platforms',
                    min=0,
                    step=1
                ),

                # Button to submit the inputs
                html.Button('Submit', id='submit-button', n_clicks=0),
                
                # Placeholder for any results or outputs
                html.Div(id='output-container', style={'margin-top': '20px'})
            ])
        ])
    ])
])

# Define callback functions to update the graphs based on user inputs
@app.callback(
    dash.dependencies.Output("apt-platform-stacked-bar-chart", "figure"),
    [dash.dependencies.Input("apt-filter", "value"),
     dash.dependencies.Input("platform-filter", "value"),
     dash.dependencies.Input("cvss-slider", "value")]
)
def update_stacked_bar_chart(selected_apt, selected_platform, cvss_score):
    # Filter data based on selected APT, platform, and CVSS score
    df_filtered = df_expanded.copy()
    if selected_apt:
        df_filtered = df_filtered[df_filtered['APT'].isin(selected_apt)]
    if selected_platform:
        df_filtered = df_filtered[df_filtered['platform'].isin(selected_platform)]
    # For now, CVSS score is not applied. You can include it if needed.

    # Regroup data
    filtered_counts = df_filtered.groupby(['APT', 'platform']).size().reset_index(name='count')

    # Update the stacked bar chart
    return create_stacked_bar_chart(filtered_counts)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
