import streamlit as st
st.set_page_config(layout="wide")

import pandas as pd
from datetime import datetime, timezone
import time
import re
import urllib.request
from urllib.error import URLError, HTTPError

# Add this at the top of your script - Auto-refresh functionality
# Cache control with TTL
st.cache_data.clear()  # Clear cache on app startup

# Set a TTL (Time To Live) for all cached functions
@st.cache_data(ttl=300)  # Cache expires after 5 minutes
def load_csv_data(file_path):
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"File not found. Please ensure '{file_path}' is in the correct path.")
        return None

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

# Add refresh controls in sidebar
with st.sidebar:
    st.title("Data Refresh Controls")
    last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    refresh_text = st.empty()
    refresh_text.info(f"Last refreshed: {last_refresh}")
    
    if st.button("🔄 Refresh Data Now"):
        st.cache_data.clear()
        st.success("Data refreshed! The latest changes should now be visible.")
        st.rerun()  # Changed from st.experimental_rerun()
    
    auto_refresh = st.checkbox("Enable auto-refresh", value=False)
    if auto_refresh:
        refresh_interval = st.slider("Refresh interval (minutes)", 
                                    min_value=1, 
                                    max_value=60, 
                                    value=5)
        
        # Convert minutes to seconds for the countdown
        refresh_seconds = refresh_interval * 60
        
        # Create a placeholder for the countdown
        countdown_placeholder = st.empty()
        
        # Use a non-blocking approach for the countdown
        # This will only update when the page is active
        if "countdown_start" not in st.session_state:
            st.session_state.countdown_start = time.time()
            
        elapsed = time.time() - st.session_state.countdown_start
        remaining = max(0, refresh_seconds - int(elapsed))
        
        if remaining <= 0:
            st.cache_data.clear()
            st.session_state.countdown_start = time.time()
            st.rerun()  # Changed from st.experimental_rerun()
        else:
            mins, secs = divmod(remaining, 60)
            countdown_placeholder.info(f"Next refresh in: {int(mins)}m {int(secs)}s")

# Logo URL
logo_url = "https://raw.githubusercontent.com/bradbishop1978/store-search-app/16a6f28ccce5db3711f78c060c1f29b98a84f8c1/Primary%20Logo.jpg"

# Create a single column for the logo and title
col = st.container()

with col:
    # Use HTML to align the logo and title
    st.markdown(
        f"""
        <div style="display: flex; align-items: center;">
            <img src="{logo_url}" width="150" height="60" style="margin-right: 50px;">
            <h1 style="margin: 0;">Store Information Search</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

# Load CSV data using the cached function
data = load_csv_data('merged_df.csv')
if data is None:
    st.stop()

# Load additional CSV data using the cached function
order_details = load_csv_data('orderdetails.csv')
if order_details is None:
    st.stop()

# Initialize session state for selected store and input
if 'selected_store' not in st.session_state:
    st.session_state.selected_store = ""
if 'store_name_input' not in st.session_state:
    st.session_state.store_name_input = ""
if 'full_address_input' not in st.session_state:
    st.session_state.full_address_input = ""
if 'single_address_input' not in st.session_state:
    st.session_state.single_address_input = ""
if 'single_address_result' not in st.session_state:
    st.session_state.single_address_result = None

# Helper functions
def format_value(value):
    if pd.isna(value):
        return "-"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)

def format_price(value):
    if pd.isna(value) or value == '-':
        return "$0.00"
    try:
        return f"${float(value) / 100:.2f}"  # Convert to float and divide by 100 for cents
    except (ValueError, TypeError):
        return "$0.00"

# Example usage to demonstrate the fix
print(format_price(1000))         # Should print: $10.00
print(format_price('-'))          # Should print: $0.00
print(format_price(None))         # Should print: $0.00
print(format_price('invalid'))    # Should print: $0.00

def format_date(date_value):
    # Convert to datetime, coercing errors
    date_value = pd.to_datetime(date_value, errors='coerce')
    
    # Check if date_value is NaT
    if pd.isna(date_value):
        return "-"
    
    # Now it is safe to call strftime since it is a valid datetime
    return date_value.strftime('%m/%d/%Y')

def time_elapsed(order_date):
    if pd.isna(order_date):
        return "-"
    order_date = pd.to_datetime(order_date)  # Convert to datetime
    now = datetime.now(timezone.utc)  # Current UTC time
    delta = now - order_date

    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
    elif delta.seconds // 3600 > 0:
        return f"{delta.seconds // 3600} hour{'s' if delta.seconds // 3600 != 1 else ''} ago"
    elif delta.seconds // 60 > 0:
        return f"{delta.seconds // 60} minute{'s' if delta.seconds // 60 != 1 else ''} ago"
    else:
        return "Just now"

def format_store_status(status):
    if status == "Offboard":
        return "<span style='color:red; font-style:italic;'>Offboard</span>"
    return status if status and status != "-" else "LSM Active"

# Function to extract zip code from an address
def extract_zip_code(address):
    # Common US zip code pattern (5 digits, optionally followed by dash and 4 more digits)
    zip_pattern = r'\b(\d{5}(?:-\d{4})?)\b'
    match = re.search(zip_pattern, address)
    if match:
        # Return just the 5-digit part if it's a ZIP+4
        return match.group(1).split('-')[0]
    return None

# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["Store Search", "Single Address Search", "Performance Data📊"])

with tab1:
    # Input for store name
    store_name = st.text_input("Enter Store Name (case insensitive):", value=st.session_state.store_name_input, key="store_name_tab1")

    # Additional input for full address
    full_address = st.text_input("Enter Full Address (case insensitive):", value=st.session_state.full_address_input, key="full_address_tab1")

    # Clear button functionality
    if st.button("Clear", key="clear_button_tab1"):
        st.session_state.selected_store = ""
        st.session_state.store_name_input = ""
        st.session_state.full_address_input = ""
        store_name = ""
        full_address = ""

    # Reset the selected store if either the store name or full address is typed
    if store_name != st.session_state.store_name_input or full_address != st.session_state.full_address_input:
        st.session_state.selected_store = ""
        st.session_state.store_name_input = store_name
        st.session_state.full_address_input = full_address

    # Check if the user input matches any store name exactly
    if store_name:
        input_lower = store_name.lower()
        exact_match = data[data['store_name'].str.lower() == input_lower]

        if not exact_match.empty:
            st.session_state.selected_store = exact_match['store_name'].iloc[0]  # Update selected store

        # Suggest stores if there's no exact match
        if st.session_state.selected_store == "":
            matching_stores = data[data['store_name'].str.lower().str.contains(input_lower)]
            if not matching_stores.empty:
                st.subheader("Suggested Stores:")
                for index, row in matching_stores.iterrows():
                    if st.button(f"{row['store_name']}", key=f"store_button_{index}"):
                        st.session_state.selected_store = row['store_name']
                        st.session_state.store_name_input = row['store_name']
                        st.session_state.full_address_input = ""  # Clear address input
                        break  # Reset suggestions on selection

    # Check if the user input matches any full address
    if full_address:
        input_full_address_lower = full_address.lower()
        matching_addresses = data[data['full_address'].str.lower().str.contains(input_full_address_lower)]

        if not matching_addresses.empty:
            st.subheader("Suggested Addresses:")
            for index, row in matching_addresses.iterrows():
                if st.button(f"{row['full_address']}", key=f"address_button_{index}"):
                    # When an address is selected, set the corresponding store
                    st.session_state.selected_store = row['store_name']
                    st.session_state.store_name_input = row['store_name']
                    st.session_state.full_address_input = ""  # Clear address input
                    break  # Reset suggestions on selection

    # Assign values for the text inputs from the session state
    store_name = st.session_state.store_name_input
    full_address = st.session_state.full_address_input

    # Display information if a specific store has been chosen
    if st.session_state.selected_store:
        selected_store = st.session_state.selected_store
        filtered_data = data[data['store_name'].str.lower() == selected_store.lower()]

        if not filtered_data.empty:
            col1, col2, col3, col7 = st.columns(4)

            with col1:
                st.write("### Store Info")
                st.write("**Company:**", format_value(filtered_data['company_name'].iloc[0] if 'company_name' in filtered_data.columns else '-'))
                st.write("**LSM ID:**", f"[{format_value(filtered_data['store_id'].iloc[0])}](https://www.lulastoremanager.com/stores/{filtered_data['store_id'].iloc[0]})" if 'store_id' in filtered_data.columns else '-')
                st.write("**Comp ID:**", format_value(filtered_data['company_id'].iloc[0] if 'company_id' in filtered_data.columns else '-'))
                st.write("**Store Add:**", format_value(filtered_data['full_address'].iloc[0] if 'full_address' in filtered_data.columns else '-'))

            with col2:
                st.write("### Login Info")
                st.write("**Email:**", format_value(filtered_data['email'].iloc[0] if 'email' in filtered_data.columns else '-'))
                last_login_at = filtered_data['last_login_at'].iloc[0] if 'last_login_at' in filtered_data.columns else '-'

                if pd.notna(last_login_at):  # Check for valid datetime
                    login_date = pd.to_datetime(last_login_at)
                    days_since_login = (datetime.now(timezone.utc) - login_date).days
                    st.write("**Login since:**", f"{days_since_login} day{'s' if days_since_login != 1 else ''} ago")
                else:
                    st.write("**Login since:**", "-")

                st.write("**Role Name:**", format_value(filtered_data['role_name'].iloc[0] if 'role_name' in filtered_data.columns else '-'))
                st.write("**Phone No:**", format_value(filtered_data['phone_number'].iloc[0] if 'phone_number' in filtered_data.columns else '-'))

            with col3:
                st.write("### D S P Info")
                st.write("**UberEats ID:**", format_value(filtered_data['ubereats_id'].iloc[0] if 'ubereats_id' in filtered_data.columns else '-'))
                st.write("**DoorDash ID:**", format_value(filtered_data['doordash_id'].iloc[0] if 'doordash_id' in filtered_data.columns else '-'))
                st.write("**GrubHub ID:**", format_value(filtered_data['grubhub_id'].iloc[0] if 'grubhub_id' in filtered_data.columns else '-'))

            # Extract order details based on the selected store
            store_orders = order_details[order_details['store_name'].str.lower() == selected_store.lower()]

            if not store_orders.empty:
                store_orders['order_date'] = pd.to_datetime(store_orders['order_date'], errors='coerce')  # Ensure date column is parsed
                latest_order = store_orders.loc[store_orders['order_date'].idxmax()]
                elapsed_time = time_elapsed(latest_order['order_date'])  # Calculate elapsed time
                order_status = latest_order.get('status', "N/A")
                order_amount = latest_order.get('order_total', 0)
                order_amount_str = f"${order_amount:.2f}" if order_amount else "$0.00"  # Show as dollar amount
                dsp = format_value(latest_order.get('delivery_platform', '-'))

                with col7:
                    st.write("### Last Order Info")
                    st.write("**Order since:**", elapsed_time)  # Display time since order
                    st.write("**Status:**", format_value(order_status))
                    st.write("**Amount:**", order_amount_str)  # Show correct amount directly
                    st.write("**DSP:**", format_value(dsp))
            else:
                with col7:
                    st.write("### Last Order Info")
                    st.markdown("<span style='color:red; font-style:italic;'>No orders found for this store within 30 days.</span>", unsafe_allow_html=True)

            # Create second row of columns (4-7 + col8)
            col4, col5, col6, col8 = st.columns(4)

            with col4:
                st.write("### Add'l info")
                st.write("**Store Email:**", format_value(filtered_data['store_email'].iloc[0] if 'store_email' in filtered_data.columns else '-'))
                st.write("**Store Phone:**", format_value(filtered_data['store_phone'].iloc[0] if 'store_phone' in filtered_data.columns else '-'))
                st.write("**Created Date:**", format_date(filtered_data['created_date'].iloc[0] if 'created_date' in filtered_data.columns else '-'))

                if 'store_status' in filtered_data.columns and not filtered_data['store_status'].isnull().all():
                    store_status = filtered_data['store_status'].iloc[0]
                    st.markdown("**Store Status:** " + format_store_status(store_status), unsafe_allow_html=True)
                else:
                    st.markdown("**Store Status:** LSM Active", unsafe_allow_html=True)

            with col5:
                st.write("### Subscription")
                st.write("**Stripe ID:**", f"[{format_value(filtered_data['stripe_customer_id'].iloc[0])}](https://dashboard.stripe.com/customers/{filtered_data['stripe_customer_id'].iloc[0]})" if 'stripe_customer_id' in filtered_data.columns else '-')

                subs_status = filtered_data['subscription_status'].iloc[0] if 'subscription_status' in filtered_data.columns else None

                if subs_status and isinstance(subs_status, str):
                    if subs_status.lower() == "past_due":
                        st.markdown("**Subs Status:** <span style='color:red; font-style:italic;'>Past_due</span>", unsafe_allow_html=True)
                    elif subs_status.lower() == "active":
                        st.markdown("**Subs Status:** <span style='color:green; font-weight:bold;'>Active</span>", unsafe_allow_html=True)
                    elif subs_status.lower() == "canceled":
                        st.markdown("**Subs Status:** <span style='color:orange; font-weight:bold;'>Canceled</span>", unsafe_allow_html=True)
                    else:
                        st.write("**Subs Status:**", format_value(subs_status))
                else:
                    st.write("**Subs Status:**", "-")

                st.write("**Payment:**", format_value(filtered_data['payment_method'].iloc[0] if 'payment_method' in filtered_data.columns else '-'))
                st.write("**Pay Period:**", format_date(filtered_data['current_period_start'].iloc[0] if 'current_period_start' in filtered_data.columns else '-'))
                st.write("**Subs Name:**", format_value(filtered_data['product_name'].iloc[0] if 'product_name' in filtered_data.columns else '-'))
                st.write("**Amount:**", format_price(filtered_data['price_amount'].iloc[0] if 'price_amount' in filtered_data.columns else '-'))

            with col6:
                st.write("### Device Info")
                device_status = filtered_data['status'].iloc[0] if 'status' in filtered_data.columns else None
                if device_status and isinstance(device_status, str):
                    if device_status.lower() == "online":
                        st.markdown("**Status:** <span style='color:green; font-weight:bold;'>Online</span>", unsafe_allow_html=True)
                    elif device_status.lower() == "offline":
                        st.markdown("**Status:** <span style='color:red; font-style:italic;'>Offline</span>", unsafe_allow_html=True)
                    else:
                        st.write("**Status:**", device_status)
                else:
                    st.write("**Status:**", "-")

                esper_id = filtered_data['esper_id'].iloc[0] if 'esper_id' in filtered_data.columns else '-'
                device_name = filtered_data['device_name'].iloc[0] if 'device_name' in filtered_data.columns else '-'
                serial_number = filtered_data['serial_number'].iloc[0] if 'serial_number' in filtered_data.columns else '-'
                brand = filtered_data['brand'].iloc[0] if 'brand' in filtered_data.columns else '-'

                st.write("**Device Name:**", f"[{format_value(device_name)}](https://ozrlk.esper.cloud/devices/{esper_id})" if esper_id != '-' else '-')
                st.write("**Serial No:**", format_value(serial_number))
                st.write("**Model:**", format_value(brand))

            # col8 - New Column 
            with col8:
                st.write("### Store Location Info")
                
                location_status = filtered_data['Store Location pipeline stage'].iloc[0] if 'Store Location pipeline stage' in filtered_data.columns else "-"
                
                def format_location_status(status):
                    if isinstance(status, str):
                        if status.lower() == "live":
                            return "<span style='color:green; font-weight:bold;'>Live</span>"
                        elif status.lower() == "pending launch":
                            return "<span style='color:orange; font-weight:bold;'>Pending Launch</span>"
                        elif status.lower() == "churned - cancelled":
                            return "<span style='color:red; font-style:italic;'>Churned - Cancelled</span>"
                    return status

                if location_status and isinstance(location_status, str):
                    st.markdown("**Location Status:** " + format_location_status(location_status), unsafe_allow_html=True)
                else:
                    st.markdown("**Location Status:** <span style='color:gray;'>No records available</span>", unsafe_allow_html=True)

                st.write("**Onboarding Status:**", format_value(filtered_data['Onboarding Status'].iloc[0] if 'Onboarding Status' in filtered_data.columns else "-"))
                st.write("**Classification:**", format_value(filtered_data['Company Classification'].iloc[0] if 'Company Classification' in filtered_data.columns else "-"))
                st.write("**Account Manager:**", format_value(filtered_data['Account Manager'].iloc[0] if 'Account Manager' in filtered_data.columns else "-"))
                st.write("**Date Live:**", format_value(filtered_data['Date Live'].iloc[0] if 'Date Live' in filtered_data.columns else "-"))
                st.write("**Churned Date:**", format_value(filtered_data['Churn Date'].iloc[0] if 'Churn Date' in filtered_data.columns else "-"))

        else:
            st.write("No matching store found.")

with tab2:
    st.header("Single Address Search")
    
    # Input for single address
    single_address = st.text_input("Enter an address to search:", key="single_address_input")
    
    # Search button
    if st.button("Search Address", key="search_address_button"):
        if single_address:
            # Extract zip code from the address
            zip_code = extract_zip_code(single_address)
            
            if zip_code:
                st.info(f"Searching for information about zip code: {zip_code}")
                
                # Get population density
                with st.spinner("Fetching population density..."):
                    population_density = get_population_density(zip_code)
                
                # Create a result dictionary to store in session state
                result = {
                    "address": single_address,
                    "zip_code": zip_code,
                    "population_density": population_density
                }
                
                # Store the result in session state
                st.session_state.single_address_result = result
            else:
                st.error("Could not extract a valid zip code from the address. Please ensure the address includes a 5-digit zip code.")
        else:
            st.warning("Please enter an address to search.")
    
    # Clear results button
    if st.button("Clear Results", key="clear_results_button"):
        st.session_state.single_address_result = None
    
    # Display results if available
    if st.session_state.single_address_result:
        result = st.session_state.single_address_result
        
        st.subheader("Address Information")
        
        # Create columns for display
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Full Address:**", result["address"])
            st.write("**Zip Code:**", result["zip_code"])
        
        with col2:
            if result["population_density"]:
                st.write("**Population Density:**", f"{result['population_density']} people per square mile")
            else:
                st.write("**Population Density:**", "Information not available")
        
        # Check if this address matches any stores in the database
        if 'full_address' in data.columns:
            matching_stores = data[data['full_address'].str.contains(result["zip_code"], case=False, na=False)]
            
            if not matching_stores.empty:
                st.subheader("Stores in this Zip Code")
                st.dataframe(matching_stores[['store_name', 'full_address']])
            else:
                st.info(f"No stores found in zip code {result['zip_code']}.")

with tab3:
    # Load performance data using the cached function
    performance_data = load_csv_data('performancedata.csv')
    if performance_data is None:
        st.stop()
    
    # Use the selected store name from tab 1
    if st.session_state.selected_store:  # Use the exact selected store from session state
        # Exact case-insensitive match like in Tab 1
        filtered_performance_data = performance_data[
            performance_data['store_name'].str.lower() == st.session_state.selected_store.lower()
        ]
    
        # Function to format numerical values in dollars
        def format_to_dollars(value):
            if pd.isna(value):
                return "$0.00"
            return f"${value:.2f}" if isinstance(value, (int, float)) else value
    
        if not filtered_performance_data.empty:
            # Apply formatting to numerical columns
            for column in filtered_performance_data.columns:
                if pd.api.types.is_numeric_dtype(filtered_performance_data[column]):
                    filtered_performance_data[column] = filtered_performance_data[column].apply(format_to_dollars)
    
            st.markdown(f"### 12-Months Sales data for <span style='color:green; font-weight:bold;'>{st.session_state.selected_store}</span>:", unsafe_allow_html=True)
            st.dataframe(filtered_performance_data)
        else:
            st.warning(f"No performance data found for '{st.session_state.selected_store}'.")
    else:
        st.info("Please select a store in the Store Search tab first.")
