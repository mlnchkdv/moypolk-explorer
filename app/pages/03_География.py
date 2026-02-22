"""🗺️ География — миграция памяти, межрегиональные связи."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import PLOTLY_LAYOUT, BLUE, RED, LIGHT_BLUE, ORANGE, GREEN, PCT_LOCAL_MEMORY, TOTAL_CARDS
from data_loader import load_migration_matrix, load_network_edges

st.title("🗺️ География памяти")

st.markdown(
    "Пространственный анализ: откуда родом ветераны и откуда поданы карточки. "
    "Миграционные потоки XX века отражаются в географии цифровой памяти."
)
st.caption(f"Миграционный анализ рассчитан на основе **{TOTAL_CARDS:,}** карточек.".replace(",", "\u202f"))

# ── Данные ────────────────────────────────────────────────────────
df_mig = load_migration_matrix()
df_edges = load_network_edges()

# ═══════════════════════════════════════════════════════════════════
# 1. Heatmap миграции
# ═══════════════════════════════════════════════════════════════════
st.subheader("Матрица миграции: рождение → подача карточки")

with st.expander("ℹ️ Как читать"):
    st.markdown(
        "Строки — регион рождения ветерана, столбцы — регион подачи карточки. "
        "Интенсивность цвета — количество карточек. Диагональ — «локальная память» "
        "(карточка подана из того же региона). Отклонения от диагонали — миграция."
    )

if not df_mig.empty:
    top_n = st.slider(
        "Количество регионов",
        min_value=10,
        max_value=min(50, len(df_mig)),
        value=20,
        step=5,
        key="geo_top_n",
    )

    # Pivot к матрице
    if "birth_region" in df_mig.columns and "submit_region" in df_mig.columns:
        # Определяем топ-N регионов по суммарному количеству
        region_sums = (
            df_mig.groupby("birth_region")["count"].sum()
            .add(df_mig.groupby("submit_region")["count"].sum(), fill_value=0)
        )
        top_regions = region_sums.nlargest(top_n).index.tolist()

        sub = df_mig[
            df_mig["birth_region"].isin(top_regions) & df_mig["submit_region"].isin(top_regions)
        ]
        matrix = sub.pivot_table(
            index="birth_region", columns="submit_region",
            values="count", fill_value=0, aggfunc="sum",
        )
        # Упорядочиваем
        common = [r for r in top_regions if r in matrix.index and r in matrix.columns]
        matrix = matrix.loc[common, common]

        fig = go.Figure(go.Heatmap(
            z=matrix.values,
            x=matrix.columns.tolist(),
            y=matrix.index.tolist(),
            colorscale="Blues",
            hovertemplate=(
                "Рождение: %{y}<br>Подача: %{x}<br>Карточек: %{z:,.0f}<extra></extra>"
            ),
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=f"Миграционная матрица (топ-{top_n} регионов)",
            xaxis_title="Регион подачи",
            yaxis_title="Регион рождения",
            height=max(500, top_n * 25),
        )
        # FIX: xaxis/yaxis конфликтуют с PLOTLY_LAYOUT — переопределяем отдельным вызовом
        fig.update_xaxes(tickangle=45, tickfont=dict(size=10))
        fig.update_yaxes(tickfont=dict(size=10), autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Ожидаются столбцы birth_region, submit_region, count.")
else:
    st.info("Данные migration_matrix.parquet не найдены.")

# ═══════════════════════════════════════════════════════════════════
# 2. Доля локальной / мигрировавшей памяти
# ═══════════════════════════════════════════════════════════════════
st.subheader("Локальная vs. мигрировавшая память")

col1, col2 = st.columns([1, 2])

with col1:
    fig_pie = go.Figure(go.Pie(
        labels=["Локальная", "Мигрировавшая"],
        values=[PCT_LOCAL_MEMORY, 100 - PCT_LOCAL_MEMORY],
        marker=dict(colors=[BLUE, ORANGE]),
        hole=0.4,
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))
    fig_pie.update_layout(
        **PLOTLY_LAYOUT,
        title="Доля локальной памяти",
        height=350,
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown(
        f"""
        **{PCT_LOCAL_MEMORY}%** карточек поданы из того же региона, где родился ветеран
        («локальная память»).

        **{100 - PCT_LOCAL_MEMORY:.1f}%** — из другого региона. Это отражает масштабные
        миграционные процессы XX века: индустриализацию, эвакуацию, послевоенную
        урбанизацию.

        Память о ветеране чаще «путешествует» вместе с его потомками —
        дети и внуки публикуют карточки из городов, куда семья переехала.
        """
    )

# ═══════════════════════════════════════════════════════════════════
# 3. Топ межрегиональных связей
# ═══════════════════════════════════════════════════════════════════
st.subheader("Сильнейшие межрегиональные связи")

with st.expander("ℹ️ Метод"):
    st.markdown(
        "Топ-20 пар регионов (рождение → подача) с наибольшим числом карточек. "
        "Диагональные пары (один регион) исключены — показаны только миграционные потоки."
    )

if not df_edges.empty:
    top_edges = df_edges.nlargest(20, "count")
    if "source" in top_edges.columns and "target" in top_edges.columns:
        top_edges["label"] = top_edges["source"] + " → " + top_edges["target"]
        top_edges = top_edges.sort_values("count")

        fig_bar = go.Figure(go.Bar(
            y=top_edges["label"],
            x=top_edges["count"],
            orientation="h",
            marker_color=LIGHT_BLUE,
            hovertemplate="%{y}<br>Карточек: %{x:,.0f}<extra></extra>",
        ))
        # FIX: margin конфликтует с PLOTLY_LAYOUT — разбиваем на 2 вызова
        fig_bar.update_layout(
            **PLOTLY_LAYOUT,
            title="Топ-20 межрегиональных потоков памяти",
            xaxis_title="Количество карточек",
            height=550,
            showlegend=False,
        )
        fig_bar.update_layout(margin=dict(l=300, r=30, t=50, b=50))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("Ожидаются столбцы source, target, count.")
else:
    st.info("Данные network_edges.parquet не найдены.")
