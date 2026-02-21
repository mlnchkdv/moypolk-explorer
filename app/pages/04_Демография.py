"""🎖️ Демография — возраст × звание, конвергенция."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from config import PLOTLY_LAYOUT, BLUE, RED, LIGHT_BLUE, ORANGE, GREEN, PALETTE, AGE_GAP_RANGE
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

with st.expander("ℹ️ Как читать"):
    st.markdown(
        "Каждая кривая — распределение возраста на момент гибели для определённой "
        "категории звания. Наложение (overlap) показывает, насколько схожи или различны "
        "возрастные профили рядовых и офицеров."
    )

if not df.empty and "rank_group" in df.columns and "age" in df.columns:
    rank_groups = sorted(df["rank_group"].unique())
    colors = {rg: PALETTE[i % len(PALETTE)] for i, rg in enumerate(rank_groups)}

    fig = go.Figure()
    for rg in rank_groups:
        sub = df[df["rank_group"] == rg]
        if "count" in sub.columns:
            # Данные уже агрегированы: age, count
            fig.add_trace(go.Scatter(
                x=sub["age"],
                y=sub["count"],
                mode="lines",
                name=rg,
                fill="tozeroy",
                opacity=0.5,
                line=dict(color=colors[rg], width=2),
                hovertemplate=f"{rg}<br>Возраст: %{{x}}<br>Карточек: %{{y:,.0f}}<extra></extra>",
            ))
        else:
            # Если count отсутствует, используем histogram-like подход
            fig.add_trace(go.Histogram(
                x=sub["age"],
                name=rg,
                marker_color=colors[rg],
                opacity=0.5,
                nbinsx=50,
            ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Распределение возраста по категориям звания",
        xaxis_title="Возраст (лет)",
        yaxis_title="Количество",
        barmode="overlay",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

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
        # Агрегация: средневзвешенный возраст по (rank_group, death_year)
        # FIX: векторная агрегация вместо groupby().apply() (FutureWarning в pandas 2.x)
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
                line=dict(color=colors[rg], width=2),
                marker=dict(size=8),
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
            # Разрыв между первой (рядовые) и последней (офицеры) группой
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

    # ═══════════════════════════════════════════════════════════════
    # 3. Таблица KS-тестов
    # ═══════════════════════════════════════════════════════════════
    st.subheader("Тесты Колмогорова–Смирнова")

    with st.expander("ℹ️ Метод"):
        st.markdown(
            "Двухвыборочный тест KS проверяет, различаются ли распределения возраста "
            "между парами категорий звания. Малый p-value (< 0.05) означает "
            "статистически значимое различие. "
            "Реализован на NumPy без внешних зависимостей."
        )

    def ks_2samp_numpy(x: np.ndarray, y: np.ndarray):
        """Двухвыборочный тест KS на основе NumPy."""
        if len(x) == 0 or len(y) == 0:
            return np.nan, np.nan
        x = np.sort(x)
        y = np.sort(y)
        n1, n2 = len(x), len(y)
        combined = np.sort(np.concatenate([x, y]))
        cdf_x = np.searchsorted(x, combined, side="right") / n1
        cdf_y = np.searchsorted(y, combined, side="right") / n2
        d = float(np.max(np.abs(cdf_x - cdf_y)))
        # Аппроксимация p-value через распределение Колмогорова
        n_eff = (n1 * n2) / (n1 + n2)
        z = d * np.sqrt(n_eff)
        # P = 2 * sum_{k=1}^{inf} (-1)^{k-1} * exp(-2 k^2 z^2)
        p = 2.0 * sum(
            ((-1) ** (k - 1)) * np.exp(-2.0 * k * k * z * z)
            for k in range(1, 50)
        )
        p = float(np.clip(p, 0.0, 1.0))
        return d, p

    if len(rank_groups) >= 2:
        # Реконструируем выборки из агрегированных данных (age, count)
        # Ограничиваем до 5000 точек на группу для скорости
        MAX_SAMPLE = 5000
        samples = {}
        for rg in rank_groups:
            sub = df[df["rank_group"] == rg]
            if "count" in sub.columns:
                ages = sub["age"].values.astype(int)
                counts = sub["count"].values.astype(int)
                expanded = np.repeat(ages, counts)
                if len(expanded) > MAX_SAMPLE:
                    rng = np.random.default_rng(42)
                    expanded = rng.choice(expanded, MAX_SAMPLE, replace=False)
                samples[rg] = expanded
            else:
                samples[rg] = sub["age"].dropna().values

        ks_data = []
        for i in range(len(rank_groups)):
            for j in range(i + 1, len(rank_groups)):
                rg1, rg2 = rank_groups[i], rank_groups[j]
                x, y = samples.get(rg1, np.array([])), samples.get(rg2, np.array([]))
                d, p = ks_2samp_numpy(x, y)
                if np.isnan(d):
                    sig = "нет данных"
                elif p < 0.001:
                    sig = "✅ Да (p < 0.001)"
                elif p < 0.05:
                    sig = "✅ Да (p < 0.05)"
                else:
                    sig = "❌ Нет (p ≥ 0.05)"
                ks_data.append({
                    "Группа 1": rg1,
                    "Группа 2": rg2,
                    "n₁": len(x),
                    "n₂": len(y),
                    "KS-статистика": f"{d:.4f}" if not np.isnan(d) else "—",
                    "p-value": f"{p:.4f}" if not np.isnan(p) else "—",
                    "Значимое различие": sig,
                })

        st.dataframe(pd.DataFrame(ks_data), use_container_width=True, hide_index=True)

        st.info(
            "**Вывод для исследователя.** Значимые различия в распределениях возраста "
            "между группами (p < 0.05) подтверждают, что война не «выровняла» демографию "
            "полностью: возрастные профили разных категорий звания статистически различались. "
            "Сравните KS-статистику с графиком конвергенции: "
            "высокая статистика при малом разрыве медиан указывает на различие в форме "
            "распределения (дисперсия, асимметрия), а не только в центральной тенденции.",
            icon="🔬",
        )

else:
    st.info(
        "Данные rank_age_distribution.parquet не найдены или не содержат "
        "необходимые столбцы (rank_group, age)."
    )
