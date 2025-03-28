import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import plotly.io as pio
import os
import math

# Page setup
st.set_page_config(page_title="Team Performance Dashboard", layout="wide")
st.title("Monthly Performance Comparison")

# Month selection
months = st.multiselect(
    "Select 2 months to compare",
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"],
    default=["February", "March"]
)

if len(months) != 2:
    st.warning("Please select exactly 2 months.")
    st.stop()

# Number of FSCs
num_members = st.slider("Select Number of FSC in Team", min_value=1, max_value=30, value=6)
members = []
data = {}
working_days = {}

# Working days input
st.markdown("### Enter Working Days for Each Selected Month")
for month in months:
    days = st.number_input(f"Working Days in {month}", min_value=1, max_value=31, value=20, key=f"days_{month}")
    working_days[month] = days

# FSC data entry
st.markdown("### Enter Cases Closed for Each FSC")
cols = st.columns(len(months) + 1)
for i in range(num_members):
    name = cols[0].text_input(f"Name {i+1}", key=f"name_{i}", value=f"FSC{i+1}")
    members.append(name)
    for j, month in enumerate(months):
        val = cols[j+1].number_input(f"{month} - {name}", min_value=0, step=1, key=f"{month}_{name}")
        data.setdefault(month, []).append(val)

# --- CHARTS ---
df = pd.DataFrame(data, index=members)
calendar_order = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
sorted_months = sorted(months, key=lambda x: calendar_order.index(x))
month1, month2 = sorted_months[0], sorted_months[1]

# Line chart
st.markdown("### Monthly Closes Trend")
fig = go.Figure()
for month in sorted_months:
    fig.add_trace(go.Scatter(x=members, y=df[month], mode='lines+markers', name=month))
fig.update_layout(height=400, xaxis_title="FSCs", yaxis_title="Closed Cases", yaxis=dict(range=[0, 50]))
st.plotly_chart(fig, use_container_width=True)

# Individual gauges
st.markdown("### Individual FSC Performance Gauges")
col1, col2 = st.columns(2)
all_gauges = []
for i, member in enumerate(members):
    base = df.loc[member, month1]
    comp = df.loc[member, month2]
    g = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=comp,
        delta={'reference': base, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge={'axis': {'range': [0, 50]}},
        title={'text': f"{member} ({month2} vs {month1})"}
    ))
    all_gauges.append(g)
    (col1 if i % 2 == 0 else col2).plotly_chart(g, use_container_width=True)

# Average per day gauges
st.markdown("### Average Cases Closed Per Day")
avg_day_gauges = []
col3, col4 = st.columns(2)
for i, month in enumerate(sorted_months):
    total = df[month].sum()
    avg_day = round(total / working_days[month], 2)
    g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_day,
        title={'text': f"{month}: Avg Closed per Day"},
        gauge={'axis': {'range': [0, 10]}}
    ))
    avg_day_gauges.append(g)
    (col3 if i % 2 == 0 else col4).plotly_chart(g, use_container_width=True)

# Total vs Target gauges
st.markdown("### Total Closes vs Target")
total_target_gauges = []
target = 15 * num_members
for i, month in enumerate(sorted_months):
    total = df[month].sum()
    g = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=total,
        delta={'reference': target, 'increasing': {'color': 'green'}, 'decreasing': {'color': 'red'}},
        gauge={'axis': {'range': [0, max(50, target + 10)]}},
        title={'text': f"{month} Total vs Target ({target})"}
    ))
    total_target_gauges.append(g)
    st.plotly_chart(g, use_container_width=True)

# PDF EXPORT FUNCTION with centered rows
def generate_centered_pdf(df, working_days, sorted_months, line_chart, gauge_charts, avg_gauges, total_gauges):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(False)
    pdf.set_font("Arial", size=12)

    # Header
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, "FSC Performance Report", ln=True, align='C')

    # Working Days
    pdf.set_font("Arial", size=10)
    y_cursor = 18
    for month in sorted_months:
        pdf.set_xy(10, y_cursor)
        pdf.cell(0, 6, f"{month} Working Days: {working_days[month]}")
        y_cursor += 6

    def save_plot_as_image(fig, filename, width=500):
        path = os.path.join(tempfile.gettempdir(), filename)
        pio.write_image(fig, path, format='png', width=width, height=300)
        return path

    # Gauges: Avg Closed per Day
    avg_img1 = save_plot_as_image(avg_gauges[0], "avg1.png", width=300)
    avg_img2 = save_plot_as_image(avg_gauges[1], "avg2.png", width=300)
    pdf.image(avg_img1, x=10, y=30, w=50)
    pdf.image(avg_img2, x=65, y=30, w=50)

    # Gauges: Total Closed vs Target
    tgt_img1 = save_plot_as_image(total_gauges[0], "total1.png", width=300)
    tgt_img2 = save_plot_as_image(total_gauges[1], "total2.png", width=300)
    pdf.image(tgt_img1, x=10, y=64, w=50)
    pdf.image(tgt_img2, x=65, y=64, w=50)

    # Line Chart
    line_img = save_plot_as_image(line_chart, "line_chart.png", width=700)
    pdf.image(line_img, x=125, y=30, w=160)

    # Individual Gauges
    gauge_w = 58
    spacing = 60
    per_row = 5
    gauge_y_top = 115
    gauge_y_bottom = 165

    rows = [gauge_charts[:per_row], gauge_charts[per_row:per_row*2]]
    y_positions = [gauge_y_top, gauge_y_bottom]

    for row_idx, gauges in enumerate(rows):
        count = len(gauges)
        total_width = spacing * count
        start_x = (297 - total_width) / 2  # A4 landscape is 297mm wide
        for i, fig in enumerate(gauges):
            img = save_plot_as_image(fig, f"gauge_{row_idx}_{i}.png", width=350)
            x = start_x + i * spacing
            y = y_positions[row_idx]
            pdf.image(img, x=x, y=y, w=gauge_w)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        return tmp_file.name

# EXPORT BUTTON
if st.button("📄 Export Finalized PDF Report"):
    pdf_path = generate_centered_pdf(df, working_days, sorted_months, fig, all_gauges, avg_day_gauges, total_target_gauges)
    with open(pdf_path, "rb") as f:
        st.download_button("📥 Download PDF", f, file_name="fsc_performance_report.pdf", mime="application/pdf")
