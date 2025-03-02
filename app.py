import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO


st.set_page_config(layout="wide")

hide_streamlit_style = """
                <style>
                
                #MainMenu {
                visibility: hidden;
                height: 0%;
                }
                header {
                visibility: hidden;
                height: 0%;
                }
                footer {
                visibility: hidden;
                height: 0%;
                }
                </style>
                """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def get_tracker_list(hash_key):
    url = 'https://api.eu.navixy.com/v2/tracker/list'
    headers = {'Content-Type': 'application/json'}
    data = {'hash': hash_key}
    response = requests.post(url, headers=headers, json=data)


    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"API request failed with status code {response.status_code}: {response.text}")
        return None


def get_tracker_attributes(hash_key, tracker_id):


    url = 'https://api.eu.navixy.com/dwh/v1/tracker/raw_data/get_inputs'
    headers = {'Content-Type': 'application/json'}
    data = {'hash': hash_key, 'tracker_id': tracker_id}
    response = requests.post(url, headers=headers, json=data)


    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"API request failed with status code {response.status_code}: {response.text}")
        return None


def get_tracker_data(hash_key, tracker_id, selected_columns):


    url = 'https://api.eu.navixy.com/dwh/v1/tracker/raw_data/read'
    headers = {'accept': 'text/csv', 'Content-Type': 'application/json'}
    data = {
        'hash': hash_key,
        'tracker_id': tracker_id,
        'from': (datetime.utcnow() - timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'to': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'columns': selected_columns
    }
    response = requests.post(url, headers=headers, json=data)


    if response.status_code == 200:
        return response.text
    else:
        st.error(f"API request failed with status code {response.status_code}: {response.text}")
        return None


def format_attributes(attributes_response):
    formatted_columns = []

    for input_attr in attributes_response.get('inputs', []):
        formatted_columns.append(f"inputs.{input_attr}")

    for state in attributes_response.get('states', []):
        formatted_columns.append(f"states.{state}")

    for i in range(1, attributes_response.get('discrete_inputs', 0) + 1):
        formatted_columns.append(f"discrete_inputs.{i}")

    for i in range(1, attributes_response.get('discrete_outputs', 0) + 1):
        formatted_columns.append(f"discrete_outputs.{i}")

    return formatted_columns

def main():
    st.title("Tracker RAW Data Analyzer")

    hash_key = st.query_params["session_key"]

    if not hash_key:
        st.error("Hash key is missing in the URL.")
        return

    tracker_list_response = get_tracker_list(hash_key)
    if not tracker_list_response:
        return

    trackers = tracker_list_response.get('list', [])
    tracker_labels = [tracker['label'] for tracker in trackers]

    selected_label = st.sidebar.selectbox("Select a tracker", tracker_labels)
    if selected_label:
        selected_tracker = next(tracker for tracker in trackers if tracker['label'] == selected_label)
        tracker_id = selected_tracker['id']

        attributes_response = get_tracker_attributes(hash_key, tracker_id)
        if attributes_response and attributes_response.get('success'):
            formatted_columns = format_attributes(attributes_response)

            selected_columns = ["server_time", "lat", "lng", "speed", "alt"] + formatted_columns

            tracker_data_csv = get_tracker_data(hash_key, tracker_id, selected_columns)
            if tracker_data_csv:
                tracker_data_df = pd.read_csv(StringIO(tracker_data_csv))


                st.subheader("Data Preview")
                st.write(tracker_data_df)

                st.subheader("Data Summary")
                st.write(tracker_data_df.describe())

                st.subheader("Plot Data")
                columns = tracker_data_df.columns.tolist()

                x_column = st.selectbox("Select x-axis column", columns, index=columns.index('server_time'))

                y_columns = st.multiselect("Select up to 2 attributes for the y-axis", [col for col in columns if col != x_column], default=['alt', 'speed'])

                if st.button("Generate Plot"):
                    if y_columns:
                        plot_data = tracker_data_df.set_index(x_column)[y_columns]
                        st.line_chart(plot_data)
                    else:
                        st.warning("Please select at least one attribute for the y-axis.")

                st.subheader("Map View")
                if st.button("Show on Map"):
                    map_data = tracker_data_df.rename(columns={'lng': 'lon'})
                    st.map(map_data)

if __name__ == "__main__":
    main()
