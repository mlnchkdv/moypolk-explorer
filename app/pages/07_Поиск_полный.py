"""🔎 Поиск по всем карточкам с текстом — подсветка, закладки, метрики."""

import re
import streamlit as st
import pandas as pd
import numpy as np

from config import TOTAL_CARDS, SAMPLE_SIZE, BLUE, ORANGE, RED
from data_loader import get_duckdb_connection, get_full_search_connection

# ── Инициализация состояния сессии ─────────────────────────────────
if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = {}   # {id: {fio, region, rank, url, story_excerpt}}

if "full_search_page" not in st.session_state:
    st.session_state.full_search_page = 0

# ── Вспомогательные функции ────────────────────────────────────────

def highlight(text: str, query: str, max_chars: int = 3000) -> str:
    """Обернуть все вхождения query в <mark> для подсветки."""
    if not query or not text:
        return (text or "")[:max_chars]
    snippet = text[:max_chars]
    escaped = re.escape(query.strip())
    highlighted = re.sub(
        f"({escaped})", r"<mark>\1</mark>",
        snippet, flags=re.IGNORECASE
    )
    suffix = f"…<br><small>(показано {max_chars} из {len(text)} символов)</small>" if len(text) > max_chars else ""
    return highlighted + suffix


def compute_mattr(text: str, window: int = 50) -> float:
    words = text.lower().split()
    if len(words) < window:
        return round(len(set(words)) / max(len(words), 1), 3)
    ttrs = [len(set(words[i:i + window])) / window for i in range(len(words) - window + 1)]
    return round(float(np.mean(ttrs)), 3)


def classify_narrative(story: str) -> str:
    if not story or len(story) < 100:
        return "Формуляр"
    s = story.lower()
    first_person = any(w in s for w in ["я помню", "мой дед", "моя бабушка", "мой отец", "мой прадед"])
    if first_person and len(story) > 500:
        return "Семейная история"
    if len(story) > 1000 and any(w in s for w in ["фронт", "бой", "наступление", "дивизия", "полк"]):
        return "Мемуар"
    return "Смешанный"


def card_metrics(story: str) -> dict:
    words = story.split()
    return {
        "Символов": len(story),
        "Слов": len(words),
        "Уникальных слов": len(set(w.lower() for w in words)),
        "MATTR": compute_mattr(story),
        "Тип нарратива": classify_narrative(story),
    }


# ═══════════════════════════════════════════════════════════════════
st.title("🔎 Расширенный поиск по карточкам")

# ── Выбор источника данных ─────────────────────────────────────────
con_full = get_full_search_connection()
con_sample = get_duckdb_connection()

if con_full is not None:
    con = con_full
    table = "soldiers_full"
    source_label = "полный датасет (~981K карточек с текстом)"
    source_icon = "✅"
elif con_sample is not None:
    con = con_sample
    table = "soldiers"
    source_label = f"сэмпл {SAMPLE_SIZE // 1000}K из {TOTAL_CARDS:,}".replace(",", " ")
    source_icon = "⚠️"
else:
    st.error(
        "Данные не найдены. Запустите:\n"
        "```\npython scripts/prepare_data.py --input polk_11_05_2025_done.csv\n```"
    )
    st.stop()

st.info(f"{source_icon} Источник: **{source_label}**", icon="ℹ️")

# ── Закладки (sidebar) ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⭐ Закладки")
    bm_count = len(st.session_state.bookmarks)
    if bm_count == 0:
        st.caption("Нет сохранённых карточек.")
    else:
        st.caption(f"Сохранено: {bm_count}")
        for bm_id, bm in list(st.session_state.bookmarks.items()):
            with st.expander(f"📌 {bm.get('fio', '—')[:40]}"):
                st.markdown(f"**Регион:** {bm.get('region', '—')}")
                st.markdown(f"**Звание:** {bm.get('rank', '—')}")
                excerpt = bm.get("story_excerpt", "")
                if excerpt:
                    st.caption(excerpt[:200])
                if bm.get("url"):
                    st.link_button("Открыть ↗", bm["url"])
                if st.button("🗑 Удалить", key=f"del_{bm_id}"):
                    del st.session_state.bookmarks[bm_id]
                    st.rerun()

        if st.button("Очистить все закладки", type="secondary"):
            st.session_state.bookmarks.clear()
            st.rerun()

# ── Фильтры ──────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    query_text = st.text_input(
        "🔍 Ключевое слово / ФИО",
        placeholder="Например: Сталинград, рядовой Иванов, госпиталь…",
        key="full_search_query",
    )

with col2:
    try:
        regions = con.execute(
            f"SELECT DISTINCT region FROM {table} WHERE region IS NOT NULL ORDER BY region"
        ).fetchdf()
        region_list = ["Все регионы"] + regions["region"].tolist()
    except Exception:
        region_list = ["Все регионы"]
    selected_region = st.selectbox("Регион", region_list, key="full_region")

with col3:
    try:
        ranks = con.execute(
            f"SELECT rank, COUNT(*) AS cnt FROM {table} WHERE rank IS NOT NULL "
            f"GROUP BY rank ORDER BY cnt DESC LIMIT 30"
        ).fetchdf()
        rank_list = ["Все звания"] + ranks["rank"].tolist()
    except Exception:
        rank_list = ["Все звания"]
    selected_rank = st.selectbox("Звание", rank_list, key="full_rank")

col4, col5, col6 = st.columns([1, 1, 1])
with col4:
    year_from = st.number_input("Год рождения от", min_value=1850, max_value=1940, value=1850, step=1)
with col5:
    year_to = st.number_input("Год рождения до", min_value=1850, max_value=1940, value=1940, step=1)
with col6:
    show_metrics = st.checkbox("📊 Метрики карточки", value=False,
                                help="Вычислить MATTR, тип нарратива и статистику для каждой найденной карточки")

# ── Поиск ─────────────────────────────────────────────────────────
PAGE_SIZE = 15

search_clicked = st.button("🔍 Найти", type="primary")
if search_clicked:
    st.session_state.full_search_page = 0

if search_clicked or query_text:
    conditions = []

    if query_text.strip():
        safe_q = query_text.strip().replace("'", "''")
        conditions.append(f"(fio ILIKE '%{safe_q}%' OR story ILIKE '%{safe_q}%')")

    if selected_region != "Все регионы":
        safe_r = selected_region.replace("'", "''")
        conditions.append(f"region = '{safe_r}'")

    if selected_rank != "Все звания":
        safe_rk = selected_rank.replace("'", "''")
        conditions.append(f"rank = '{safe_rk}'")

    if year_from > 1850 or year_to < 1940:
        conditions.append(
            f"TRY_CAST(REGEXP_EXTRACT(birthday, '(\\d{{4}})', 1) AS INTEGER) "
            f"BETWEEN {year_from} AND {year_to}"
        )

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    try:
        total = con.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
        ).fetchone()[0]
    except Exception as e:
        st.error(f"Ошибка запроса: {e}")
        st.stop()

    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"**Найдено: {total:,} карточек**".replace(",", " "))
    with c2:
        if total > 0 and query_text:
            st.caption(f"Подсветка: «{query_text.strip()[:30]}»")

    if total == 0:
        st.warning("Ничего не найдено. Попробуйте изменить запрос.")
        st.stop()

    # ── Пагинация ──────────────────────────────────────────────────
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    max_pages = min(total_pages, 100)
    page = st.session_state.full_search_page
    offset = page * PAGE_SIZE

    if total_pages > 1:
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("← Назад", disabled=page == 0, key="prev_full"):
                st.session_state.full_search_page = max(0, page - 1)
                st.rerun()
        with pc2:
            st.caption(f"Страница {page + 1} из {max_pages}" +
                       (f" (всего {total_pages}, показано первые {max_pages})" if total_pages > max_pages else ""))
        with pc3:
            if st.button("Вперёд →", disabled=page >= max_pages - 1, key="next_full"):
                st.session_state.full_search_page = page + 1
                st.rerun()

    # ── Результаты ─────────────────────────────────────────────────
    try:
        select_cols = "id, fio, region, rank, birthday, death, story, awards_txt, url"
        results = con.execute(
            f"SELECT {select_cols} FROM {table} WHERE {where_clause} "
            f"ORDER BY fio LIMIT {PAGE_SIZE} OFFSET {offset}"
        ).fetchdf()
    except Exception as e:
        st.error(f"Ошибка выборки: {e}")
        st.stop()

    hl_query = query_text.strip() if query_text else ""

    for _, row in results.iterrows():
        with st.container(border=True):
            hdr_col, bm_col = st.columns([5, 1])

            with hdr_col:
                fio = row.get("fio") or "—"
                st.markdown(f"### {fio}")
                meta = []
                if pd.notna(row.get("rank")) and row["rank"]:
                    meta.append(f"**Звание:** {row['rank']}")
                if pd.notna(row.get("birthday")) and row["birthday"]:
                    meta.append(f"**Рождение:** {row['birthday']}")
                if pd.notna(row.get("death")) and row["death"]:
                    meta.append(f"**Гибель:** {row['death']}")
                if pd.notna(row.get("region")) and row["region"]:
                    meta.append(f"**Регион:** {row['region']}")
                if pd.notna(row.get("awards_txt")) and row["awards_txt"]:
                    meta.append(f"**Награды:** {str(row['awards_txt'])[:150]}")
                st.markdown(" · ".join(meta) if meta else "Нет метаданных")

            with bm_col:
                card_id = str(row.get("id", id(row)))
                is_bookmarked = card_id in st.session_state.bookmarks
                bm_label = "⭐ В закладках" if is_bookmarked else "☆ Закладка"
                if st.button(bm_label, key=f"bm_{card_id}_{page}"):
                    if is_bookmarked:
                        del st.session_state.bookmarks[card_id]
                    else:
                        story_val = row.get("story", "") or ""
                        st.session_state.bookmarks[card_id] = {
                            "fio": fio,
                            "region": row.get("region", ""),
                            "rank": row.get("rank", ""),
                            "url": row.get("url", ""),
                            "story_excerpt": str(story_val)[:300],
                        }
                    st.rerun()

                url = row.get("url", "")
                if pd.notna(url) and url:
                    st.link_button("Открыть ↗", url, use_container_width=True)

            # ── Текст с подсветкой ─────────────────────────────────
            story = str(row.get("story") or "")
            if story:
                with st.expander("📖 Текст карточки"):
                    if hl_query:
                        hl_html = highlight(story, hl_query, max_chars=3000)
                        st.markdown(
                            f"""<style>mark{{background:#FFF176;border-radius:3px;padding:1px 2px}}</style>
                            <div style="line-height:1.6;font-size:0.95rem">{hl_html}</div>""",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(story[:3000])
                        if len(story) > 3000:
                            st.caption(f"…(показано 3000 из {len(story)} символов)")

                # ── Метрики карточки (опционально) ──────────────────
                if show_metrics:
                    with st.expander("📊 Метрики этой карточки"):
                        m = card_metrics(story)
                        mc = st.columns(len(m))
                        for col, (k, v) in zip(mc, m.items()):
                            col.metric(k, v)
else:
    st.markdown(
        "Введите запрос и нажмите **Найти**.\n\n"
        "**Возможности:**\n"
        "- Поиск по ФИО и полному тексту карточки\n"
        "- Подсветка найденного выражения прямо в тексте\n"
        "- Фильтр по региону, званию и году рождения\n"
        "- ⭐ Сохраняйте интересные карточки в закладки (на время сессии)\n"
        "- 📊 Включите «Метрики карточки» для расчёта MATTR, типа нарратива и статистики слов\n\n"
        "_Закладки доступны в боковой панели._"
    )
