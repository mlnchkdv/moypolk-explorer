"""🔎 Поиск по карточкам — подсветка ключевых слов, закладки, метрики, экспорт."""

import re
import datetime
import streamlit as st
import pandas as pd
import numpy as np

from config import TOTAL_CARDS, SAMPLE_SIZE, BLUE, ORANGE
from data_loader import get_duckdb_connection, get_full_search_connection

# ── Глобальный стиль подсветки (инжектируем один раз) ─────────────
st.html("""
<style>
mark {
    background: #FFF176;
    border-radius: 3px;
    padding: 1px 3px;
    font-weight: 600;
}
.card-text {
    line-height: 1.75;
    font-size: 0.95rem;
    color: #212121;
    white-space: pre-wrap;
    word-break: break-word;
}
.meta-chip {
    display: inline-block;
    background: #E3F2FD;
    color: #1565C0;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.82rem;
    margin: 2px 3px 2px 0;
}
</style>
""")

# ── Инициализация состояния сессии ─────────────────────────────────
if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = {}
if "full_search_page" not in st.session_state:
    st.session_state.full_search_page = 0


# ── Вспомогательные функции ────────────────────────────────────────

def highlight(text: str, query: str, max_chars: int = 4000) -> str:
    """Обернуть все вхождения query в <mark>. Возвращает безопасный HTML."""
    snippet = text[:max_chars]
    suffix = f"<br><small style='color:#757575'>…показано {max_chars} из {len(text)} символов</small>" if len(text) > max_chars else ""
    if not query or not query.strip():
        return snippet.replace("\n", "<br>") + suffix
    escaped = re.escape(query.strip())
    highlighted = re.sub(f"({escaped})", r"<mark>\1</mark>", snippet, flags=re.IGNORECASE)
    return highlighted.replace("\n", "<br>") + suffix


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
        "Символов": f"{len(story):,}".replace(",", "\u202f"),
        "Слов": f"{len(words):,}".replace(",", "\u202f"),
        "Уникальных": f"{len(set(w.lower() for w in words)):,}".replace(",", "\u202f"),
        "MATTR": compute_mattr(story),
        "Тип": classify_narrative(story),
    }


def generate_export_html(bookmarks: dict, search_query: str = "") -> str:
    """Генерирует HTML-файл с закладками, готовый для печати/сохранения как PDF."""
    today = datetime.date.today().strftime("%d.%m.%Y")
    cards_html = ""
    for bm in bookmarks.values():
        story_excerpt = bm.get("story_excerpt", "")
        if search_query and story_excerpt:
            story_excerpt = re.sub(
                f"({re.escape(search_query.strip())})", r"<mark>\1</mark>",
                story_excerpt, flags=re.IGNORECASE,
            )
        url_html = (
            f'<p><a href="{bm["url"]}" target="_blank">Открыть карточку на сайте →</a></p>'
            if bm.get("url") else ""
        )
        cards_html += f"""
<div class="card">
  <h2>{bm.get("fio", "—")}</h2>
  <p class="meta">
    <span>🎖️ {bm.get("rank") or "звание неизвестно"}</span>
    &nbsp;·&nbsp;
    <span>📍 {bm.get("region") or "регион неизвестен"}</span>
  </p>
  <p class="excerpt">{story_excerpt or "<em>текст недоступен</em>"}</p>
  {url_html}
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Закладки — Бессмертный полк ({today})</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 960px; margin: 0 auto; padding: 24px; color: #212121; }}
  h1   {{ color: #1565C0; border-bottom: 2px solid #1565C0; padding-bottom: 8px; }}
  .card {{ border: 1px solid #ccc; border-radius: 8px; padding: 20px 24px; margin-bottom: 24px; }}
  h2   {{ margin: 0 0 6px 0; font-size: 1.2rem; }}
  .meta {{ color: #555; font-size: 0.9rem; margin: 0 0 12px 0; }}
  .excerpt {{ line-height: 1.75; color: #333; white-space: pre-wrap; }}
  mark {{ background: #FFF176; border-radius: 2px; padding: 0 2px; font-weight: 600; }}
  a    {{ color: #1565C0; }}
  @media print {{ .card {{ page-break-inside: avoid; }} }}
</style>
</head>
<body>
<h1>🎖️ Закладки — Бессмертный полк</h1>
<p>Экспортировано: <strong>{today}</strong> &nbsp;·&nbsp; Карточек: <strong>{len(bookmarks)}</strong>
{f"&nbsp;·&nbsp; Поиск: <strong>«{search_query}»</strong>" if search_query else ""}
</p>
{cards_html}
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════
st.title("🔎 Поиск по карточкам ветеранов")

# ── Выбор источника данных ─────────────────────────────────────────
con_full = get_full_search_connection()
con_sample = get_duckdb_connection()

if con_full is not None:
    con = con_full
    table = "soldiers_full"
    st.success(f"Источник: **полный датасет** (~{TOTAL_CARDS:,} карточек)".replace(",", "\u202f"), icon="✅")
elif con_sample is not None:
    con = con_sample
    table = "soldiers"
    st.warning(
        f"Источник: **сэмпл {SAMPLE_SIZE // 1000}K** из {TOTAL_CARDS:,} карточек. "
        "Для полного поиска сгенерируйте FTS-индекс:\n"
        "```\npython scripts/prepare_data.py --input polk_11_05_2025_done.csv\n```".replace(",", "\u202f"),
        icon="⚠️",
    )
else:
    st.error(
        "Данные не найдены. Запустите:\n"
        "```\npython scripts/prepare_data.py --input polk_11_05_2025_done.csv\n```"
    )
    st.stop()

# ── Закладки (sidebar) ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⭐ Закладки")
    bm_count = len(st.session_state.bookmarks)

    if bm_count == 0:
        st.caption("Нет сохранённых карточек.\nДобавляйте через кнопку ☆ на карточке.")
    else:
        st.caption(f"Сохранено: **{bm_count}** карточек")

        # Экспорт закладок
        hl_q = st.session_state.get("full_search_query", "")
        html_bytes = generate_export_html(st.session_state.bookmarks, hl_q).encode("utf-8")
        st.download_button(
            label="📥 Экспорт закладок → HTML (→ PDF)",
            data=html_bytes,
            file_name=f"polk_bookmarks_{datetime.date.today()}.html",
            mime="text/html",
            use_container_width=True,
            help="Откройте скачанный файл в браузере и используйте Печать → Сохранить как PDF",
        )
        st.markdown("---")

        for bm_id, bm in list(st.session_state.bookmarks.items()):
            with st.expander(f"📌 {(bm.get('fio') or '—')[:35]}"):
                if bm.get("rank"):
                    st.caption(f"🎖️ {bm['rank']}")
                if bm.get("region"):
                    st.caption(f"📍 {bm['region']}")
                excerpt = bm.get("story_excerpt", "")
                if excerpt:
                    st.markdown(f"_{excerpt[:180]}…_" if len(excerpt) > 180 else f"_{excerpt}_")
                if bm.get("url"):
                    st.link_button("Открыть ↗", bm["url"])
                if st.button("🗑 Удалить", key=f"del_{bm_id}", use_container_width=True):
                    del st.session_state.bookmarks[bm_id]
                    st.rerun()

        st.markdown("---")
        if st.button("Очистить все закладки", type="secondary", use_container_width=True):
            st.session_state.bookmarks.clear()
            st.rerun()

# ── Панель фильтров ────────────────────────────────────────────────
with st.container(border=True):
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        query_text = st.text_input(
            "🔍 Ключевое слово / ФИО",
            placeholder="Например: Сталинград, рядовой Иванов, госпиталь, медаль…",
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

    col4, col5, col6 = st.columns([1, 1, 2])
    with col4:
        year_from = st.number_input("Год рождения от", min_value=1850, max_value=1940, value=1850, step=1)
    with col5:
        year_to = st.number_input("до", min_value=1850, max_value=1940, value=1940, step=1)
    with col6:
        show_metrics = st.checkbox(
            "📊 Показывать метрики карточки",
            value=False,
            help="MATTR, тип нарратива, статистика слов — вычисляется для каждой карточки",
        )

    search_clicked = st.button("🔍 Найти", type="primary", use_container_width=False)

if search_clicked:
    st.session_state.full_search_page = 0

# ── Поисковый запрос ───────────────────────────────────────────────
PAGE_SIZE = 12

if search_clicked or query_text or selected_region != "Все регионы" or selected_rank != "Все звания":
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

    where_clause = " AND ".join(conditions) if conditions else "story IS NOT NULL"

    try:
        total = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_clause}").fetchone()[0]
    except Exception as e:
        st.error(f"Ошибка запроса: {e}")
        st.stop()

    c1, c2 = st.columns([3, 1])
    with c1:
        num_str = f"{total:,}".replace(",", "\u202f")
        st.markdown(f"**Найдено: {num_str} карточек**")
    with c2:
        if total > 0 and query_text:
            st.caption(f"Подсвечивается: «{query_text.strip()[:30]}»")

    if total == 0:
        st.warning("Ничего не найдено. Попробуйте изменить запрос.")
        st.stop()

    # ── Пагинация ──────────────────────────────────────────────────
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    max_pages = min(total_pages, 100)
    page = min(st.session_state.full_search_page, max_pages - 1)
    offset = page * PAGE_SIZE

    def _render_pagination(suffix: str):
        """Отрисовка блока пагинации (вызывается сверху и снизу)."""
        if total_pages <= 1:
            return
        pc1, pc2, pc3 = st.columns([1, 3, 1])
        with pc1:
            if st.button("← Назад", disabled=page == 0, key=f"prev_{suffix}"):
                st.session_state.full_search_page = max(0, page - 1)
                st.rerun()
        with pc2:
            tail = f" (показано первые {max_pages} из {total_pages})" if total_pages > max_pages else ""
            st.caption(f"Страница {page + 1} из {max_pages}{tail}")
        with pc3:
            if st.button("Вперёд →", disabled=page >= max_pages - 1, key=f"next_{suffix}"):
                st.session_state.full_search_page = page + 1
                st.rerun()

    _render_pagination("top")

    # ── Результаты ─────────────────────────────────────────────────
    select_cols = "id, fio, region, rank, birthday, death, story, awards_txt, url"
    try:
        results = con.execute(
            f"SELECT {select_cols} FROM {table} WHERE {where_clause} "
            f"ORDER BY fio LIMIT {PAGE_SIZE} OFFSET {offset}"
        ).fetchdf()
    except Exception as e:
        st.error(f"Ошибка выборки: {e}")
        st.stop()

    hl_query = query_text.strip() if query_text else ""

    for _, row in results.iterrows():
        card_id = str(row.get("id", id(row)))
        is_bookmarked = card_id in st.session_state.bookmarks

        with st.container(border=True):
            # ── Заголовок карточки ──────────────────────────────────
            hdr_col, act_col = st.columns([5, 1])

            with hdr_col:
                fio = row.get("fio") or "ФИО не указано"
                # Если поиск был по ФИО — подсвечиваем его в заголовке
                if hl_query and re.search(re.escape(hl_query), fio, re.IGNORECASE):
                    hl_fio = re.sub(
                        f"({re.escape(hl_query)})", r"<mark>\1</mark>",
                        fio, flags=re.IGNORECASE,
                    )
                    st.html(f"<h3 style='margin:0 0 4px 0'>{hl_fio}</h3>")
                else:
                    st.markdown(f"### {fio}")

            with act_col:
                bm_label = "⭐" if is_bookmarked else "☆"
                bm_help = "Удалить из закладок" if is_bookmarked else "Добавить в закладки"
                if st.button(bm_label, key=f"bm_{card_id}_{page}", help=bm_help):
                    if is_bookmarked:
                        del st.session_state.bookmarks[card_id]
                    else:
                        story_val = str(row.get("story") or "")
                        st.session_state.bookmarks[card_id] = {
                            "fio": fio,
                            "region": row.get("region") or "",
                            "rank": row.get("rank") or "",
                            "url": row.get("url") or "",
                            "story_excerpt": story_val[:400],
                        }
                    st.rerun()

                url = row.get("url") or ""
                if pd.notna(url) and url:
                    st.link_button("↗", url, help="Открыть карточку на сайте")

            # ── Метаданные (чипы) ───────────────────────────────────
            chips = []
            if pd.notna(row.get("rank")) and row["rank"]:
                chips.append(f"🎖️ {row['rank']}")
            bd = row.get("birthday") or ""
            dt = row.get("death") or ""
            if bd or dt:
                chips.append(f"📅 {bd or '?'} — {dt or '?'}")
            if pd.notna(row.get("region")) and row["region"]:
                chips.append(f"📍 {row['region']}")
            if chips:
                chips_html = "".join(
                    f'<span class="meta-chip">{c}</span>' for c in chips
                )
                st.html(f'<div style="margin-bottom:4px">{chips_html}</div>')

            # Награды (если есть)
            awards = str(row.get("awards_txt") or "")
            if awards and awards != "nan":
                st.caption(f"🏅 {awards[:200]}")

            # ── Текст карточки с подсветкой ─────────────────────────
            story = str(row.get("story") or "")
            if story and story != "nan":
                with st.expander("📖 Текст карточки", expanded=False):
                    hl_html = highlight(story, hl_query, max_chars=4000)
                    st.html(f'<div class="card-text">{hl_html}</div>')

                # ── Метрики (опционально) ────────────────────────────
                if show_metrics:
                    m = card_metrics(story)
                    metric_cols = st.columns(len(m))
                    for mc, (k, v) in zip(metric_cols, m.items()):
                        mc.metric(k, v)

    # ── Пагинация внизу ─────────────────────────────────────────
    _render_pagination("bottom")
else:
    st.markdown(
        "### Как использовать\n\n"
        "1. Введите **ключевое слово** или **ФИО** в строку поиска\n"
        "2. При необходимости уточните **регион**, **звание** или **год рождения**\n"
        "3. Нажмите **Найти**\n\n"
        "**Возможности:**\n"
        "- 🔆 Подсветка найденного выражения прямо в тексте карточки\n"
        "- ⭐ Сохраняйте интересные карточки в **закладки** (боковая панель)\n"
        "- 📥 Экспортируйте закладки в **HTML** и сохраните как PDF через браузер\n"
        "- 📊 Включите **метрики карточки** для расчёта MATTR, типа нарратива и статистики\n\n"
        "_Закладки хранятся в течение сессии и доступны в боковой панели._"
    )
