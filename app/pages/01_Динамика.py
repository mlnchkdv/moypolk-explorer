"""📈 Динамика — временные ряды публикаций."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from config import PLOTLY_LAYOUT, BLUE, RED, LIGHT_BLUE, ORANGE, MONTHS_RU, MONTHS_RU_FULL
from data_loader import load_monthly_counts, load_halflife_yearly

st.title("📈 Динамика публикаций")

st.markdown(
    "Анализ временной динамики: когда и как публиковались карточки ветеранов. "
    "Выявление сезонных паттернов и скорости затухания активности."
)

# ── Данные ────────────────────────────────────────────────────────
df_monthly = load_monthly_counts()
df_halflife = load_halflife_yearly()

# ═══════════════════════════════════════════════════════════════════
# 1. Помесячная динамика
# ═══════════════════════════════════════════════════════════════════
st.subheader("Помесячная динамика публикаций")

with st.expander("ℹ️ Как читать этот график"):
    st.markdown(
        "**Area chart** показывает количество новых карточек по месяцам. "
        "Аннотации отмечают ключевые события, повлиявшие на динамику: "
        "юбилеи Победы, пандемия COVID-19 и др."
    )

if not df_monthly.empty:
    df_m = df_monthly.copy()
    df_m["month"] = pd.to_datetime(df_m["month"])

    # Фильтр по годам
    years = sorted(df_m["month"].dt.year.unique())
    year_range = st.slider(
        "Диапазон лет",
        min_value=int(years[0]),
        max_value=int(years[-1]),
        value=(int(years[0]), int(years[-1])),
        key="dynamics_years",
    )
    mask = df_m["month"].dt.year.between(*year_range)
    df_plot = df_m[mask]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot["month"],
        y=df_plot["count"],
        fill="tozeroy",
        fillcolor="rgba(21,101,192,0.15)",
        line=dict(color=BLUE, width=2),
        name="Публикации",
        hovertemplate="%{x|%B %Y}<br>Карточек: %{y:,.0f}<extra></extra>",
    ))

    # Аннотации
    annotations = [
        ("2015-05-01", "70-летие\nПобеды", 0.95),
        ("2020-04-01", "COVID-19", 0.85),
        ("2025-05-01", "80-летие\nПобеды", 0.95),
    ]
    for date_str, label, y_rel in annotations:
        dt = pd.Timestamp(date_str)
        if year_range[0] <= dt.year <= year_range[1]:
            fig.add_annotation(
                x=dt, y=df_plot["count"].max() * y_rel,
                text=label, showarrow=True, arrowhead=2,
                arrowcolor=RED, font=dict(color=RED, size=11),
                ax=0, ay=-35,
            )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Количество опубликованных карточек по месяцам",
        xaxis_title="Дата",
        yaxis_title="Карточек",
        showlegend=False,
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Данные monthly_counts.parquet не найдены.")

# ═══════════════════════════════════════════════════════════════════
# 2. Сезонность (bar по месяцам)
# ═══════════════════════════════════════════════════════════════════
st.subheader("Сезонность: распределение по месяцам")

with st.expander("ℹ️ Метод"):
    st.markdown(
        "Суммарное число карточек за каждый месяц (агрегат по всем годам). "
        "Выраженный пик в мае связан с Днём Победы 9 мая."
    )

if not df_monthly.empty:
    df_s = df_monthly.copy()
    df_s["month_dt"] = pd.to_datetime(df_s["month"])
    df_s["m"] = df_s["month_dt"].dt.month
    seasonal = df_s.groupby("m")["count"].sum().reset_index()
    seasonal["month_name"] = seasonal["m"].map(lambda x: MONTHS_RU[x - 1])
    seasonal["color"] = seasonal["m"].apply(lambda x: RED if x == 5 else BLUE)

    fig2 = go.Figure(go.Bar(
        x=seasonal["month_name"],
        y=seasonal["count"],
        marker_color=seasonal["color"],
        hovertemplate="%{x}<br>Карточек: %{y:,.0f}<extra></extra>",
    ))
    fig2.update_layout(
        **PLOTLY_LAYOUT,
        title="Суммарные публикации по месяцам года",
        xaxis_title="Месяц",
        yaxis_title="Карточек (всего)",
        showlegend=False,
        height=400,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# 3. Нормализованные профили по годам
# ═══════════════════════════════════════════════════════════════════
st.subheader("Нормализованные профили сезонности")

with st.expander("ℹ️ Метод"):
    st.markdown(
        "Для каждого года доля карточек по месяцам нормализована к 100%. "
        "Позволяет сравнить «форму» сезонности между годами: "
        "становится ли пик в мае более или менее выраженным."
    )

if not df_monthly.empty:
    df_n = df_monthly.copy()
    df_n["month_dt"] = pd.to_datetime(df_n["month"])
    df_n["year"] = df_n["month_dt"].dt.year
    df_n["m"] = df_n["month_dt"].dt.month

    # Нормализация внутри года
    year_totals = df_n.groupby("year")["count"].sum()
    df_n = df_n.merge(year_totals.rename("year_total"), on="year")
    df_n["pct"] = df_n["count"] / df_n["year_total"] * 100
    df_n["month_name"] = df_n["m"].map(lambda x: MONTHS_RU[x - 1])

    top_years = year_totals.nlargest(6).index.tolist()
    df_top = df_n[df_n["year"].isin(top_years)]

    fig3 = go.Figure()
    colors = [BLUE, RED, LIGHT_BLUE, ORANGE, "#66BB6A", "#AB47BC"]
    for i, yr in enumerate(sorted(top_years)):
        sub = df_top[df_top["year"] == yr].sort_values("m")
        fig3.add_trace(go.Scatter(
            x=sub["month_name"],
            y=sub["pct"],
            mode="lines+markers",
            name=str(yr),
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=5),
            hovertemplate=f"{yr}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))

    fig3.update_layout(
        **PLOTLY_LAYOUT,
        title="Доля публикаций по месяцам (нормализовано, топ-6 годов)",
        xaxis_title="Месяц",
        yaxis_title="Доля (%)",
        height=400,
    )
    st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# 4. Полураспад
# ═══════════════════════════════════════════════════════════════════
st.subheader("Полураспад активности")

with st.expander("ℹ️ Что такое полураспад?"):
    st.markdown(
        "**Полураспад** — число дней после пика (обычно 9 мая), за которое "
        "ежедневное число публикаций сокращается вдвое. Метрика характеризует "
        "«длительность внимания» — как быстро затухает волна памяти."
    )

if not df_halflife.empty:
    df_h = df_halflife.sort_values("year")

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        x=df_h["year"],
        y=df_h["halflife"],
        marker_color=BLUE,
        name="Полураспад (дни)",
        hovertemplate="Год %{x}<br>Полураспад: %{y:.1f} дней<extra></extra>",
    ))

    # Линейный тренд
    if len(df_h) > 2:
        z = np.polyfit(df_h["year"], df_h["halflife"], 1)
        trend_y = np.polyval(z, df_h["year"])
        fig4.add_trace(go.Scatter(
            x=df_h["year"],
            y=trend_y,
            mode="lines",
            name=f"Тренд ({z[0]:+.2f} дн/год)",
            line=dict(color=RED, dash="dash", width=2),
        ))

    fig4.update_layout(
        **PLOTLY_LAYOUT,
        title="Полураспад активности по годам",
        xaxis_title="Год",
        yaxis_title="Дни",
        height=400,
    )
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Данные halflife_yearly.parquet не найдены.")
