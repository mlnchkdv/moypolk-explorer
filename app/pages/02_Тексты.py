"""📝 Тексты — анализ нарративов, тональности, лексики, тем, NER."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from config import (
    PLOTLY_LAYOUT, BLUE, RED, LIGHT_BLUE, ORANGE, GREEN, GREY,
    NARRATIVE_COLORS, NARRATIVE_TYPES, PALETTE,
)
from data_loader import (
    load_narrative_types_yearly, load_sentiment_yearly,
    load_mattr_yearly, load_lda_topics, load_lda_evolution,
    load_ner_top_entities,
)

st.title("📝 Анализ текстов")

st.markdown(
    "Многомерный анализ текстового корпуса: типы нарративов, тональность, "
    "лексическое разнообразие, тематическое моделирование и извлечение именованных сущностей."
)

# ── Данные ────────────────────────────────────────────────────────
df_narr = load_narrative_types_yearly()
df_sent = load_sentiment_yearly()
df_mattr = load_mattr_yearly()
df_topics = load_lda_topics()
df_lda_ev = load_lda_evolution()
df_ner = load_ner_top_entities()

# ═══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📖 Нарративы", "💬 Тональность", "🔤 MATTR", "🧩 LDA-темы", "🏷️ NER",
])

# ═══════════════════════════════════════════════════════════════════
# TAB 1: Нарративы
# ═══════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Типы нарративов")

    with st.expander("ℹ️ Методология"):
        st.markdown(
            "Тексты классифицируются на 4 типа по структурным признакам:\n\n"
            "- **Формуляр** — краткие анкетные данные (ФИО, даты, звание)\n"
            "- **Мемуар** — развёрнутые личные воспоминания\n"
            "- **Семейная история** — рассказ от лица потомков\n"
            "- **Смешанный** — сочетание нескольких типов\n\n"
            "Классификация выполнена на основе длины текста, наличия маркеров "
            "первого/третьего лица и структурных паттернов."
        )

    if not df_narr.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Stacked area
            # FIX: yaxis уже есть в PLOTLY_LAYOUT — переопределяем отдельным вызовом
            fig = go.Figure()
            for ntype in NARRATIVE_TYPES:
                if ntype in df_narr.columns:
                    fig.add_trace(go.Scatter(
                        x=df_narr["year"],
                        y=df_narr[ntype],
                        mode="lines",
                        name=ntype,
                        stackgroup="one",
                        line=dict(color=NARRATIVE_COLORS.get(ntype, GREY), width=0.5),
                        hovertemplate=f"{ntype}<br>Год: %{{x}}<br>Доля: %{{y:.1f}}%<extra></extra>",
                    ))
            fig.update_layout(
                **PLOTLY_LAYOUT,
                title="Доли нарративов по годам (%)",
                xaxis_title="Год публикации",
                yaxis_title="Доля (%)",
                height=420,
            )
            fig.update_yaxes(range=[0, 100], gridcolor="#E0E0E0")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Средние доли — горизонтальный bar
            means = {}
            for ntype in NARRATIVE_TYPES:
                if ntype in df_narr.columns:
                    means[ntype] = df_narr[ntype].mean()
            if means:
                fig2 = go.Figure(go.Bar(
                    y=list(means.keys()),
                    x=list(means.values()),
                    orientation="h",
                    marker_color=[NARRATIVE_COLORS.get(k, GREY) for k in means],
                    hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
                ))
                fig2.update_layout(
                    **PLOTLY_LAYOUT,
                    title="Средняя доля каждого типа нарратива",
                    xaxis_title="Доля (%)",
                    height=420,
                )
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Данные narrative_types_yearly.parquet не найдены.")

# ═══════════════════════════════════════════════════════════════════
# TAB 2: Тональность
# ═══════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Тональность текстов")

    with st.expander("ℹ️ Методология"):
        st.markdown(
            "Sentiment score вычисляется с помощью модели анализа тональности, "
            "адаптированной для русскоязычных текстов. Значения от −1 (негативный) "
            "до +1 (позитивный). Показан средний балл по годам и по типам нарративов."
        )

    if not df_sent.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig = go.Figure()
            if "mean_score" in df_sent.columns:
                fig.add_trace(go.Scatter(
                    x=df_sent["year"],
                    y=df_sent["mean_score"],
                    mode="lines+markers",
                    line=dict(color=BLUE, width=2),
                    marker=dict(size=6),
                    name="Средний sentiment",
                    hovertemplate="Год %{x}<br>Score: %{y:.3f}<extra></extra>",
                ))
            fig.update_layout(
                **PLOTLY_LAYOUT,
                title="Средняя тональность по годам",
                xaxis_title="Год публикации",
                yaxis_title="Sentiment score",
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # По типам нарративов
            type_cols = [c for c in df_sent.columns if c.startswith("sentiment_")]
            if type_cols:
                means = {c.replace("sentiment_", ""): df_sent[c].mean() for c in type_cols}
                fig2 = go.Figure(go.Bar(
                    x=list(means.keys()),
                    y=list(means.values()),
                    marker_color=PALETTE[:len(means)],
                    hovertemplate="%{x}<br>Score: %{y:.3f}<extra></extra>",
                ))
                fig2.update_layout(
                    **PLOTLY_LAYOUT,
                    title="Тональность по типам нарративов",
                    xaxis_title="Тип",
                    yaxis_title="Средний score",
                    height=420,
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.caption("Разбивка по типам недоступна.")
    else:
        st.info("Данные sentiment_yearly.parquet не найдены.")

# ═══════════════════════════════════════════════════════════════════
# TAB 3: MATTR
# ═══════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Лексическое разнообразие (MATTR)")

    with st.expander("ℹ️ Что такое MATTR?"):
        st.markdown(
            "**MATTR** (Moving-Average Type-Token Ratio) — мера лексического "
            "разнообразия, устойчивая к длине текста. Вычисляется как среднее TTR "
            "в скользящем окне фиксированной длины.\n\n"
            "Снижение MATTR со временем может указывать на растущую шаблонность текстов."
        )

    if not df_mattr.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_mattr["year"],
                y=df_mattr["mattr"],
                mode="lines+markers",
                line=dict(color=BLUE, width=2),
                marker=dict(size=5),
                name="MATTR",
                hovertemplate="Год %{x}<br>MATTR: %{y:.4f}<extra></extra>",
            ))

            # Тренд
            if len(df_mattr) > 2:
                z = np.polyfit(df_mattr["year"], df_mattr["mattr"], 1)
                trend = np.polyval(z, df_mattr["year"])
                fig.add_trace(go.Scatter(
                    x=df_mattr["year"],
                    y=trend,
                    mode="lines",
                    name=f"Тренд ({z[0]:+.4f}/год)",
                    line=dict(color=RED, dash="dash", width=2),
                ))

            fig.update_layout(
                **PLOTLY_LAYOUT,
                title="Среднее лексическое разнообразие по годам",
                xaxis_title="Год публикации",
                yaxis_title="MATTR",
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # По типам нарративов
            type_cols = [c for c in df_mattr.columns if c.startswith("mattr_")]
            if type_cols:
                means = {c.replace("mattr_", ""): df_mattr[c].mean() for c in type_cols}
                fig2 = go.Figure(go.Bar(
                    x=list(means.keys()),
                    y=list(means.values()),
                    marker_color=PALETTE[:len(means)],
                    hovertemplate="%{x}<br>MATTR: %{y:.4f}<extra></extra>",
                ))
                fig2.update_layout(
                    **PLOTLY_LAYOUT,
                    title="MATTR по типам нарративов",
                    xaxis_title="Тип",
                    yaxis_title="Средний MATTR",
                    height=420,
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.caption("Разбивка по типам недоступна.")
    else:
        st.info("Данные mattr_yearly.parquet не найдены.")

# ═══════════════════════════════════════════════════════════════════
# TAB 4: LDA
# ═══════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Тематическое моделирование (LDA)")

    with st.expander("ℹ️ Методология"):
        st.markdown(
            "**LDA** (Latent Dirichlet Allocation) — метод автоматического выявления "
            "«скрытых тем» в текстовом корпусе. Модель обучена на 7 темах. "
            "Для каждой темы показаны ключевые слова и их веса.\n\n"
            "**Эволюция тем** показывает, как менялось распределение тем по годам."
        )

    if not df_topics.empty:
        # Bar charts для каждой темы
        topics_list = sorted(df_topics["topic_id"].unique())

        n_cols = 3
        cols = st.columns(n_cols)
        for i, tid in enumerate(topics_list[:7]):
            sub = df_topics[df_topics["topic_id"] == tid].nlargest(8, "weight")
            with cols[i % n_cols]:
                fig = go.Figure(go.Bar(
                    y=sub["word"],
                    x=sub["weight"],
                    orientation="h",
                    marker_color=PALETTE[i % len(PALETTE)],
                    hovertemplate="%{y}: %{x:.3f}<extra></extra>",
                ))
                topic_label = sub["topic_label"].iloc[0] if "topic_label" in sub.columns else f"Тема {tid}"
                # FIX: margin и yaxis конфликтуют с PLOTLY_LAYOUT — разбиваем на 2 вызова
                fig.update_layout(
                    **PLOTLY_LAYOUT,
                    title=f"{topic_label}",
                    height=280,
                    showlegend=False,
                )
                fig.update_layout(margin=dict(l=80, r=10, t=40, b=30))
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

    # Эволюция тем
    if not df_lda_ev.empty:
        st.markdown("---")
        st.markdown("#### Эволюция тем по годам")

        fig_ev = go.Figure()
        topic_cols = [c for c in df_lda_ev.columns if c.startswith("topic_")]
        for i, col in enumerate(topic_cols):
            label = col.replace("topic_", "").replace("_", " ").title()
            fig_ev.add_trace(go.Scatter(
                x=df_lda_ev["year"],
                y=df_lda_ev[col],
                mode="lines",
                name=label,
                stackgroup="one",
                line=dict(width=0.5, color=PALETTE[i % len(PALETTE)]),
                hovertemplate=f"{label}<br>Год: %{{x}}<br>Вес: %{{y:.3f}}<extra></extra>",
            ))

        fig_ev.update_layout(
            **PLOTLY_LAYOUT,
            title="Динамика тематических весов",
            xaxis_title="Год публикации",
            yaxis_title="Средний вес темы",
            height=450,
        )
        st.plotly_chart(fig_ev, use_container_width=True)

    if df_topics.empty and df_lda_ev.empty:
        st.info("Данные LDA не найдены.")

# ═══════════════════════════════════════════════════════════════════
# TAB 5: NER
# ═══════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Именованные сущности (NER)")

    with st.expander("ℹ️ Методология"):
        st.markdown(
            "**NER** (Named Entity Recognition) — извлечение именованных сущностей "
            "из текстов карточек. Показаны топ-30 наиболее частых локаций "
            "и организаций, упомянутых в текстах."
        )

    if not df_ner.empty:
        col1, col2 = st.columns(2)

        for i, (etype, title, col) in enumerate([
            ("LOC", "Топ-30 локаций", col1),
            ("ORG", "Топ-30 организаций", col2),
        ]):
            sub = df_ner[df_ner["entity_type"] == etype].nlargest(30, "count")
            if sub.empty:
                continue
            with col:
                fig = go.Figure(go.Bar(
                    y=sub["entity"].iloc[::-1],
                    x=sub["count"].iloc[::-1],
                    orientation="h",
                    marker_color=BLUE if etype == "LOC" else ORANGE,
                    hovertemplate="%{y}<br>Упоминаний: %{x:,.0f}<extra></extra>",
                ))
                # FIX: margin конфликтует с PLOTLY_LAYOUT — разбиваем на 2 вызова
                fig.update_layout(
                    **PLOTLY_LAYOUT,
                    title=title,
                    height=700,
                    showlegend=False,
                )
                fig.update_layout(margin=dict(l=180, r=10, t=40, b=30))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Данные ner_top_entities.parquet не найдены.")
