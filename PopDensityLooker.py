import re
import time
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup

# Function to get the population density text using requests and BeautifulSoup
def get_population_density_text(zip_code):
    url = f"https://www.zip-codes.com/zip-code/{zip_code}/zip-code-{zip_code}.asp"
    
    # Set headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    try:
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find paragraphs that contain population density information
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                if p.text and 'population density of' in p.text:
                    return p.text.strip()
            
            return None
        else:
            st.warning(f"Failed to fetch data for zip code {zip_code}: HTTP {response.status_code}")
            return None
    except Exception as e:
        st.warning(f"Error for zip code {zip_code}: {e}")
        return None

# Function to extract population density from the full text
def extract_population_density(text):
    if not text:
        return None
        
    # Regular expression to extract the population density value
    match = re.search(r'population density of ([\d,]+(?:\.\d+)?) people per square mile', text)
    if match:
        return match.group(1)  # This will return the population density number
    else:
        return None

# Streamlit App
def main():
    st.title("Population Density Finder")
    st.write("Upload a CSV with zip codes to find population density information.")

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV with zip codes in a column named 'ZipCode'", type="csv")
    
    if uploaded_file is not None:
        # Read the uploaded CSV into a pandas DataFrame
        df = pd.read_csv(uploaded_file)
        
        # Make the column names lowercase for case-insensitive checking
        df.columns = df.columns.str.lower()

        # Check if the column 'zipcode' exists
        if 'zipcode' not in df.columns:
            st.error("The uploaded CSV must have a 'ZipCode' column (case-insensitive).")
            return
        
        # Display a preview of the data
        st.subheader("Preview of uploaded data")
        st.dataframe(df.head())
        
        # Display a button to initiate the search
        if st.button('Find Population Density'):
            # Create a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create columns for the full text and population density
            df['Full Text'] = None
            df['Population Density'] = None
            
            # Process the zip codes one by one and update progress bar
            for i, zip_code in enumerate(df['zipcode']):
                # Update the progress bar and text
                progress = (i + 1) / len(df)
                progress_bar.progress(progress)
                status_text.text(f"Processing {i + 1} of {len(df)} zip codes ({int(progress * 100)}%)")
                
                # Scrape population density text and extract value
                text = get_population_density_text(str(zip_code))
                df.at[i, 'Full Text'] = text
                if text:
                    df.at[i, 'Population Density'] = extract_population_density(text)
                else:
                    df.at[i, 'Population Density'] = "Not Found"
                
                # Sleep between requests to avoid overloading the server
                time.sleep(1)

            # Display the resulting dataframe with the population densities
            st.subheader("Results")
            st.dataframe(df)
            
            # Prepare the updated dataframe for download
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Updated CSV",
                data=csv,
                file_name="updated_zip_codes.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
