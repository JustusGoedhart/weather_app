#%%
import streamlit as st
import bcrypt
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from io import StringIO
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import schedule
import time

# Login works as expected
# Logout button correctly placed in sidebar menu
# Temperature change for Cambridge UK for one week is shown including the dataframe
# Drop down menu in sidebar to choose other cities, which will be displayed in the main page
# "Viewing weather for city" did not update when choosing new dropdown option, which is corrected here
# Changing layout of data that is displayed to make it more userfriendly
    # Current temperature
    # Table with temperature at each time of the day starting with midnight
    # Precipitation
    # Condition
    # High and low of the day
    # Second toggle for day / 7 day period

# Initialize session state for username
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'city' not in st.session_state:
    st.session_state['city'] = "Cambridge, UK"  # Default city

# List of cities for the dropdown
cities = {
    "Cambridge, UK": ("52.2053,0.1218", "Europe/London"),
    "Hamburg, Germany": ("53.5511,9.9937", "Europe/Berlin"),
    "New York City, US": ("40.7128,-74.0060", "America/New_York"),
    "Mumbai, India": ("19.0760,72.8777", "Asia/Kolkata")
}

# Function to hash passwords using bcrypt
def hash_password(password):
    # Generate a salt and return a hashed password
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)

# Dummy database of users with hashed passwords
users = {
    "user1": hash_password("password1"),
    "user2": hash_password("password2")
}

# API authentication details
api_username = 'student_goedhart_justus'
api_password = 'Mp3JEcg75R'

# Function to fetch weather data
#@st.cache_data(ttl=3600) # Cache data for 1 hour (3600 seconds)
def fetch_weather_data(city):
    coordinates, tz = cities[city]
    timezone = pytz.timezone(tz)
    now = datetime.now(timezone)  # Current local time
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
    formatted_start = start_of_day.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    formatted_end = end_of_day.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    url = f'https://api.meteomatics.com/{formatted_start}--{formatted_end}:PT1H/t_2m:C,precip_1h:mm,weather_symbol_1h:idx/{coordinates}/csv'
    response = requests.get(url, auth=HTTPBasicAuth(api_username, api_password))
    if response.status_code == 200:
        data = pd.read_csv(StringIO(response.text), delimiter=';')
        data['validdate'] = pd.to_datetime(data['validdate']).dt.tz_convert(timezone)
        # Rename columns for consistency and to avoid special characters
        data.rename(columns={'t_2m:C': 'temperature_C', 'precip_1h:mm': 'precipitation_mm', 'weather_symbol_1h:idx': 'weather_symbol'}, inplace=True)

        # Create a mapping dictionary for weather symbols
        weather_symbol_mapping = {
            1: "Clear sky",
            2: "Partly cloudy",
            3: "Cloudy",
            4: "Overcast",
            5: "Mist",
            # Add more mappings as needed
        }
        
        # Map weather symbols to weather conditions
        data['weather_condition'] = data['weather_symbol'].map(weather_symbol_mapping)
        
        # Return the updated data including precipitation
        return data, now
    else:
        st.error(f"Failed to retrieve data: {response.status_code} {response.text}")
        return None, now

# Schedule the fetch_weather_data function to run every hour
#schedule.every().hour.do(fetch_weather_data)

#while True:
    #schedule.run_pending()
    #time.sleep(60)  # Sleep for 60 seconds

# Function to logout user
def logout():
    st.session_state['username'] = None
    st.experimental_rerun()

# Function to login user
def login(username, password):
    if username in users and bcrypt.checkpw(password.encode(), users[username]):
        st.session_state['username'] = username
        st.experimental_rerun()  # Rerun the app to update the login state


# Function to display login form
def login_form():
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if login(username, password):
                st.success("Logged in successfully!")
            else:
                st.error("Username or password is incorrect")

# Function to display the main page
def main_page():
    city = st.session_state['city']
    weather_data, current_time = fetch_weather_data(city)

    if weather_data is not None:
        # Display the welcome message as a header
        st.header(f"Current weather in {city}.")

        # Prepare data for the custom table-like display
        times = weather_data['validdate'].dt.strftime('%-I%p').tolist()
        temperatures = [f"{temp:.1f}" for temp in weather_data['temperature_C'].tolist()]
        precipitations = [f"{precip:.1f}" for precip in weather_data['precipitation_mm'].tolist()]
        weather_conditions = weather_data['weather_condition'].tolist()

        # Create dataframe for the table
        table_data = pd.DataFrame({
            'Time of Day': times,
            'Temperature (°C)': temperatures,
            'Precipitation (mm)': precipitations,
            'Weather Conditions': weather_conditions
        })

        # Display the current temperature and weather condition
        st.subheader("Today's weather:")
        current_time_str = current_time.strftime('%-I%p').upper()
        current_temperature_str = table_data.loc[table_data['Time of Day'] == current_time_str, 'Temperature (°C)'].iloc[0]
        current_temperature = float(current_temperature_str)  # Convert to float
        current_condition = table_data.loc[table_data['Time of Day'] == current_time_str, 'Weather Conditions'].iloc[0]

        # Convert temperature values to numeric type
        table_data['Temperature (°C)'] = pd.to_numeric(table_data['Temperature (°C)'], errors='coerce')

        # Get the high and low temperatures for the day
        high_temp = table_data['Temperature (°C)'].max()
        low_temp = table_data['Temperature (°C)'].min()

        # Convert high_temp and low_temp to float
        high_temp = float(high_temp)
        low_temp = float(low_temp)

        st.write(f"Current Temperature: {current_temperature:.1f} °C")
        st.write(f"Current Cloud Cover: {current_condition}")
        st.write(f"Local Time: {current_time.strftime('%-I%p').lower()}")
        st.write(f"High of the Day: {high_temp:.1f} °C")
        st.write(f"Low of the Day: {low_temp:.1f} °C")

        # Display the hourly weather overview table
        st.subheader("Hourly Weather Overview:")
        table_data = table_data.fillna("Nighttime")
        st.table(table_data.T) # T to transpose the table



        # Display the radio button group for selecting chart type
        chart_type = st.radio("Select chart type:", ["Temperature (°C)", "Precipitation (mm)"])
        
        if chart_type == "Temperature (°C)": #default temperature
            st.line_chart(weather_data.set_index('validdate')['temperature_C'], use_container_width=True)
        else:  # precipitation
            st.bar_chart(weather_data.set_index('validdate')['precipitation_mm'], use_container_width=True)
    else:
        st.write("Unable to fetch weather data.")

# Display login form or main page based on session state
def app():
    # Check login status to decide which page to show
    if st.session_state.get('username'):
        # Handle sidebar operations first
        st.sidebar.write("Welcome! You are logged in as:", st.session_state['username'])
        if st.sidebar.button("Logout", key="logout_button"):  # Logout button in the sidebar
            logout()
            return  # Stop execution to refresh the app after logging out

        # City selection
        selected_city = st.sidebar.selectbox("Select a city:", list(cities.keys()), key='city_selector')
        if selected_city != st.session_state.get('city', None):
            st.session_state['city'] = selected_city  # Update the current city in session state
            st.experimental_rerun()  # Rerun the app to reflect the change immediately
        else:
            # Call main_page only after handling sidebar to avoid duplicate display
            main_page()
    else:
        # If not logged in, show the login form
        login_form()

app()  # Call the app function to run the app