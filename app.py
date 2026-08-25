import streamlit as st
import pandas as pd
import requests

def get_leetcode_stats(username):
    url = "https://leetcode.com/graphql"
    query = """
    query userProblemsSolved($username: String!) {
      matchedUser(username: $username) {
        submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
        profile {
          ranking
        }
      }
    }
    """
    try:
        response = requests.post(url, json={'query': query, 'variables': {"username": username}}, timeout=5)
        if response.status_code == 200:
            return response.json().get('data', {}).get('matchedUser')
    except Exception:
        return None
    return None

st.set_page_config(layout="wide")
st.title("Classroom LeetCode Tracker")

# 1. Load the student list
try:
    students_df = pd.read_csv("students.csv")
except FileNotFoundError:
    st.error("Please create a 'students.csv' file with 'name' and 'leetcode_username' columns.")
    st.stop()

# 2. Fetch data with a progress bar
data = []
progress_bar = st.progress(0)
total_students = len(students_df)

for idx, row in students_df.iterrows():
    name = row['name']
    username = str(row['leetcode_username']).strip()
    
    stats = get_leetcode_stats(username)
    
    if stats and stats.get('submitStatsGlobal'):
        submissions = stats['submitStatsGlobal']['acSubmissionNum']
        solved = {item['difficulty']: item['count'] for item in submissions}
        rank = stats['profile']['ranking'] if stats.get('profile') else "N/A"
        
        data.append({
            "Name": name,
            "Username": username,
            "Total Solved": solved.get("All", 0),
            "Easy": solved.get("Easy", 0),
            "Medium": solved.get("Medium", 0),
            "Hard": solved.get("Hard", 0),
            "Global Rank": rank
        })
    else:
        # If username is invalid or request timed out
        data.append({
            "Name": name,
            "Username": username,
            "Total Solved": 0,
            "Easy": 0,
            "Medium": 0,
            "Hard": 0,
            "Global Rank": "Not Found"
        })
    
    progress_bar.progress((idx + 1) / total_students)

# 3. Display results
if data:
    result_df = pd.DataFrame(data)
    st.dataframe(
        result_df.sort_values(by="Total Solved", ascending=False).reset_index(drop=True),
        use_container_width=True
    )
