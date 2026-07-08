# charts.py — Plotly figure builders for the dashboard

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from config import STATUS_COLORS


def arrival_distribution_chart(dist_df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart: projected vs actual arrivals by hour."""
    hour_labels = [
        f"{h % 12 or 12}{'am' if h < 12 else 'pm'}" for h in dist_df["hour"]
    ]

    fig = go.Figure()
    fig.add_bar(
        x=hour_labels,
        y=dist_df["projected"],
        name="Projected",
        marker_color="#B5D4F4",
        marker_line_width=0,
    )
    fig.add_bar(
        x=hour_labels,
        y=dist_df["actual"],
        name="Actual",
        marker_color="#378ADD",
        marker_line_width=0,
    )
    fig.update_layout(
        barmode="group",
        height=225,
        margin=dict(l=10, r=10, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.25, x=0, font_size=11),
        xaxis=dict(showgrid=False, tickfont_size=10),
        yaxis=dict(showgrid=True, gridcolor="rgba(136,135,128,0.15)", tickfont_size=10),
        font=dict(family="sans-serif", size=11),
    )
    return fig


def transport_donut(motor_coach: int, personal_vehicle: int) -> go.Figure:
    """Donut chart of transport type breakdown."""
    fig = go.Figure(go.Pie(
        labels=["Motor coach", "Personal vehicle"],
        values=[motor_coach, personal_vehicle],
        hole=0.65,
        marker_colors=["#378ADD", "#97C459"],
        textinfo="none",
        hovertemplate="%{label}: %{value} units (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        height=225,
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="left",
            x=-0.1,
            font=dict(size=11, color="#4A5568"),
            itemsizing="constant",
            bgcolor="rgba(0,0,0,0)",
        ),
        font=dict(family="sans-serif", size=11),
    )
    return fig


def status_pipeline_bar(stats: dict) -> go.Figure:
    """Horizontal stacked bar showing pipeline progression."""
    total = stats["total"] or 1
    fig = go.Figure()

    segments = [
        ("On-site",       stats["on_site"],     STATUS_COLORS["On-site"]),
        ("At South Gate", stats.get("in_transit_sg", 0), STATUS_COLORS["At South Gate"]),
        ("At Ruby",       stats.get("in_transit_ruby", 0), STATUS_COLORS["At Ruby"]),
        ("Not arrived",   stats["not_arrived"],  STATUS_COLORS["Not arrived"]),
    ]

    for label, value, color in segments:
        fig.add_bar(
            x=[value],
            y=["Units"],
            orientation="h",
            name=label,
            marker_color=color,
            text=f"{value}" if value > 0 else "",
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"{label}: {value}<extra></extra>",
        )

    fig.update_layout(
        barmode="stack",
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def variance_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram of arrival variances (minutes early/late)."""
    data = df["variance_minutes"].dropna()
    if data.empty:
        fig = go.Figure()
        fig.update_layout(
            height=160,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text="No arrivals yet", showarrow=False,
                              font=dict(size=12, color="#888780"), xref="paper", yref="paper",
                              x=0.5, y=0.5)],
        )
        return fig

    colors = ["#E24B4A" if v > 0 else "#639922" for v in data]

    fig = go.Figure(go.Histogram(
        x=data,
        nbinsx=20,
        marker_color="#378ADD",
        hovertemplate="Variance %{x:.0f} min: %{y} units<extra></extra>",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="#888780", line_width=1)
    fig.update_layout(
        height=160,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="Minutes early / late",
            title_font_size=10,
            tickfont_size=10,
            showgrid=False,
        ),
        yaxis=dict(
            title="Units",
            title_font_size=10,
            tickfont_size=10,
            showgrid=True,
            gridcolor="rgba(136,135,128,0.15)",
        ),
        font=dict(family="sans-serif", size=11),
    )
    return fig


def leg_duration_chart(leg_stats: dict) -> go.Figure:
    """Bar chart comparing average travel time for each leg, with min/max range."""
    labels = {
        "ruby_to_southgate":     "Ruby → South Gate",
        "southgate_to_basecamp": "South Gate → Basecamp",
        "ruby_to_basecamp":      "Ruby → Basecamp",
    }
    colors = ["#378ADD", "#BA7517", "#639922"]

    names, avgs, mins, maxs, counts = [], [], [], [], []
    for key, label in labels.items():
        stat = leg_stats[key]
        names.append(label)
        avgs.append(stat["avg"] if stat["avg"] is not None else 0)
        mins.append(stat["min"] if stat["min"] is not None else 0)
        maxs.append(stat["max"] if stat["max"] is not None else 0)
        counts.append(stat["count"])

    fig = go.Figure()
    fig.add_bar(
        x=names,
        y=avgs,
        marker_color=colors,
        text=[f"{a:.0f} min" if c > 0 else "No data" for a, c in zip(avgs, counts)],
        textposition="outside",
        error_y=dict(
            type="data",
            symmetric=False,
            array=[mx - a for mx, a in zip(maxs, avgs)],
            arrayminus=[a - mn for a, mn in zip(avgs, mins)],
            color="rgba(95,94,90,0.4)",
            thickness=1.5,
        ),
        hovertemplate="%{x}<br>Avg: %{y:.1f} min<extra></extra>",
    )

    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="Minutes", title_font_size=10, tickfont_size=10,
                   showgrid=True, gridcolor="rgba(136,135,128,0.15)"),
        xaxis=dict(tickfont_size=10, showgrid=False),
        font=dict(family="sans-serif", size=11),
        showlegend=False,
    )
    return fig