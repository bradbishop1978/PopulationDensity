import time
import re
import pandas as pd
import streamlit as st
import requests
from lxml import html

# Function to get the full text from the webpage using requests and lxml
def get_population_density_text(zip_code):
    # Construct the URL for the given zip code
    url = f"https://www.zip-codes.com/zip-code/{zip_code}/zip-code-{zip_code}.asp"
    
    # Send a GET request to the URL
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if request was successful
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return None
    
    # Parse the HTML content of the page with lxml
    tree = html.fromstring(response.content)
    
    # Use XPath to extract the population density text
    population_text = tree.xpath('//p[contains(text(), "population density of")]/text()')
    
    if population_text:
        return population_text[0]
    else:
        return None

# Function to extract population density from the full text
def extract_population_density(text):
    # Regular expression to extract the population density value
    match = re.search(r'population density of ([\d,]+(?:\.\d+)?) people per square mile', text)
    if match:
        return match.group(1)  # This will return the population density number
    else:
        return None

# Streamlit App
def main():
    st.title("Population Density Finder")

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV with zip codes in column A", type="csv")
    
    if uploaded_file is not None:
        # Read the uploaded CSV into a pandas DataFrame
        df = pd.read_csv(uploaded_file)
        
        # Make the column names lowercase for case-insensitive checking
        df.columns = df.columns.str.lower()

        # Check if the column 'zipcode' exists
        if 'zipcode' not in df.columns:
            st.error("The uploaded CSV must have a 'ZipCode' column (case-insensitive).")
            return
        
        # Display a button to initiate the search
        if st.button('Find Population Density'):
            # Create columns for the full text and population density
            df['Full Text'] = None
            df['Population Density'] = None
            
            # Progress bar setup
            progress_text = st.empty()  # Text to display progress (e.g., "1 of 10")
            progress_bar = st.progress(0)  # Progress bar that will be updated
            
            # Process the zip codes one by one and update progress bar
            for i, zip_code in enumerate(df['zipcode'], 1):
                # Update the progress bar and text
                progress_text.text(f"{i} of {len(df)}")
                progress_bar.progress(i / len(df))
                
                # Scrape population density text and extract value
                text = get_population_density_text(str(zip_code))
                df.at[i - 1, 'Full Text'] = text
                if text:
                    df.at[i - 1, 'Population Density'] = extract_population_density(text)
                else:
                    df.at[i - 1, 'Population Density'] = "Not Found"
                
                # Optional: Sleep between requests to avoid overloading the server
                time.sleep(1)

            # Display the resulting dataframe with the population densities
            st.write(df)
            
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
