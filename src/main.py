import streamlit as st # type: ignore
import requests
import pandas as pd # type: ignore
import pydeck as pdk # type: ignore
from datetime import datetime, timedelta

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

today = datetime.now()
six_months_ago = today - timedelta(days=182)
start_of_this_year = datetime(today.year, 1, 1)
end_of_previous_year = datetime(today.year - 1, 12, 31)
start_of_previous_year = datetime(today.year - 1, 1, 1)

API_URLS = {
    "Past Hour": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "Past Day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "Past 7 Days": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "Past 30 Days": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson",
    "Past 6 Months": f"{BASE_URL}?starttime={six_months_ago.strftime('%Y-%m-%d')}&endtime={today.strftime('%Y-%m-%d')}&format=geojson&limit=20000",
    "This Year": f"{BASE_URL}?starttime={start_of_this_year.strftime('%Y-%m-%d')}&endtime={today.strftime('%Y-%m-%d')}&format=geojson&limit=20000",
    "Previous Year": f"{BASE_URL}?starttime={start_of_previous_year.strftime('%Y-%m-%d')}&endtime={end_of_previous_year.strftime('%Y-%m-%d')}&format=geojson&limit=20000",
}

MAP_API_URLS = {
    "Light Map": "mapbox://styles/mapbox/light-v9",
    "Dark Map": "mapbox://styles/mapbox/dark-v9",
    "Street Map": "mapbox://styles/mapbox/streets-v11",
    "Satellite Map": "mapbox://styles/mapbox/satellite-v9",
    "Heat Map": "mapbox://styles/mapbox/dark-v9",
}

def fetch_earthquake_data(time_period="Past Day"):
    response = requests.get(API_URLS[time_period])
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch data from USGS API.")
        return None

def switch_map_style(map_type="dark map"):
    return MAP_API_URLS[map_type]

def parse_earthquake_data(data):
    features = data["features"]
    earthquakes = [
        {
            "latitude": feature["geometry"]["coordinates"][1],
            "longitude": feature["geometry"]["coordinates"][0],
            "magnitude": feature["properties"]["mag"],
            "place": feature["properties"]["place"],
            "time": pd.to_datetime(feature["properties"]["time"], unit='ms'),
        }
        for feature in features
    ]
    return pd.DataFrame(earthquakes)

def get_color(magnitude):
    return [
        255, 
        int(255 * (1 - (magnitude / 10))),
        0,
        200,
    ]

if "filtered_df" not in st.session_state:
    st.session_state.filtered_df = None

st.set_page_config(page_title="Earthquake Map", layout="wide")
st.title("EQ Forecaster")
st.sidebar.markdown("### Filter Options")
time_period = st.selectbox(
    "Select the time period for the earth quakes",
    list(API_URLS.keys()),
    label_visibility="hidden",
    index= None,
    placeholder="Select the Time Period",
    key="time_period_selectbox",
)


if time_period:
    data = fetch_earthquake_data(time_period)
else:
    data = fetch_earthquake_data()  

if data:
    df = parse_earthquake_data(data)
    df = df.dropna(subset=["magnitude"])
    min_magnitude = st.sidebar.slider("Set Minimum Magnitude", 0.0, 10.0, 0.0, 0.1)
    if st.sidebar.button("Filter Magnitude"):
        st.session_state.filtered_df = df[df["magnitude"] >= min_magnitude]
        st.session_state.filtered_df["color"] = st.session_state.filtered_df["magnitude"].apply(get_color)
    filtered_df = st.session_state.filtered_df if st.session_state.filtered_df is not None else df
    filtered_df["color"] = filtered_df["magnitude"].apply(get_color)
    col1, col2 = st.columns([4, 1])

    with col1:
        map_type = st.selectbox(
            "Select the type of map",
            list(MAP_API_URLS.keys()),
            label_visibility="hidden",
            index=0,
            placeholder="Select the Map Type",
        )

        if map_type == "Heat Map":
            layer = pdk.Layer(
                "HeatmapLayer",
                data=filtered_df,
                get_position=["longitude", "latitude"],
                get_weight="magnitude",
                radius_pixels=50,
                intensity=1,
                threshold=0.3,
            )
        else:
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=filtered_df,
                get_position=["longitude", "latitude"],
                get_color="color",
                get_radius="magnitude * 10000",
                pickable=True,
            )
    
        st.pydeck_chart(
            pdk.Deck(
                map_style=switch_map_style(map_type),
                initial_view_state=pdk.ViewState(
                    latitude=30.3753,
                    longitude=69.3451,
                    # latitude=filtered_df["latitude"].mean(),
                    # longitude=filtered_df["longitude"].mean(),
                    zoom=3,
                    pitch=0,
                ),
                layers=[layer],
                tooltip={"text": "Place: {place}\nMagnitude: {magnitude}"},
            )
        )

    with col2:
        st.markdown(
            """
            <div style="text-align: center; margin-top: 10px;">
            <p style="margin-bottom: 10px;">High (Red)</p>
            <div style="width: 40px; height: 400px; background: linear-gradient(to bottom, red, yellow); margin: auto;"></div>
            <p style="margin-top: 10px;">Low (Yellow)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )