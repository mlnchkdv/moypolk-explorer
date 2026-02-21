"""📊 DMI — индекс цифровой памяти по регионам."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from config import PLOTLY_LAYOUT, BLUE, RED, LIGHT_BLUE, ORANGE, GREEN, DMI_GINI, STORY_VS_AWARDS_R
from data_loader import load_dmi_by_region

st.title("📊 Индекс цифровой памяти (DMI)")

st.markdown(
    "DMI — композитный индекс, характеризующий «полноту» цифровой памяти региона. "
    "Учитывает долю карточек с текстом, фотографиями, наградами и другие параметры."
)

# ── Данные ────────────────────────────────────────────────────────
df = load_dmi_by_region()

if df.empty:
    st.info("Данные dmi_by_region.parquet не найдены.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════
# 1. Scatter: DMI vs Volume
# ═══════════════════════════════════════════════════════════════════
st.subheader("DMI vs. объём карточек")

with st.expander("ℹ️ Метод"):
    st.markdown(
        "Каждая точка — регион. По оси X — общее число карточек (log), "
        "по оси Y — индекс DMI. Пунктир — линейная регрессия. "
        "R² показывает, какая доля вариации DMI объясняется объёмом."
    )

if "count" in df.columns and "dmi" in df.columns:
    df_plot = df[df["count"] > 0].copy()
    df_plot["log_count"] = np.log10(df_plot["count"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot["log_count"],
        y=df_plot["dmi"],
        mode="markers",
        marker=dict(color=BLUE, size=8, opacity=0.7, line=dict(width=1, color="white")),
        text=df_plot["region"] if "region" in df_plot.columns else None,
        hovertemplate="%{text}<br>Карточек: 10^%{x:.1f}<br>DMI: %{y:.3f}<extra></extra>",
    ))

    # Тренд
    if len(df_plot) > 3:
        z = np.polyfit(df_plot["log_count"], df_plot["dmi"], 1)
        trend_x = np.linspace(df_plot["log_count"].min(), df_plot["log_count"].max(), 100)
        trend_y = np.polyval(z, trend_x)
        # R²
        y_pred = np.polyval(z, df_plot["log_count"])
        ss_res = np.sum((df_plot["dmi"] - y_pred) ** 2)
        ss_tot = np.sum((df_plot["dmi"] - df_plot["dmi"].mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        fig.add_trace(go.Scatter(
            x=trend_x, y=trend_y,
            mode="lines",
            name=f"R² = {r2:.2f}",
            line=dict(color=RED, dash="dash", width=2),
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="DMI vs. объём карточек",
        xaxis_title="log₁₀(Карточек)",
        yaxis_title="DMI",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# 2. Scatter: Story% vs Awards%
# ═══════════════════════════════════════════════════════════════════
st.subheader("Доля текстов vs. доля наград")

with st.expander("ℹ️ Интерпретация"):
    st.markdown(
        f"Отрицательная корреляция (r = {STORY_VS_AWARDS_R}) означает, что регионы "
        "с большей долей текстовых описаний имеют меньшую долю упомянутых наград "
        "и наоборот. Это может отражать разные стратегии документирования."
    )

story_col = "story_pct" if "story_pct" in df.columns else None
awards_col = "awards_pct" if "awards_pct" in df.columns else None

if story_col and awards_col:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df[story_col],
        y=df[awards_col],
        mode="markers",
        marker=dict(color=ORANGE, size=8, opacity=0.7, line=dict(width=1, color="white")),
        text=df["region"] if "region" in df.columns else None,
        hovertemplate="%{text}<br>Story: %{x:.1f}%<br>Awards: %{y:.1f}%<extra></extra>",
    ))

    df_scatter = df[[story_col, awards_col]].dropna()
    if len(df_scatter) > 3:
        z = np.polyfit(df_scatter[story_col], df_scatter[awards_col], 1)
        tx = np.linspace(df_scatter[story_col].min(), df_scatter[story_col].max(), 100)
        fig2.add_trace(go.Scatter(
            x=tx, y=np.polyval(z, tx),
            mode="lines",
            name=f"r = {STORY_VS_AWARDS_R}",
            line=dict(color=RED, dash="dash", width=2),
        ))

    fig2.update_layout(
        **PLOTLY_LAYOUT,
        title="Доля текстов vs. доля наград по регионам",
        xaxis_title="Доля с текстом (%)",
        yaxis_title="Доля с наградами (%)",
        height=420,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# 3. Гистограмма DMI (Gini)
# ═══════════════════════════════════════════════════════════════════
st.subheader("Распределение DMI по регионам")

col1, col2 = st.columns([2, 1])

with col1:
    if "dmi" in df.columns:
        fig3 = go.Figure(go.Histogram(
            x=df["dmi"],
            nbinsx=30,
            marker_color=LIGHT_BLUE,
            hovertemplate="DMI: %{x:.3f}<br>Регионов: %{y}<extra></extra>",
        ))
        fig3.add_vline(
            x=df["dmi"].mean(),
            line_dash="dash", line_color=RED,
            annotation_text=f"Среднее: {df['dmi'].mean():.3f}",
            annotation_position="top right",
        )
        fig3.update_layout(
            **PLOTLY_LAYOUT,
            title=f"Распределение DMI (Gini = {DMI_GINI})",
            xaxis_title="DMI",
            yaxis_title="Регионов",
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)

with col2:
    st.metric("Gini DMI", f"{DMI_GINI:.3f}")
    st.markdown(
        f"Коэффициент Джини = **{DMI_GINI}** указывает на умеренное неравенство "
        "в полноте цифровой памяти между регионами."
    )

# ═══════════════════════════════════════════════════════════════════
# 4. Heatmap корреляций
# ═══════════════════════════════════════════════════════════════════
st.subheader("Корреляции компонентов DMI")

with st.expander("ℹ️ Метод"):
    st.markdown(
        "Корреляционная матрица (Pearson) между компонентами индекса: "
        "доля текстов, доля фото, доля наград, объём и др."
    )

numeric_cols = [c for c in df.columns if df[c].dtype in ["float64", "float32", "int64"] and c != "count"]
if len(numeric_cols) >= 3:
    corr = df[numeric_cols].corr()

    fig4 = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale="RdBu_r",
        zmid=0,
        text=np.round(corr.values, 2),
        texttemplate="%{text}",
        hovertemplate="%{y} × %{x}<br>r = %{z:.3f}<extra></extra>",
    ))
    fig4.update_layout(
        **PLOTLY_LAYOUT,
        title="Корреляции между компонентами",
        height=500,
        xaxis=dict(tickangle=45, tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10)),
    )
    st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# 5. Таблица регионов с сортировкой
# ═══════════════════════════════════════════════════════════════════
st.subheader("Регионы по DMI")

display_cols = ["region", "dmi", "count"] if "region" in df.columns else df.columns.tolist()
available = [c for c in display_cols if c in df.columns]
# Добавляем процентные столбцы
for c in ["story_pct", "photo_pct", "awards_pct"]:
    if c in df.columns and c not in available:
        available.append(c)

sort_col = st.selectbox("Сортировать по", available, index=available.index("dmi") if "dmi" in available else 0)
ascending = st.checkbox("По возрастанию", value=False)

df_display = df[available].sort_values(sort_col, ascending=ascending).reset_index(drop=True)
st.dataframe(df_display, use_container_width=True, height=500, hide_index=True)
