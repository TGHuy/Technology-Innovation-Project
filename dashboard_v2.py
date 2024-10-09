import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import dash
import networkx as nx
import plotly.express as px
from branca.colormap import linear
import folium
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output

# Load your dataset
excel = 'VisualAmended_v6.xlsx'  # Adjust to your file path
data_sheet = 'CleanedDataset'
df = pd.read_excel(excel, sheet_name=data_sheet)

# Split platforms by commas
df_expanded = df.assign(platform=df['platforms'].str.split(',')).explode('platform')
df_expanded['platform'] = df_expanded['platform'].str.strip()
df_expanded = df_expanded[df_expanded['CWE-ID'] != 'UNKNOWN']

# Identify the top 5 vulnerable platforms
platform_counts = df_expanded['platform'].value_counts()
top_5_platforms = platform_counts.head(5).index.tolist()

# Filter the data to include only the top 5 platforms
df_top_platforms = df_expanded[df_expanded['platform'].isin(top_5_platforms)]

# Group the data by APT and platform
apt_platform_counts = df_top_platforms.groupby(['APT', 'platform']).size().reset_index(name='count')

# Create a pivot table to count occurrences of each CWE per platform
platform_cwe_pivot = df_expanded.pivot_table(index='platform', columns='CWE-ID', aggfunc='size', fill_value=0)

# Filter out rows where either 'CWE-ID' is 'Unknown' and 'NVD-CWE-noinfo'
df_filtered = df[['CVE ID', 'CWE-ID']].dropna()
df_filtered = df_filtered[(df_filtered['CWE-ID'] != 'UNKNOWN') & (df_filtered['CWE-ID'] != 'NVD-CWE-noinfo')]

# Group the data by CWE and count the number of CVEs associated with each CWE
cwe_cve_count = df_filtered.groupby('CWE-ID').count().reset_index()
cwe_cve_count.columns = ['CWE-ID', 'CVE Count']

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the dashboard with buttons instead of dropdown
app.layout = html.Div([
    html.H1("Interactive Dashboard for Platforms and CVE/CWE", style={'textAlign': 'center'}),

    # Create buttons for CVE, Platform, and CWE sections
    html.Div([
        html.Button('CVE Diagram', id='cve-button', n_clicks=0, className='button-83'),
        html.Button('Platform Diagram', id='platform-button', n_clicks=0, className='button-83'),
        html.Button('CWE Heatmap', id='cwe-button', n_clicks=0, className='button-83')
    ], style={'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'height': '50vh'}),

    # Div to display the selected content dynamically
    html.Div(id='section-content', style={'marginTop': 20})
])


# Define the callback to update content based on the clicked button
@app.callback(Output('section-content', 'children'),
              [Input('cve-button', 'n_clicks'),
               Input('platform-button', 'n_clicks'),
               Input('cwe-button', 'n_clicks')])
def render_content(cve_clicks, platform_clicks, cwe_clicks):
    # Determine which button was clicked
    if cve_clicks > platform_clicks and cve_clicks > cwe_clicks:
        # CVE Section: Display the bar chart for CWE and CVE
        fig = px.bar(
            cwe_cve_count,
            x='CWE-ID',
            y='CVE Count',
            title='Bar Chart of Number of CVEs Associated with Each CWE (MANTHI)',
            labels={'CWE-ID': 'CWE-ID', 'CVE Count': 'Number of CVEs'}
        )
        fig.update_xaxes(tickangle=90)  # Rotate x-axis labels for better readability
        return html.Div([
            html.H3('CVE-Related Bar Chart'),
            dcc.Graph(figure=fig)
        ])

    elif platform_clicks > cve_clicks and platform_clicks > cwe_clicks:
        # Platform Section: Show filters and stacked bar chart
        return html.Div([
            html.H3("Platform-Related Visualizations"),
            # Filters (Dropdowns and Slider)
            html.Div([
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
                )
            ], style={'width': '50%', 'margin': 'auto'}),
            # Stacked Bar Chart
            html.Div([
                dcc.Graph(id="apt-platform-stacked-bar-chart",
                          figure=create_stacked_bar_chart(apt_platform_counts))
            ], style={'width': '75%', 'margin': 'auto'})
        ])

    elif cwe_clicks > cve_clicks and cwe_clicks > platform_clicks:
        # CWE Section: Display a heatmap related to CWE
        pivot_table = df_expanded.pivot_table(index='platform', columns='CWE-ID', aggfunc='size', fill_value=0)
        heatmap = go.Figure(go.Heatmap(
            z=pivot_table.values,
            x=pivot_table.columns,
            y=pivot_table.index,
            colorscale='sunset'
        ))
        heatmap.update_layout(title='Heatmap of CWE Occurrences Across Platforms')
        return html.Div([
            html.H3('CWE-Related Visualizations'),
            dcc.Graph(figure=heatmap)
        ])


# Callback to update the stacked bar chart based on filters
@app.callback(
    Output("apt-platform-stacked-bar-chart", "figure"),
    [Input("apt-filter", "value"),
     Input("platform-filter", "value"),
     Input("cvss-slider", "value")]
)
def update_stacked_bar_chart(selected_apt, selected_platform, cvss_score):
    # Filter data based on selected APT, platform, and CVSS score
    df_filtered = df_expanded.copy()
    if selected_apt:
        df_filtered = df_filtered[df_filtered['APT'].isin(selected_apt)]
    if selected_platform:
        df_filtered = df_filtered[df_filtered['platform'].isin(selected_platform)]

    # Regroup data
    filtered_counts = df_filtered.groupby(['APT', 'platform']).size().reset_index(name='count')

    # Update the stacked bar chart
    return create_stacked_bar_chart(filtered_counts)


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

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
