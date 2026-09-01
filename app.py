import io
import zipfile
from datetime import datetime
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ----------------- LeetCode API Fetcher -----------------
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
        res = requests.post(url, json={'query': query, 'variables': {"username": username}}, timeout=5)
        if res.status_code == 200:
            return res.json().get('data', {}).get('matchedUser')
    except Exception:
        pass
    return None

# ----------------- Section PDF Generator -----------------
def generate_section_pdf(dataframe, section_name):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25
    )
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'],
        fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"), spaceAfter=4
    )
    timestamp_style = ParagraphStyle(
        'Timestamp', parent=styles['Normal'],
        fontSize=9, leading=12, textColor=colors.HexColor("#64748b"), spaceAfter=14
    )

    current_time_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    elements.append(Paragraph(f"Coding Report: {section_name}", title_style))
    elements.append(Paragraph(f"<b>Generated on:</b> {current_time_str} • Section Roster", timestamp_style))
    elements.append(Spacer(1, 5))

    # Table Header with Register Number
    table_data = [["Rank", "Reg No", "Student Name", "LeetCode ID", "Total", "Easy", "Med", "Hard", "Global Rank"]]
    
    for idx, row in dataframe.iterrows():
        table_data.append([
            str(idx + 1),
            str(row["Reg No"]),
            str(row["Name"]),
            str(row["Username"]),
            str(row["Total Solved"]),
            str(row["Easy"]),
            str(row["Medium"]),
            str(row["Hard"]),
            str(row["Global Rank"])
        ])

    # Adjusted column widths to accommodate the Register Number column cleanly
    pdf_table = Table(table_data, colWidths=[35, 80, 140, 110, 50, 45, 45, 45, 85])
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (3, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TEXTCOLOR', (5, 1), (5, -1), colors.HexColor("#16a34a")), # Easy
        ('TEXTCOLOR', (6, 1), (6, -1), colors.HexColor("#d97706")), # Med
        ('TEXTCOLOR', (7, 1), (7, -1), colors.HexColor("#dc2626")), # Hard
    ]))

    elements.append(pdf_table)
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ----------------- Excel Generators -----------------
def generate_section_excel(dataframe, section_name):
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False, sheet_name=section_name[:31])
    excel_buffer.seek(0)
    return excel_buffer.getvalue()

def generate_multi_tab_excel(sections_dict):
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        for sec_name, df_sec in sections_dict.items():
            sheet_title = str(sec_name)[:31]
            df_sec.to_excel(writer, index=False, sheet_name=sheet_title)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()

# ----------------- App UI -----------------
st.set_page_config(layout="wide")
st.title("Multi-Section Coding Tracker Dashboard")

uploaded_file = st.file_uploader("Upload Student List CSV (with 'reg_no', 'name', 'leetcode_username', 'section')", type=["csv"])

if uploaded_file:
    students_df = pd.read_csv(uploaded_file)
    
    required_cols = {"reg_no", "name", "leetcode_username", "section"}
    if not required_cols.issubset(set(students_df.columns)):
        st.error(f"Uploaded CSV must include all required columns: {', '.join(required_cols)}")
        st.stop()

    if st.button("Fetch & Process All Sections"):
        records = []
        progress = st.progress(0)
        total = len(students_df)

        for idx, row in students_df.iterrows():
            uname = str(row["leetcode_username"]).strip()
            stats = get_leetcode_stats(uname)
            
            if stats and stats.get("submitStatsGlobal"):
                subs = {item["difficulty"]: item["count"] for item in stats["submitStatsGlobal"]["acSubmissionNum"]}
                rank = stats["profile"]["ranking"] if stats.get("profile") else "N/A"
                records.append({
                    "Section": row["section"],
                    "Reg No": str(row["reg_no"]),
                    "Name": row["name"],
                    "Username": uname,
                    "Total Solved": subs.get("All", 0),
                    "Easy": subs.get("Easy", 0),
                    "Medium": subs.get("Medium", 0),
                    "Hard": subs.get("Hard", 0),
                    "Global Rank": rank
                })
            else:
                records.append({
                    "Section": row["section"],
                    "Reg No": str(row["reg_no"]),
                    "Name": row["name"],
                    "Username": uname,
                    "Total Solved": 0,
                    "Easy": 0,
                    "Medium": 0,
                    "Hard": 0,
                    "Global Rank": "N/A"
                })
            progress.progress((idx + 1) / total)

        full_df = pd.DataFrame(records)
        st.session_state.processed_df = full_df

if "processed_df" in st.session_state:
    df = st.session_state.processed_df
    st.header("📈 Inter-Section Comparison & Analytics")

    # 1. Aggregate metrics by Section
    section_summary = df.groupby("Section").agg(
    Total_Students=("Reg No", "count"),
    Avg_Solved=("Total Solved", "mean"),
    Max_Solved=("Total Solved", "max"),
    Total_Easy=("Easy", "sum"),
    Total_Medium=("Medium", "sum"),
    Total_Hard=("Hard", "sum"),
    Active_Students=("Total Solved", lambda x: (x > 0).sum())
    ).reset_index()

    section_summary["Avg_Solved"] = section_summary["Avg_Solved"].round(1)

    # 2. Key High-Level KPI Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    best_sec = section_summary.sort_values(by="Avg_Solved", ascending=False).iloc[0]

    kpi1.metric("Top Performing Section", f"{best_sec['Section']}")
    kpi2.metric("Highest Average Solved", f"{best_sec['Avg_Solved']} problems")
    kpi3.metric("Total Hard Problems (All)", f"{df['Hard'].sum()}")
    kpi4.metric("Active Participation Rate", f"{(df['Total Solved'] > 0).mean() * 100:.1f}%")

    st.markdown("---")

    # 3. Chart 1: Average Solved per Section (Ranked Bar Chart)
    col_left, col_right = st.columns(2)

    with col_left:
          st.subheader("🏆 Average Problems Solved per Student")
          fig_avg = px.bar(
          section_summary.sort_values(by="Avg_Solved", ascending=True),
          x="Avg_Solved",
          y="Section",
          orientation="h",
          text="Avg_Solved",
          color="Avg_Solved",
          color_continuous_scale="Blues",
          labels={"Avg_Solved": "Average Solved Count", "Section": "Class Section"}
          )
    fig_avg.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_avg, use_container_width=True)

    # 4. Chart 2: Stacked Breakdown by Difficulty (Easy / Med / Hard)
    with col_right:
       st.subheader("🧩 Difficulty Breakdown by Section")
       # Melt dataframe for easy multi-color stacked bar representation
       melted_diff = df.groupby("Section")[["Easy", "Medium", "Hard"]].mean().reset_index()
       melted_diff = pd.melt(melted_diff, id_vars=["Section"], value_vars=["Easy", "Medium", "Hard"],
                          var_name="Difficulty", value_name="Average Count")
    
    fig_diff = px.bar(
        melted_diff,
        x="Section",
        y="Average Count",
        color="Difficulty",
        color_discrete_map={"Easy": "#16a34a", "Medium": "#d97706", "Hard": "#dc2626"},
        barmode="stack",
        labels={"Average Count": "Avg Solved per Student"}
    )
    fig_diff.update_layout(margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_diff, use_container_width=True)

  # 5. Chart 3: Distribution Box Plot (Identifies outliers and overall spread)
    st.subheader("📦 Problem Distribution & Spread (Box Plot)")
    fig_box = px.box(
     df,
     x="Section",
     y="Total Solved",
     color="Section",
     points="all", # Shows individual student dots alongside box plots
     hover_data=["Name", "Reg No", "Total Solved"],
    labels={"Total Solved": "Total Problems Solved"}
    )
    fig_box.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_box, use_container_width=True)

  # 6. Comparative Summary Table
    st.subheader("📋 Section Leaderboard Summary")
    st.dataframe(
    section_summary.sort_values(by="Avg_Solved", ascending=False).reset_index(drop=True),
    use_container_width=True
    )
    
    
    
    sections = {sec: group.sort_values(by="Total Solved", ascending=False).reset_index(drop=True) 
                for sec, group in df.groupby("Section")}

    st.subheader(f"📊 Tracking {len(sections)} Sections")

    # Bulk Downloads
    col1, col2 = st.columns(2)
    with col1:
        zip_pdf_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_pdf_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for sec_name, sec_df in sections.items():
                pdf_bytes = generate_section_pdf(sec_df, str(sec_name))
                zip_file.writestr(f"{sec_name}_Report.pdf", pdf_bytes)
        zip_pdf_buffer.seek(0)

        st.download_button(
            label="📦 Download All Section PDFs (ZIP)",
            data=zip_pdf_buffer,
            file_name="All_Sections_PDF_Reports.zip",
            mime="application/zip",
            use_container_width=True
        )

    with col2:
        multi_excel_bytes = generate_multi_tab_excel(sections)
        st.download_button(
            label="📗 Download Master Excel (All Sections)",
            data=multi_excel_bytes,
            file_name="Master_Coding_Status_All_Sections.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.divider()

    # Individual Section Views & Downloads
    for sec_name, sec_df in sections.items():
        with st.expander(f"📁 {sec_name} ({len(sec_df)} Students)"):
            st.dataframe(sec_df, use_container_width=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label=f"📄 Download {sec_name} PDF",
                    data=generate_section_pdf(sec_df, str(sec_name)),
                    file_name=f"{sec_name}_Report.pdf",
                    mime="application/pdf",
                    key=f"pdf_{sec_name}"
                )
            with c2:
                st.download_button(
                    label=f"📊 Download {sec_name} Excel",
                    data=generate_section_excel(sec_df, str(sec_name)),
                    file_name=f"{sec_name}_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"excel_{sec_name}"
                )
