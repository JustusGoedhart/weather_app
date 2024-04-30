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
import time
import uuid

# Load sensitive data from Streamlit Secrets
user1_username = st.secrets["USER1_USERNAME"]
user1_password_hash = st.secrets["USER1_PASSWORD_HASHED"]
user2_username = st.secrets["USER2_USERNAME"]
user2_password_hash = st.secrets["USER2_PASSWORD_HASHED"]

# Function to logout user
def logout():
    st.session_state['username'] = None
    st.rerun()

def authenticate(username, password, secrets):
    # Extract the hashed password based on the username
    if username in secrets:
        hashed_password = secrets[username]
        # Convert the stored hash from string to bytes for bcrypt
        stored_hash = hashed_password.encode().decode('unicode_escape').encode('raw_unicode_escape')
        return bcrypt.checkpw(password.encode(), stored_hash)
    else:
        return False

# Function to authenticate user
def authenticate_user(username, password):
    if username == user1_username:
        return authenticate(username, password, user1_password_hash)
    elif username == user2_username:
        return authenticate(username, password, user2_password_hash)
    else:
        return False

# Function to login user
def login(username, password):
    if authenticate(username, password):
        st.session_state['username'] = username  # Set the session state here
        return username
    return None

def login_form():
    form_key = f"login_form_{uuid.uuid4()}"
    with st.form(form_key):
        username = st.text_input("Username", key=f"username_{form_key}")
        password = st.text_input("Password", type="password", key=f"password_{form_key}")
        submitted = st.form_submit_button("Login")
        if submitted:
            if login(username, password):
                st.success("Logged in successfully!")
                st.session_state['username'] = username
                st.rerun()
                return True
            else:
                st.error("Username or password is incorrect")
                return False

# Initialize session state for username
if 'username' not in st.session_state:
    st.session_state['username'] = None

# Display the login form if no user is logged in
if not st.session_state['username']:
    login_form()

if 'city' not in st.session_state:
    st.session_state['city'] = "Cambridge, UK"  # Default city

# List of cities for the dropdown
cities = {
    "Cambridge, UK": ("52.2053,0.1218", "Europe/London"),
    "Hamburg, Germany": ("53.5511,9.9937", "Europe/Berlin"),
    "New York City, US": ("40.7128,-74.0060", "America/New_York"),
    "Mumbai, India": ("19.0760,72.8777", "Asia/Kolkata"),
    "Owase, Japan": ("34.0710,136.1903", "Asia/Tokyo"),
    "Sydney, Australia": ("-33.8688,151.2093", "Australia/Sydney"),
    "Rio de Janeiro, Brazil": ("-22.9068,-43.1729", "America/Sao_Paulo")
}

# API authentication details
api_username = st.secrets["API_USERNAME"]
api_password = st.secrets["API_PASSWORD"]

# Function to fetch weather data
def fetch_weather_data(city):
    coordinates, tz = cities[city]
    timezone = pytz.timezone(tz)
    now = datetime.now(timezone)  # Current local time
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
    formatted_start = start_of_day.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    formatted_end = end_of_day.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    url = f'https://api.meteomatics.com/{formatted_start}--{formatted_end}:PT1H/t_2m:C,precip_1h:mm,weather_symbol_1h:idx,wind_speed_10m:ms,wind_dir_10m:d,sunrise:sql,sunset:sql/{coordinates}/csv'
    response = requests.get(url, auth=HTTPBasicAuth(api_username, api_password))
    if response.status_code == 200:
        data = pd.read_csv(StringIO(response.text), delimiter=';')
        data['validdate'] = pd.to_datetime(data['validdate']).dt.tz_convert(timezone)
        # Rename columns for consistency and to avoid special characters
        data.rename(columns={
            't_2m:C': 'temperature_C', 
            'precip_1h:mm': 'precipitation_mm', 
            'weather_symbol_1h:idx': 'weather_symbol',
            'wind_speed_10m:ms': 'wind_speed_mps',  # renaming wind speed
            'wind_dir_10m:d': 'wind_direction_degrees'  # renaming wind direction
        }, inplace=True)

        # Create a mapping dictionary for weather symbols
        weather_symbol_mapping = {
            0: "A weather symbol could not be determined",
            1: "Clear sky",
            2: "Light clouds",
            3: "Partly cloudy",
            4: "Cloudy",
            5: "Rain",
            6: "Rain and snow / sleet",
            7: "Snow",
            8: "Rain shower",
            9: "Snow shower",
            10: "Sleet shower",
            11: "Light fog",
            12: "Dense fog",
            13: "Freezing rain",
            14: "Thunderstorms",
            15: "Drizzle",
            16: "Sandstorm",
            101: "Clear sky (night)",
            102: "Light clouds (night)",
            103: "Partly cloudy (night)",
            104: "Cloudy (night)",
            105: "Rain (night)",
            106: "Rain and snow / sleet (night)",
            107: "Snow (night)",
            108: "Rain shower (night)",
            109: "Snow shower (night)",
            110: "Sleet shower (night)",
            111: "Light fog (night)",
            112: "Dense fog (night)",
            113: "Freezing rain (night)",
            114: "Thunderstorms (night)",
            115: "Drizzle (night)",
            116: "Sandstorm (night)"
        }
        
        # Map weather symbols to weather conditions
        data['weather_condition'] = data['weather_symbol'].map(weather_symbol_mapping)

        # Convert wind direction from degrees to cardinal directions
        cardinal_directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        data['wind_direction_cardinal'] = data['wind_direction_degrees'].apply(lambda deg: cardinal_directions[int((deg % 360) / 22.5)])

        # Convert wind speed from m/s to km/h
        data['wind_speed_kph'] = data['wind_speed_mps'] * 3.6

        return data, now
    else:
        st.error(f"Failed to retrieve data: {response.status_code} {response.text}")
        return None, now

# Function to display the main page
def main_page():
    city = st.session_state['city']
    weather_data, current_time = fetch_weather_data(city)

    if weather_data is not None:
        # Display the welcome message as a header
        st.header(f"Today's weather in {city}.")

        # Prepare data for the custom table-like display
        times = weather_data['validdate'].dt.strftime('%-I%p').tolist()
        temperatures = [f"{temp:.1f}" for temp in weather_data['temperature_C'].tolist()]
        precipitations = [f"{precip:.1f}" for precip in weather_data['precipitation_mm'].tolist()]
        weather_conditions = weather_data['weather_condition'].tolist()
        wind_speeds = [f"{wind:.1f}" for wind in weather_data['wind_speed_kph'].tolist()]
        wind_directions = [f"{dir}" for dir in weather_data['wind_direction_cardinal'].tolist()]


        # Create dataframe for the table
        table_data = pd.DataFrame({
            'Time of Day': times,
            'Temperature (°C)': temperatures,
            'Precipitation (mm)': precipitations,
            'Weather Conditions': weather_conditions,
            'Wind Speed (km/h)': wind_speeds,  # Added wind speed
            'Wind Direction': wind_directions
        })

        # Display the current temperature and weather condition
        current_time_str = current_time.strftime('%-I%p').upper()
        current_temperature_str = table_data.loc[table_data['Time of Day'] == current_time_str, 'Temperature (°C)'].iloc[0]
        current_temperature = float(current_temperature_str)  # Convert to float
        current_condition = table_data.loc[table_data['Time of Day'] == current_time_str, 'Weather Conditions'].iloc[0]
        current_wind_speed_str = table_data.loc[table_data['Time of Day'] == current_time_str, 'Wind Speed (km/h)'].iloc[0]
        current_wind_speed = float(current_wind_speed_str)  # Convert to float if necessary
        current_wind_direction = table_data.loc[table_data['Time of Day'] == current_time_str, 'Wind Direction'].iloc[0]

        # Convert temperature values to numeric type
        table_data['Temperature (°C)'] = pd.to_numeric(table_data['Temperature (°C)'], errors='coerce')

        # Get the high and low temperatures for the day
        high_temp = table_data['Temperature (°C)'].max()
        low_temp = table_data['Temperature (°C)'].min()

        # Convert high_temp and low_temp to float
        high_temp = float(high_temp)
        low_temp = float(low_temp)

        # Centered and styled weather information
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown(f"<h1 style='text-align: center; color: blue;'>{round(current_temperature)} °C</h1>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="text-align: center;">
                <p><b>Current Cloud Cover:</b> {current_condition}</p>
                <p><b>Local Time:</b> {current_time.strftime('%-I%p').lower()}</p>
                <p>H: {round(high_temp)} °C / L: {round(low_temp)} °C</p>
                <p><b>Wind:</b> {current_wind_speed} km/h, {current_wind_direction}</p>
        </div>
        """, unsafe_allow_html=True)

        #st.write(f"Current Temperature: {current_temperature:.1f} °C")
        #st.write(f"Current Cloud Cover: {current_condition}")
        #st.write(f"Local Time: {current_time.strftime('%-I%p').lower()}")
        #st.write(f"High of the Day: {high_temp:.1f} °C")
        #st.write(f"Low of the Day: {low_temp:.1f} °C")

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
    # Initialize session state for username if not set
    if 'username' not in st.session_state:
        st.session_state['username'] = None

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
            st.rerun()  # Rerun the app to reflect the change immediately
        else:
            # Call main_page only after handling sidebar to avoid duplicate display
            main_page()
    else:
        # If not logged in, show the login form
        login_form()

app()  # Call the app function to run the app