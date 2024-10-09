#Group data by Region (country) to get the frequency of apartments
region_frequency = df.groupby('Region').size().reset_index(name='region_count')

# Load country boundaries as GeoDataFrame from the specified shapefile
geojson_path = r'ne_10m_admin_0_countries.shp'  # Update this path
world = gpd.read_file(geojson_path)

# Check the columns in your GeoDataFrame
print(world.columns)

# Convert the 'NAME' in English and 'Region' columns to string before merging
world['NAME_EN'] = world['NAME'].astype(str)
region_frequency['Region'] = region_frequency['Region'].astype(str)

# Merge world boundaries with the region frequency data
world_with_data = world.merge(region_frequency, left_on='NAME_EN', right_on='Region', how='left')

# Initialize a folium map centered on the world
m = folium.Map(location=[20, 0], zoom_start=2)

# Create a color scale for the region counts
colormap = linear.YlOrRd_09.scale(world_with_data['region_count'].min(), world_with_data['region_count'].max())

# Define a function to determine the style of each country
def style_function(feature):
    region_count = feature['properties'].get('region_count', 0)
    if pd.isna(region_count) or region_count == 0:
        return {
            'fillColor': 'white',  # Color for regions with no data
            'color': 'black',  # Border color
            'weight': 1.0,  # Border weight
            'fillOpacity': 1,  # Full opacity for no data regions
        }
    else:
        return {
            'fillColor': colormap(region_count),  # Scale based on region_count
            'color': 'black',
            'weight': 1.0,
            'fillOpacity': 0.7,
        }

# Create a GeoJson layer with styling
folium.GeoJson(
    world_with_data,
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(fields=['NAME_EN', 'region_count'])  # Tooltip to show country name and count
).add_to(m)

# Add country boundaries to the map (for visual clarity)
folium.GeoJson(
    world,
    style_function=lambda feature: {
        'fillColor': 'transparent',  # Make the fill color transparent
        'color': 'black',  # Border color
        'weight': 1.0,  # Border weight
        'fillOpacity': 0  # No fill opacity
    },
).add_to(m)

# Add a color legend to the map
colormap.caption = 'APT Density'
colormap.add_to(m)

# Display the map
m
