import re
import time
import pandas as pd
import streamlit as st
import urllib.request
from urllib.error import URLError, HTTPError

# Function to normalize zip codes (add leading zero for 4-digit zip codes)
def normalize_zipcode(zip_code):
    """
    Normalize zip code by adding leading zero for 4-digit zip codes.
    
    Args:
        zip_code (str): Input zip code
        
    Returns:
        str: Normalized zip code with leading zero if needed
    """
    # Convert to string and strip whitespace
    zip_code = str(zip_code).strip()
    
    # Handle 4-digit zip codes by adding leading zero
    if re.match(r'^\d{4}$', zip_code):
        return '0' + zip_code
    
    # Handle 4-digit zip codes with hyphen extension (e.g., "1234-5678")
    if re.match(r'^\d{4}-\d{4}$', zip_code):
        return '0' + zip_code
    
    # Return as-is for other formats (5-digit, 9-digit, etc.)
    return zip_code

# Function to validate zip code format after normalization
def is_valid_zipcode(zip_code):
    """
    Validate if zip code is in correct format after normalization.
    
    Args:
        zip_code (str): Zip code to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    # Check for 5-digit or 9-digit (5+4) format
    return bool(re.match(r'^\d{5}(-\d{4})?$', zip_code))

# Function to get the population density using only urllib with better encoding handling
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
            # Read the raw bytes
            html_bytes = response.read()
            
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
            html = None
            
            for encoding in encodings:
                try:
                    html = html_bytes.decode(encoding, errors='replace')
                    break  # If successful, break the loop
                except UnicodeDecodeError:
                    continue
            
            if html is None:
                # If all encodings fail, use 'replace' mode with utf-8
                html = html_bytes.decode('utf-8', errors='replace')
            
            # Use regex to find population density directly in the HTML
            pattern = r'population density of ([\d,]+(?:\.\d+)?) people per square mile'
            match = re.search(pattern, html)
            
            if match:
                return match.group(1)  # Return the population density value
            else:
                # Try an alternative pattern in case the format is different
                alt_pattern = r'Population\s+Density</td>\s*<td[^>]*>([\d,\.]+)'
                alt_match = re.search(alt_pattern, html)
                if alt_match:
                    return alt_match.group(1)
                return None
    except HTTPError as e:
        if e.code == 404:
            st.warning(f"Zip code {zip_code} not found (404 error)")
        else:
            st.warning(f"HTTP Error for zip code {zip_code}: {e.code} {e.reason}")
        return None
    except URLError as e:
        st.warning(f"URL Error for zip code {zip_code}: {e.reason}")
        return None
    except Exception as e:
        st.warning(f"Error for zip code {zip_code}: {str(e)}")
        return None

# Function to handle single zip code search
def search_single_zipcode(zip_code, delay=1.0):
    st.subheader(f"Searching for Zip Code: {zip_code}")
    
    with st.spinner(f"Looking up population density for {zip_code}..."):
        # Add a small delay to simulate processing
        time.sleep(delay)
        
        # Get population density
        density = get_population_density(zip_code)
        
        # Display result
        if density:
            # Display result in a more prominent way
            st.success(f"Population Density for {zip_code}: {density} people per square mile")
            
            # Display result in a formatted box
            st.markdown("""
            <style>
            .result-box {
                background-color: #000000;
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="result-box">
                <h3>Result for Zip Code: {zip_code}</h3>
                <p><strong>Population Density:</strong> {density} people per square mile</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Could not find population density information for zip code {zip_code}")

# Function to process CSV file
def process_csv_file(uploaded_file, delay=1.0):
    # Read the uploaded CSV into a pandas DataFrame
    df = pd.read_csv(uploaded_file, dtype={'ZipCode': str})
    
    # Make the column names lowercase for case-insensitive checking
    df.columns = df.columns.str.lower()
    # Check if the column 'zipcode' exists
    if 'zipcode' not in df.columns:
        st.error("The uploaded CSV must have a 'ZipCode' column (case-insensitive).")
        return
    
    # Normalize zip codes in the dataframe
    df['zipcode'] = df['zipcode'].apply(normalize_zipcode)
    
    # Display a preview of the data
    st.subheader("Preview of uploaded data (with normalized zip codes)")
    st.dataframe(df.head())
    
    # Add options for processing
    st.subheader("Processing Options")
    
    delay = st.slider(
        "Delay between requests (seconds)", 
        min_value=0.5, 
        max_value=5.0, 
        value=1.0, 
        step=0.5,
        help="Longer delay reduces the chance of being blocked by the website"
    )
    
    # Display a button to initiate the search
    if st.button('Find Population Density'):
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create a column for population density
        df['Population Density'] = None
        
        # Create counters for statistics
        success_count = 0
        not_found_count = 0
        
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
                success_count += 1
            else:
                df.at[i, 'Population Density'] = "Not Found"
                not_found_count += 1
            
            # Sleep between requests to avoid overloading the server
            time.sleep(delay)
        
        # Display statistics
        st.subheader("Processing Statistics")
        st.write(f"✅ Successfully found: {success_count} ({success_count/len(df):.1%})")
        st.write(f"❌ Not found: {not_found_count} ({not_found_count/len(df):.1%})")
        
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

# Streamlit App
def main():
    st.title("Population Density Finder")
    
    # Add information about zip code handling
    st.info("💡 **Tip:** This app automatically handles 4-digit zip codes by adding a leading zero (e.g., 1234 becomes 01234)")
    
    # Add tabs for different search options
    tab1, tab2 = st.tabs(["Single Zip Code Search", "Batch CSV Processing"])
    
    # Tab 1: Single Zip Code Search
    with tab1:
        st.write("Enter a zip code to find its population density.")
        
        # Input for single zip code
        zip_code = st.text_input("Enter Zip Code", placeholder="e.g., 90210 or 1234")
        
        # Add delay option
        delay = st.slider(
            "Request delay (seconds)", 
            min_value=0.0, 
            max_value=3.0, 
            value=0.5, 
            step=0.5,
            help="Delay before showing results"
        )
        
        # Search button
        if st.button("Search", key="single_search"):
            if zip_code:
                # Normalize the zip code first
                normalized_zip = normalize_zipcode(zip_code)
                
                # Show normalization if it occurred
                if normalized_zip != zip_code:
                    st.info(f"Normalized zip code: {zip_code} → {normalized_zip}")
                
                # Validate normalized zip code format
                if is_valid_zipcode(normalized_zip):
                    search_single_zipcode(normalized_zip, delay)
                else:
                    st.error("Please enter a valid 4 or 5-digit zip code (or 9-digit with hyphen)")
            else:
                st.warning("Please enter a zip code to search")
    
    # Tab 2: Batch CSV Processing (existing functionality)
    with tab2:
        st.write("Upload a CSV with zip codes to find population density information.")
        st.write("**Note:** 4-digit zip codes will be automatically normalized by adding a leading zero.")
        
        # Upload CSV file
        uploaded_file = st.file_uploader("Upload a CSV with zip codes in a column named 'ZipCode'", type="csv")
        
        if uploaded_file is not None:
            process_csv_file(uploaded_file)

if __name__ == "__main__":
    main()
