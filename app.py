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

# ----------------- PDF Generator Helper -----------------
def generate_pdf(dataframe):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12
    )
    elements.append(Paragraph("Student LeetCode Performance Report", title_style))
    elements.append(Spacer(1, 10))

    # Convert DataFrame to Table data
    table_data = [[
        "Rank", "Name", "LeetCode ID", "Total Solved", "Easy", "Medium", "Hard", "Global Rank"
    ]]
    
    for idx, row in dataframe.iterrows():
        table_data.append([
            str(idx + 1),
            str(row["Name"]),
            str(row["Username"]),
            str(row["Total Solved"]),
            str(row["Easy"]),
            str(row["Medium"]),
            str(row["Hard"]),
            str(row["Global Rank"])
        ])

    pdf_table = Table(table_data, colWidths=[40, 150, 120, 80, 55, 65, 55, 100])
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (4, 1), (4, -1), colors.HexColor("#16a34a")), # Green for Easy
        ('TEXTCOLOR', (5, 1), (5, -1), colors.HexColor("#d97706")), # Amber for Medium
        ('TEXTCOLOR', (6, 1), (6, -1), colors.HexColor("#dc2626")), # Red for Hard
    ]))
    
    elements.append(pdf_table)
    doc.build(elements)
    
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# 1. Load the student list
try:
    sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTB1KTGC5kFMwErEpa6W7iDRWFw0DOXPIIG9P6f7JuSI-bKBYMGzGT6H9Iub1VE8E5oQcmerE8iBT8l/pub?output=csv"
    students_df = pd.read_csv(sheet_url)
    
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

# Generate and offer PDF Download
pdf_data = generate_pdf(result_df)

st.download_button(
    label="📥 Download Results as PDF",
    data=pdf_data,
    file_name="student_leetcode_report.pdf",
    mime="application/pdf"
