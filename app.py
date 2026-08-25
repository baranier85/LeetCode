import streamlit as st
import pandas as pd
import requests

def get_leetcode_stats(username):
    url = "https://leetcode.com/graphql"
    query = """
    query userProblemsSolved($username: String!) {
      matchedUser(username: $username) {
        username
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
    variables = {"username": username}
    response = requests.post(url, json={'query': query, 'variables': variables})
    
    if response.status_code == 200:
        return response.json()['data']['matchedUser']
    return None

# Web UI Layout
st.title("Classroom LeetCode Tracker")

# Replace with your actual student usernames
students = ["Jcvvt6HHj8", "tourist","muktij"] 

data = []
for username in students:
    stats = get_leetcode_stats(username)
    if stats:
        submissions = stats['submitStatsGlobal']['acSubmissionNum']
        solved = {item['difficulty']: item['count'] for item in submissions}
        
        data.append({
            "Student": username,
            "Total Solved": solved.get("All", 0),
            "Easy": solved.get("Easy", 0),
            "Medium": solved.get("Medium", 0),
            "Hard": solved.get("Hard", 0),
            "Global Rank": stats['profile']['ranking']
        })

if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_values(by="Total Solved", ascending=False), use_container_width=True)
else:
    st.warning("No data found for the given usernames.")
