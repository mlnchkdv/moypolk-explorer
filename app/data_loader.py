"""Загрузчик данных с кэшированием Streamlit."""

import streamlit as st
import pandas as pd
import pathlib
from config import AGG_DIR, SAMPLE_FILE, FULL_SEARCH_DIR, FULL_SEARCH_FILE


def _load_parquet(name: str) -> pd.DataFrame:
    """Загрузить parquet-файл из директории агрегатов."""
    path =  AGG_DIR / name
    if not path.exists():
        st.error(f"Файл не найден: {path}")
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(ttl=3600)
def load_monthly_counts() -> pd.DataFrame:
    return _load_parquet("monthly_counts.parquet")


@st.cache_data(ttl=3600)
def load_yearly_stats() -> pd.DataFrame:
    return _load_parquet("yearly_stats.parquet")


@st.cache_data(ttl=3600)
def load_region_stats() -> pd.DataFrame:
    return _load_parquet("region_stats.parquet")


@st.cache_data(ttl=3600)
def load_rank_age_distribution() -> pd.DataFrame:
    return _load_parquet("rank_age_distribution.parquet")


@st.cache_data(ttl=3600)
def load_narrative_types_yearly() -> pd.DataFrame:
    return _load_parquet("narrative_types_yearly.parquet")


@st.cache_data(ttl=3600)
def load_sentiment_yearly() -> pd.DataFrame:
    return _load_parquet("sentiment_yearly.parquet")


@st.cache_data(ttl=3600)
def load_mattr_yearly() -> pd.DataFrame:
    return _load_parquet("mattr_yearly.parquet")


@st.cache_data(ttl=3600)
def load_lda_topics() -> pd.DataFrame:
    return _load_parquet("lda_topics.parquet")


@st.cache_data(ttl=3600)
def load_lda_evolution() -> pd.DataFrame:
    return _load_parquet("lda_evolution.parquet")


@st.cache_data(ttl=3600)
def load_migration_matrix() -> pd.DataFrame:
    return _load_parquet("migration_matrix.parquet")


@st.cache_data(ttl=3600)
def load_dmi_by_region() -> pd.DataFrame:
    return _load_parquet("dmi_by_region.parquet")


@st.cache_data(ttl=3600)
def load_ner_top_entities() -> pd.DataFrame:
    return _load_parquet("ner_top_entities.parquet")


@st.cache_data(ttl=3600)
def load_halflife_yearly() -> pd.DataFrame:
    return _load_parquet("halflife_yearly.parquet")


@st.cache_data(ttl=3600)
def load_network_edges() -> pd.DataFrame:
    return _load_parquet("network_edges.parquet")


@st.cache_resource
def get_duckdb_connection():
    """DuckDB-соединение для поиска по сэмплу 50K."""
    import duckdb

    if not SAMPLE_FILE.exists():
        return None
    con = duckdb.connect(":memory:")
    con.execute(
        f"CREATE TABLE soldiers AS SELECT * FROM read_parquet('{SAMPLE_FILE}')"
    )
    return con


@st.cache_resource
def get_full_search_connection():
    """DuckDB-соединение для поиска по полному FTS-датасету.

    Поддерживает два формата хранения:
      1. Чанки: data/full/soldiers_fts_part*.parquet  (< 100 MB каждый, совместимо с GitHub)
      2. Одиночный файл: data/full/soldiers_fts.parquet  (legacy / локальный)

    Возвращает None, если данные не найдены (откат на сэмпл 50K).
    """
    import duckdb

    chunks = sorted(FULL_SEARCH_DIR.glob("soldiers_fts_part*.parquet"))
    if chunks:
        glob_str = str(FULL_SEARCH_DIR / "soldiers_fts_part*.parquet")
        con = duckdb.connect(":memory:")
        con.execute(f"CREATE TABLE soldiers_full AS SELECT * FROM read_parquet('{glob_str}')")
        return con

    if FULL_SEARCH_FILE.exists():
        con = duckdb.connect(":memory:")
        con.execute(
            f"CREATE TABLE soldiers_full AS SELECT * FROM read_parquet('{FULL_SEARCH_FILE}')"
        )
        return con

    return None
