import gspread
import pandas as pd
from bokeh.plotting import figure, curdoc
from bokeh.layouts import gridplot
from bokeh.models import ColumnDataSource, Range1d, FixedTicker
from oauth2client.service_account import ServiceAccountCredentials
from bokeh.models.tools import HoverTool

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Resell").sheet1

def fetch_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # === Add Calculated Columns ===
    df["Profit per Item"] = df["Selling Price"] - df["Base Price"]
    df["Total Profit"] = df["Profit per Item"] * df["Units Sold"]
    df["Profit Margin (%)"] = (df["Profit per Item"] / df["Selling Price"]) * 100
    df["Revenue"] = df["Selling Price"] * df["Units Sold"]
    df["Projected Revenue"] = df["Selling Price"] * df["People Interested"]
    df["Projected Profit"] = df["Profit per Item"] * df["People Interested"]

    return df

def nice_range(max_val):
    if max_val == 0:
        return 10, 1
    magnitude = 10 ** (len(str(int(max_val))) - 1)
    step = magnitude // 2 if magnitude >= 10 else 1
    nice_max = ((int(max_val) // step) + 1) * step
    return nice_max, step

# Initial data load
df = fetch_data()

source = ColumnDataSource(df)

# Setup figures
tools = "hover,pan,box_zoom,reset"

def make_figure(title, y_field, color, y_range_max, y_range_step, x_range):
    p = figure(title=title, x_range=x_range, tools=tools, height=350)
    p.vbar(x='Item', top=y_field, width=0.4, source=source, color=color)
    p.y_range = Range1d(0, y_range_max * 1.05)
    p.yaxis.ticker = FixedTicker(ticks=list(range(0, int(p.y_range.end) + 1, y_range_step)))
    p.xaxis.major_label_orientation = 1
    p.add_tools(HoverTool(tooltips=[("Item", "@Item"), (title, f"@{y_field}{{0.00}}")]))
    return p

def update_data():
    new_df = fetch_data()
    source.data = ColumnDataSource.from_df(new_df)

    # Update y ranges & tickers for each plot
    # Revenue and Projected Revenue share x_range
    max_revenue = max(new_df["Revenue"].max(), new_df["Projected Revenue"].max())
    rev_max, rev_step = nice_range(max_revenue)
    p1.y_range.end = rev_max * 1.05
    p1.yaxis.ticker = FixedTicker(ticks=list(range(0, int(p1.y_range.end) + 1, rev_step)))

    # Profit Margin
    pm_max = max(new_df["Profit Margin (%)"].max(), 100)
    pm_max = (int(pm_max / 10) + 1) * 10
    p2.y_range.end = pm_max
    p2.yaxis.ticker = FixedTicker(ticks=list(range(0, int(pm_max) + 1, 10)))

    # Total Profit
    tp_max, tp_step = nice_range(new_df["Total Profit"].max())
    p3.y_range.end = tp_max * 1.05
    p3.yaxis.ticker = FixedTicker(ticks=list(range(0, int(p3.y_range.end) + 1, tp_step)))

    # Units Sold
    us_max, us_step = nice_range(new_df["Units Sold"].max())
    p4.y_range.end = us_max * 1.05
    p4.yaxis.ticker = FixedTicker(ticks=list(range(0, int(p4.y_range.end) + 1, max(1, us_step))))

    # Update x_range factors if items changed
    if list(p1.x_range.factors) != list(new_df["Item"]):
        new_items = list(new_df["Item"])
        for p in [p1, p2, p3, p4]:
            p.x_range.factors = new_items

# Prepare x_range factors
x_factors = list(df["Item"])

# Create plots
p1 = figure(title="Revenue", x_range=x_factors, tools=tools, height=350)
p1.vbar(x='Item', top='Revenue', width=0.4, source=source, color="cyan", legend_label="Revenue")
p1.vbar(x='Item', top='Projected Revenue', width=0.4, source=source, color="orange", alpha=0.5, legend_label="Projected Revenue")
p1.y_range = Range1d(0, max(df["Revenue"].max(), df["Projected Revenue"].max()) * 1.05)
p1.legend.click_policy = "hide"
p1.xaxis.major_label_orientation = 1
p1.add_tools(HoverTool(tooltips=[("Item", "@Item"), ("Revenue", "@Revenue{0.00}"), ("Projected Revenue", "@{Projected Revenue}{0.00}")]))


p2 = make_figure("Profit Margin (%)", "Profit Margin (%)", "lime", max(df["Profit Margin (%)"].max(), 100), 10, x_factors)
p3 = make_figure("Total Profit", "Total Profit", "magenta", df["Total Profit"].max(), 1000, x_factors)
p4 = make_figure("Units Sold", "Units Sold", "deepskyblue", df["Units Sold"].max(), 10, x_factors)

layout = gridplot([[p1, p2], [p3, p4]])

curdoc().add_root(layout)
curdoc().title = "Live Resell Dashboard"

# Update every 30 seconds
curdoc().add_periodic_callback(update_data, 1000)
