import re
import time
import pandas as pd
import streamlit as st
import urllib.request
from urllib.error import URLError, HTTPError

# Function to format zip codes (add leading zeros for 4-digit codes)
def format_zipcode(zip_code):
    """
    Format zip code to ensure it's 5 digits by adding leading zeros if needed.
    """
    # Convert to string and remove any whitespace
    zip_str = str(zip_code).strip()
    
    # Remove any non-digit characters except hyphens (for ZIP+4 format)
    if '-' in zip_str:
        # Handle ZIP+4 format (e.g., "12345-6789")
        parts = zip_str.split('-')
        main_zip = parts[0].zfill(5)  # Pad main zip to 5 digits
        if len(parts) > 1:
            return f"{main_zip}-{parts[1]}"
        return main_zip
    else:
        # Handle regular zip codes
        zip_digits = re.sub(r'\D', '', zip_str)  # Remove non-digits
        if len(zip_digits) == 4:
            return zip_digits.zfill(5)  # Add leading zero
        elif len(zip_digits) == 5:
            return zip_digits
        else:
            return zip_str  # Return original if not 4 or 5 digits

# Function to get the population density using only urllib with better encoding handling
def get_population_density(zip_code):
    # Format the zip code before making the request
    formatted_zip = format_zipcode(zip_code)
    url = f"https://www.zip-codes.com/zip-code/{formatted_zip}/zip-code-{formatted_zip}.asp"
    
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
            st.warning(f"Zip code {formatted_zip} not found (404 error)")
        else:
            st.warning(f"HTTP Error for zip code {formatted_zip}: {e.code} {e.reason}")
        return None
    except URLError as e:
        st.warning(f"URL Error for zip code {formatted_zip}: {e.reason}")
        return None
    except Exception as e:
        st.warning(f"Error for zip code {formatted_zip}: {str(e)}")
        return None

# Function to handle single zip code search
def search_single_zipcode(zip_code, delay=1.0):
    # Format the zip code
    formatted_zip = format_zipcode(zip_code)
    
    st.subheader(f"Searching for Zip Code: {formatted_zip}")
    
    # Show original vs formatted if they're different
    if str(zip_code).strip() != formatted_zip:
        st.info(f"Original input: {zip_code} → Formatted: {formatted_zip}")
    
    with st.spinner(f"Looking up population density for {formatted_zip}..."):
        # Add a small delay to simulate processing
        time.sleep(delay)
        
        # Get population density
        density = get_population_density(formatted_zip)
        
        # Display result
        if density:
            # Display result in a more prominent way
            st.success(f"Population Density for {formatted_zip}: {density} people per square mile")
            
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
                <h3>Result for Zip Code: {formatted_zip}</h3>
                <p><strong>Population Density:</strong> {density} people per square mile</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Could not find population density information for zip code {formatted_zip}")

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
    
    # Format all zip codes in the dataframe
    df['zipcode'] = df['zipcode'].apply(format_zipcode)
    
    # Display a preview of the data
    st.subheader("Preview of uploaded data (with formatted zip codes)")
    st.dataframe(df.head())
    
    # Show formatting summary
    original_df = pd.read_csv(uploaded_file, dtype={'ZipCode': str})
    original_df.columns = original_df.columns.str.lower()
    
    # Count how many zip codes were formatted
    formatted_count = sum(1 for orig, formatted in zip(original_df['zipcode'], df['zipcode']) 
                         if str(orig).strip() != str(formatted).strip())
    
    if formatted_count > 0:
        st.info(f"📝 Formatted {formatted_count} zip codes by adding leading zeros")
    
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
            
            # Get population density (zip_code is already formatted)
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
    
    # Add information about zip code formatting
    st.info("💡 **Tip:** 4-digit zip codes will automatically be formatted with a leading zero (e.g., 7482 → 07482)")
    
    # Add tabs for different search options
    tab1, tab2 = st.tabs(["Single Zip Code Search", "Batch CSV Processing"])
    
    # Tab 1: Single Zip Code Search
    with tab1:
        st.write("Enter a zip code to find its population density.")
        
        # Input for single zip code
        zip_code = st.text_input("Enter Zip Code", placeholder="e.g., 90210 or 7482")
        
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
                # Updated validation to accept 4 or 5 digit zip codes
                if re.match(r'^\d{4,5}(-\d{4})?$', zip_code.strip()):
                    search_single_zipcode(zip_code, delay)
                else:
                    st.error("Please enter a valid 4 or 5-digit zip code (or 9-digit with hyphen)")
            else:
                st.warning("Please enter a zip code to search")
    
    # Tab 2: Batch CSV Processing (existing functionality)
    with tab2:
        st.write("Upload a CSV with zip codes to find population density information.")
        st.write("**Note:** 4-digit zip codes in your CSV will automatically be formatted with leading zeros.")
        
        # Upload CSV file
        uploaded_file = st.file_uploader("Upload a CSV with zip codes in a column named 'ZipCode'", type="csv")
        
        if uploaded_file is not None:
            process_csv_file(uploaded_file)

if __name__ == "__main__":
    main()
