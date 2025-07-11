import streamlit as st
import pandas as pd
import geopandas
import pydeck as pdk
import json
from urllib.request import urlopen
import re

# Function to format zip codes (add leading zeros for 4-digit codes)
def format_zipcode(zip_code):
    """Format zip code to ensure it's 5 digits by adding leading zeros if needed."""
    zip_str = str(zip_code).strip()
    zip_digits = re.sub(r'\D', '', zip_str)  # Remove non-digits
    if len(zip_digits) == 4:
        return zip_digits.zfill(5)  # Add leading zero
    elif len(zip_digits) == 5:
        return zip_digits
    else:
        return zip_str  # Return original if not 4 or 5 digits

# Function to load GeoJSON data
@st.cache_data
def load_geojson(url):
    with urlopen(url) as response:
        geojson_data = json.load(response)
    return geojson_data

# Function to load data
@st.cache_data
def load_data(url):
    df = pd.read_csv(url, dtype={'zip': str})
    df.rename(columns={'zip': 'ZipCode'}, inplace=True)
    return df

# Function to create GeoDataFrame
@st.cache_data
def create_geodataframe(df, geojson):
    gdf = geopandas.GeoDataFrame.from_features(geojson['features'])
    gdf = gdf.rename(columns={'zip': 'ZipCode'})
    gdf['ZipCode'] = gdf['ZipCode'].astype(str)
    merged = gdf.merge(df, on='ZipCode', how='left')
    merged['density'] = merged['population'] / merged.area
    return merged

# Function to create pydeck layer
def create_pydeck_layer(merged, color_range):
    layer = pdk.Layer(
        "GeoJsonLayer",
        merged.__geo_interface__,
        opacity=0.8,
        stroked=False,
        filled=True,
        extruded=False,
        get_fill_color=f"{{properties.density > {color_range[0]} && properties.density <= {color_range[1]} ? [255, 0, 0, 255] :\
                         properties.density > {color_range[1]} && properties.density <= {color_range[2]} ? [255, 128, 0, 255] :\
                         properties.density > {color_range[2]} && properties.density <= {color_range[3]} ? [255, 255, 0, 255] :\
                         properties.density > {color_range[3]} && properties.density <= {color_range[4]} ? [0, 255, 0, 255] :\
                         properties.density > {color_range[4]} ? [0, 0, 255, 255] : [128, 128, 128, 255]}}",
        get_line_color=[255, 255, 255],
        get_line_width=1,
        pickable=True,
        auto_highlight=True
    )
    return layer

# Function to process uploaded CSV file
def process_csv_file(uploaded_file):
    if uploaded_file is not None:
        try:
            uploaded_file.seek(0)
            original_df = pd.read_csv(uploaded_file, dtype={'ZipCode': str})

            # Check if 'ZipCode' column exists
            if 'ZipCode' not in original_df.columns:
                st.error("The uploaded CSV file must contain a column named 'ZipCode'.")
                return None

            # Check if 'population' column exists
            if 'population' not in original_df.columns:
                st.error("The uploaded CSV file must contain a column named 'population'.")
                return None

            # Basic data validation (example: check for non-numeric population)
            if not pd.to_numeric(original_df['population'], errors='coerce').notna().all():
                st.error("The 'population' column contains non-numeric values. Please ensure it contains only numbers.")
                return None

            # Format all zip codes in the dataframe
            original_df['ZipCode'] = original_df['ZipCode'].apply(format_zipcode)

            return original_df
        except Exception as e:
            st.error(f"Error processing the uploaded CSV file: {e}")
            return None
    return None

# Main Streamlit app
def main():
    st.title("Zip Code Population Density Viewer")

    # Sidebar options
    data_source = st.sidebar.radio("Select Data Source:", ["Preloaded Data", "Upload CSV"])

    if data_source == "Preloaded Data":
        # URL for the GeoJSON data
        geojson_url = "https://raw.githubusercontent.com/OpenDataDE/Germany-zip-codes/main/geojson/zip_codes_germany.geojson"
        # URL for the CSV data
        csv_url = "https://raw.githubusercontent.com/plotly/datasets/master/2011_us_ag_exports.csv"

        # Load data
        geojson_data = load_geojson(geojson_url)
        df = load_data(csv_url)

    elif data_source == "Upload CSV":
        uploaded_file = st.sidebar.file_uploader("Upload your CSV file", type="csv")
        if uploaded_file is not None:
            df = process_csv_file(uploaded_file)
            if df is None:
                return  # Stop if there's an error in processing the CSV

            # URL for the GeoJSON data (still needed for zip code boundaries)
            geojson_url = "https://raw.githubusercontent.com/OpenDataDE/Germany-zip-codes/main/geojson/zip_codes_germany.geojson"
            geojson_data = load_geojson(geojson_url)

        else:
            st.info("Please upload a CSV file to proceed.")
            return  # Stop if no file is uploaded

    else:
        st.error("Invalid data source selected.")
        return

    # Color range selection
    st.sidebar.header("Density Color Range")
    color_range = [
        st.sidebar.number_input("Range 1 (Red): Max Density", value=100),
        st.sidebar.number_input("Range 2 (Orange): Max Density", value=500),
        st.sidebar.number_input("Range 3 (Yellow): Max Density", value=1000),
        st.sidebar.number_input("Range 4 (Green): Max Density", value=2000),
        st.sidebar.number_input("Range 5 (Blue): Max Density", value=5000)
    ]

    # Create GeoDataFrame
    try:
        merged = create_geodataframe(df, geojson_data)
    except Exception as e:
        st.error(f"Error creating GeoDataFrame: {e}.  Check that your CSV has 'ZipCode' and 'population' columns.")
        return

    # Create pydeck layer
    layer = create_pydeck_layer(merged, color_range)

    # Set initial viewport
    view_state = pdk.ViewState(
        latitude=51.5,
        longitude=10.5,
        zoom=5,
        pitch=0
    )

    # Render map
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "ZipCode: {properties.ZipCode}\nDensity: {properties.density}"}
    )

    st.pydeck_chart(r)

if __name__ == "__main__":
    main()
