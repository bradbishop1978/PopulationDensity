import re
import time
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# Function to get the population density text using requests and BeautifulSoup
def get_population_density_text(zip_code):
    url = f"https://www.zip-codes.com/zip-code/{zip_code}/zip-code-{zip_code}.asp"
    
    # Set headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find paragraphs that contain population density information
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            if p.text and 'population density of' in p.text:
                return p.text.strip()
        
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data for zip code {zip_code}: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error for zip code {zip_code}: {e}")
        return None

# Function to extract population density from the full text
def extract_population_density(text):
    if not text:
        return None
        
    # Regular expression to extract the population density value
    match = re.search(r'population density of ([\d,]+(?:\.\d+)?) people per square mile', text)
    if match:
        # Remove commas and convert to float
        density = match.group(1).replace(',', '')
        try:
            return float(density)
        except ValueError:
            return density
    else:
        return None

# Function to process a single zip code
def process_zip_code(zip_code):
    # Add a small delay to avoid overwhelming the server
    time.sleep(0.5)
    
    text = get_population_density_text(str(zip_code))
    density = extract_population_density(text) if text else None
    
    return {
        'zipcode': zip_code,
        'Full Text': text,
        'Population Density': density if density is not None else "Not Found"
    }

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
        
        # Display the total number of zip codes
        total_zip_codes = len(df)
        st.write(f"Total zip codes to process: {total_zip_codes}")
        
        # Options for processing
        st.subheader("Processing Options")
        
        # Option to use parallel processing
        use_parallel = st.checkbox("Use parallel processing (faster but may get blocked)", value=False)
        
        max_workers = 1
        if use_parallel:
            max_workers = st.slider("Number of parallel workers", min_value=2, max_value=5, value=3, 
                                   help="More workers = faster, but higher chance of being blocked")
        
        # Display a button to initiate the search
        if st.button('Find Population Density'):
            # Create a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create a new DataFrame to store results
            results = []
            
            with st.spinner('Processing zip codes...'):
                if use_parallel:
                    # Process zip codes in parallel
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all tasks and get future objects
                        future_to_zipcode = {executor.submit(process_zip_code, zip_code): zip_code 
                                            for zip_code in df['zipcode']}
                        
                        # Process results as they complete
                        for i, future in enumerate(future_to_zipcode):
                            try:
                                result = future.result()
                                results.append(result)
                            except Exception as e:
                                st.error(f"Error processing zip code: {e}")
                                results.append({
                                    'zipcode': future_to_zipcode[future],
                                    'Full Text': None,
                                    'Population Density': f"Error: {str(e)}"
                                })
                            
                            # Update progress
                            progress = (i + 1) / total_zip_codes
                            progress_bar.progress(progress)
                            status_text.text(f"Processed {i + 1} of {total_zip_codes} zip codes ({int(progress * 100)}%)")
                else:
                    # Process zip codes sequentially
                    for i, zip_code in enumerate(df['zipcode']):
                        result = process_zip_code(zip_code)
                        results.append(result)
                        
                        # Update progress
                        progress = (i + 1) / total_zip_codes
                        progress_bar.progress(progress)
                        status_text.text(f"Processed {i + 1} of {total_zip_codes} zip codes ({int(progress * 100)}%)")
            
            # Convert results to DataFrame
            results_df = pd.DataFrame(results)
            
            # Merge with original DataFrame to preserve other columns
            merged_df = pd.merge(df, results_df[['zipcode', 'Full Text', 'Population Density']], 
                                on='zipcode', how='left')
            
            # Display the resulting dataframe with the population densities
            st.subheader("Results")
            st.dataframe(merged_df)
            
            # Show statistics
            st.subheader("Statistics")
            found_count = merged_df['Population Density'].apply(
                lambda x: x != "Not Found" and not str(x).startswith("Error")
            ).sum()
            
            st.write(f"Successfully found data for {found_count} out of {total_zip_codes} zip codes ({found_count/total_zip_codes:.1%})")
            
            # Prepare the updated dataframe for download
            csv = merged_df.to_csv(index=False)
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name="population_density_results.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
