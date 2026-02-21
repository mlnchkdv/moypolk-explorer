"""🔍 Поиск — полнотекстовый поиск по сэмплу 50K."""

import streamlit as st
import pandas as pd

from config import TOTAL_CARDS, SAMPLE_SIZE, BLUE
from data_loader import get_duckdb_connection

st.title("🔍 Поиск по карточкам ветеранов")

st.info(
    f"⚠️ **Сэмпл**: поиск выполняется по выборке **{SAMPLE_SIZE // 1000}K** "
    f"из {TOTAL_CARDS:,} карточек. Стратифицированная выборка по годам "
    "обеспечивает репрезентативность.".replace(",", " "),
    icon="ℹ️",
)

# ── DuckDB ────────────────────────────────────────────────────────
con = get_duckdb_connection()

if con is None:
    st.error(
        "Файл сэмпла не найден. Запустите `python scripts/prepare_data.py` "
        "для создания data/sample/soldiers_sample_50k.parquet."
    )
    st.stop()

# ── Фильтры ──────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    query_text = st.text_input(
        "🔍 Поиск по ФИО или тексту",
        placeholder="Введите имя, фамилию или ключевое слово...",
    )

with col2:
    # Получаем уникальные регионы
    try:
        regions = con.execute("SELECT DISTINCT region FROM soldiers WHERE region IS NOT NULL ORDER BY region").fetchdf()
        region_list = ["Все регионы"] + regions["region"].tolist()
    except Exception:
        region_list = ["Все регионы"]
    selected_region = st.selectbox("Регион", region_list)

with col3:
    # Получаем уникальные звания (топ-20)
    try:
        ranks = con.execute(
            "SELECT rank, COUNT(*) AS cnt FROM soldiers WHERE rank IS NOT NULL "
            "GROUP BY rank ORDER BY cnt DESC LIMIT 30"
        ).fetchdf()
        rank_list = ["Все звания"] + ranks["rank"].tolist()
    except Exception:
        rank_list = ["Все звания"]
    selected_rank = st.selectbox("Звание", rank_list)

# Год
col4, col5 = st.columns(2)
with col4:
    year_from = st.number_input("Год рождения (от)", min_value=1850, max_value=1940, value=1850, step=1)
with col5:
    year_to = st.number_input("Год рождения (до)", min_value=1850, max_value=1940, value=1940, step=1)

# ── Поиск ─────────────────────────────────────────────────────────
PAGE_SIZE = 20

if "search_page" not in st.session_state:
    st.session_state.search_page = 0

if st.button("🔍 Найти", type="primary") or query_text:
    st.session_state.search_page = 0

    # Построение запроса
    conditions = []
    params = []

    if query_text.strip():
        safe_query = query_text.strip().replace("'", "''")
        conditions.append(f"(fio ILIKE '%{safe_query}%' OR story ILIKE '%{safe_query}%')")

    if selected_region != "Все регионы":
        conditions.append(f"region = '{selected_region}'")

    if selected_rank != "Все звания":
        conditions.append(f"rank = '{selected_rank}'")

    # Год рождения — парсинг из строки birthday
    # В данных birthday может быть строкой; фильтруем по LIKE для года
    if year_from > 1850 or year_to < 1940:
        # Пытаемся извлечь год из birthday
        conditions.append(
            f"TRY_CAST(REGEXP_EXTRACT(birthday, '(\\d{{4}})', 1) AS INTEGER) "
            f"BETWEEN {year_from} AND {year_to}"
        )

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    # Подсчёт
    try:
        count_q = f"SELECT COUNT(*) AS cnt FROM soldiers WHERE {where_clause}"
        total = con.execute(count_q).fetchone()[0]
    except Exception as e:
        st.error(f"Ошибка запроса: {e}")
        st.stop()

    st.markdown(f"**Найдено: {total:,} карточек**".replace(",", " "))

    if total == 0:
        st.warning("Ничего не найдено. Попробуйте изменить параметры поиска.")
        st.stop()

    # Пагинация
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    max_pages = min(total_pages, 50)  # Ограничиваем для UX

    page = st.session_state.search_page
    offset = page * PAGE_SIZE

    try:
        select_cols = "id, fio, region, rank, birthday, death, story, awards_txt, url"
        query = (
            f"SELECT {select_cols} FROM soldiers "
            f"WHERE {where_clause} "
            f"ORDER BY fio "
            f"LIMIT {PAGE_SIZE} OFFSET {offset}"
        )
        results = con.execute(query).fetchdf()
    except Exception as e:
        st.error(f"Ошибка запроса: {e}")
        st.stop()

    # Навигация по страницам
    if total_pages > 1:
        pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
        with pcol1:
            if st.button("← Назад", disabled=page == 0):
                st.session_state.search_page = max(0, page - 1)
                st.rerun()
        with pcol2:
            st.caption(f"Страница {page + 1} из {max_pages}")
        with pcol3:
            if st.button("Вперёд →", disabled=page >= max_pages - 1):
                st.session_state.search_page = page + 1
                st.rerun()

    # ── Карточки результатов ──────────────────────────────────────
    for _, row in results.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                fio = row.get("fio", "—")
                st.markdown(f"### {fio}")

                details = []
                if pd.notna(row.get("rank")) and row["rank"]:
                    details.append(f"**Звание:** {row['rank']}")
                if pd.notna(row.get("birthday")) and row["birthday"]:
                    details.append(f"**Рождение:** {row['birthday']}")
                if pd.notna(row.get("death")) and row["death"]:
                    details.append(f"**Гибель/смерть:** {row['death']}")
                if pd.notna(row.get("region")) and row["region"]:
                    details.append(f"**Регион:** {row['region']}")
                if pd.notna(row.get("awards_txt")) and row["awards_txt"]:
                    details.append(f"**Награды:** {row['awards_txt'][:200]}")

                st.markdown(" · ".join(details) if details else "Нет данных")

            with c2:
                url = row.get("url", "")
                if pd.notna(url) and url:
                    st.link_button("Открыть на moypolk.ru", url, use_container_width=True)

            # Текст (свёрнутый)
            story = row.get("story", "")
            if pd.notna(story) and story:
                with st.expander("📖 Текст карточки"):
                    st.markdown(str(story)[:2000])
                    if len(str(story)) > 2000:
                        st.caption(f"... (показаны первые 2000 из {len(str(story))} символов)")

else:
    st.markdown("Введите запрос и нажмите **Найти** для поиска.")
    st.caption(
        "Поиск поддерживает ФИО (частичное совпадение) и ключевые слова в тексте карточки. "
        "Регистр не важен."
    )
