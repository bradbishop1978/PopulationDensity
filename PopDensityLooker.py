import re
import time
import pandas as pd
import streamlit as st
import urllib.request

# Function to get the population density using only urllib and regex
def get_population_density(zip_code):
    url = f"https://www.zip-codes.com/zip-code/{zip_code}/zip-code-{zip_code}.asp"
    
    try:
        # Create a request with a user agent
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        # Make the request
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Use regex to find population density directly in the HTML
            pattern = r'population density of ([\d,]+(?:\.\d+)?) people per square mile'
            match = re.search(pattern, html)
            
            if match:
                return match.group(1)  # Return the population density value
            else:
                return None
    except Exception as e:
        st.warning(f"Error for zip code {zip_code}: {e}")
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
            
            # Create a column for population density
            df['Population Density'] = None
            
            # Process the zip codes one by one and update progress bar
            for i, zip_code in enumerate(df['zipcode']):
                # Update the progress bar and text
                progress = (i + 1) / len(df)
                progress_bar.progress(progress)
                status_text.text(f"Processing {i + 1} of {len(df)} zip codes ({int(progress * 100)}%)")
                
                # Get population density
                density = get_population_density(str(zip_code))
                if density:
                    df.at[i, 'Population Density'] = density
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
