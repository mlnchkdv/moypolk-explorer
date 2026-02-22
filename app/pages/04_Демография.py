"""🎖️ Демография — возраст × звание, конвергенция."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from config import PLOTLY_LAYOUT, BLUE, RED, PALETTE, AGE_GAP_RANGE, TOTAL_CARDS
from data_loader import load_rank_age_distribution

st.title("🎖️ Демография ветеранов")

st.markdown(
    "Анализ возрастного распределения по воинским званиям и годам гибели. "
    "Показана конвергенция возрастных профилей — война стирала привычные различия."
)

# ── Данные ────────────────────────────────────────────────────────
df = load_rank_age_distribution()

# ═══════════════════════════════════════════════════════════════════
# 1. Overlapping histograms: возраст × звание
# ═══════════════════════════════════════════════════════════════════
st.subheader("Распределение возраста по званиям")

if not df.empty and "rank_group" in df.columns and "age" in df.columns:
    total_records = int(df["count"].sum()) if "count" in df.columns else len(df)
    st.caption(
        f"Рассчитано на основе **{total_records:,}** записей "
        f"(из {TOTAL_CARDS:,} карточек в датасете) с указанными годами рождения и гибели.".replace(",", "\u202f")
    )

    with st.expander("ℹ️ Как читать"):
        st.markdown(
            "Каждая кривая — распределение возраста на момент гибели для определённой "
            "категории звания. Наложение (overlap) показывает, насколько схожи или различны "
            "возрастные профили рядовых и офицеров."
        )

    rank_groups = sorted(df["rank_group"].unique())
    colors = {rg: PALETTE[i % len(PALETTE)] for i, rg in enumerate(rank_groups)}

    fig = go.Figure()
    for rg in rank_groups:
        sub = df[df["rank_group"] == rg]
        if "count" in sub.columns:
            # Агрегируем count по age для каждой группы звания (суммируем годы гибели)
            age_totals = sub.groupby("age")["count"].sum().sort_index()
            fig.add_trace(go.Scatter(
                x=age_totals.index,
                y=age_totals.values,
                mode="lines",
                name=rg,
                fill="tozeroy",
                line=dict(color=colors[rg], width=3),
                opacity=0.6,
                hovertemplate=f"{rg}<br>Возраст: %{{x}}<br>Карточек: %{{y:,.0f}}<extra></extra>",
            ))
        else:
            fig.add_trace(go.Histogram(
                x=sub["age"],
                name=rg,
                marker_color=colors[rg],
                opacity=0.6,
                nbinsx=50,
            ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Распределение возраста по категориям звания",
        xaxis_title="Возраст (лет)",
        yaxis_title="Количество карточек",
        barmode="overlay",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Вывод для исследователя.** Пик распределения для рядовых приходится на "
        "18–25 лет — призывной возраст. Офицеры распределены шире: кадровый состав был "
        "старше на начало войны. Совпадение пиков в 20–25 лет указывает на младших "
        "лейтенантов из ускоренных выпусков офицерских курсов 1941–1942.",
        icon="🔬",
    )

    # ═══════════════════════════════════════════════════════════════
    # 2. Медианный возраст по годам гибели — конвергенция
    # ═══════════════════════════════════════════════════════════════
    st.subheader("Конвергенция возрастных профилей")

    with st.expander("ℹ️ Что такое конвергенция?"):
        st.markdown(
            f"В начале войны разрыв медианного возраста между рядовыми и офицерами "
            f"составлял **{AGE_GAP_RANGE}** к 1945 году. "
            "Это объясняется тем, что с ростом мобилизации и потерь "
            "различия между возрастными когортами стирались."
        )

    if "death_year" in df.columns:
        if "count" in df.columns:
            df_tmp = df.copy()
            df_tmp["weighted_age"] = df_tmp["age"] * df_tmp["count"]
            _agg = df_tmp.groupby(["rank_group", "death_year"]).agg(
                sum_w=("weighted_age", "sum"),
                sum_c=("count", "sum"),
            ).reset_index()
            _agg["median_age"] = np.where(
                _agg["sum_c"] > 0, _agg["sum_w"] / _agg["sum_c"], np.nan
            )
            agg = _agg.drop(columns=["sum_w", "sum_c"])
        else:
            agg = df.groupby(["rank_group", "death_year"])["age"].median().reset_index(name="median_age")

        agg = agg.dropna(subset=["median_age"])
        war_years = agg[agg["death_year"].between(1941, 1945)]

        fig2 = go.Figure()
        for rg in rank_groups:
            sub = war_years[war_years["rank_group"] == rg].sort_values("death_year")
            if sub.empty:
                continue
            fig2.add_trace(go.Scatter(
                x=sub["death_year"],
                y=sub["median_age"],
                mode="lines+markers",
                name=rg,
                line=dict(color=colors[rg], width=3),
                marker=dict(size=10),
                hovertemplate=f"{rg}<br>Год: %{{x}}<br>Медианный возраст: %{{y:.1f}}<extra></extra>",
            ))

        fig2.update_layout(
            **PLOTLY_LAYOUT,
            title="Медианный возраст по годам гибели (1941–1945)",
            xaxis_title="Год гибели",
            yaxis_title="Медианный возраст (лет)",
            height=420,
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Разрыв
        if len(rank_groups) >= 2:
            st.markdown("#### Динамика возрастного разрыва")
            rg1, rg2 = rank_groups[0], rank_groups[-1]
            m1 = war_years[war_years["rank_group"] == rg1].set_index("death_year")["median_age"]
            m2 = war_years[war_years["rank_group"] == rg2].set_index("death_year")["median_age"]
            gap = (m2 - m1).dropna().reset_index()
            gap.columns = ["year", "gap"]

            if not gap.empty:
                fig3 = go.Figure(go.Bar(
                    x=gap["year"],
                    y=gap["gap"],
                    marker_color=RED,
                    hovertemplate="Год %{x}<br>Разрыв: %{y:.1f} лет<extra></extra>",
                ))
                fig3.update_layout(
                    **PLOTLY_LAYOUT,
                    title=f"Разрыв медианного возраста: {rg2} − {rg1}",
                    xaxis_title="Год гибели",
                    yaxis_title="Разница (лет)",
                    height=350,
                    showlegend=False,
                )
                st.plotly_chart(fig3, use_container_width=True)

        st.info(
            "**Вывод для исследователя.** Сужение разрыва к 1945 г. объясняется двумя "
            "факторами: 1) массовая мобилизация более старших возрастов в рядовой состав; "
            "2) появление молодых офицеров из ускоренных выпусков. "
            "Если разрыв в 1941 г. максимален — это отражает кадровый состав мирного "
            "времени, когда офицеры были значительно старше рядовых.",
            icon="🔬",
        )

else:
    st.info(
        "Данные rank_age_distribution.parquet не найдены или не содержат "
        "необходимые столбцы (rank_group, age)."
    )
