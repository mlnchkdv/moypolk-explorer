"""Конфигурация приложения: цвета, стили Plotly, константы."""

# ── Цветовая палитра ──────────────────────────────────────────────
BLUE = "#1565C0"
RED = "#E53935"
LIGHT_BLUE = "#42A5F5"
ORANGE = "#FF8A65"
GREEN = "#66BB6A"
GREY = "#90A4AE"
DARK = "#212121"
WHITE = "#FFFFFF"
BG = "#FAFAFA"

PALETTE = [BLUE, RED, LIGHT_BLUE, ORANGE, GREEN, "#AB47BC", "#FFA726", "#26A69A"]
PALETTE_LIGHT = ["#BBDEFB", "#FFCDD2", "#B3E5FC", "#FFE0B2", "#C8E6C9"]

# ── Нарративы ─────────────────────────────────────────────────────
NARRATIVE_COLORS = {
    "Формуляр": BLUE,
    "Мемуар": RED,
    "Семейная история": ORANGE,
    "Смешанный": GREEN,
}

NARRATIVE_TYPES = list(NARRATIVE_COLORS.keys())

# ── Месяцы на русском ─────────────────────────────────────────────
MONTHS_RU = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
]
MONTHS_RU_FULL = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

# ── Plotly layout по умолчанию ────────────────────────────────────
PLOTLY_LAYOUT = dict(
    font=dict(family="Roboto, Arial, sans-serif", size=13, color=DARK),
    paper_bgcolor=BG,
    plot_bgcolor=WHITE,
    margin=dict(l=60, r=30, t=50, b=50),
    hoverlabel=dict(
        bgcolor=WHITE,
        font_size=12,
        font_family="Roboto, Arial, sans-serif",
    ),
    xaxis=dict(gridcolor="#E0E0E0", zerolinecolor="#BDBDBD"),
    yaxis=dict(gridcolor="#E0E0E0", zerolinecolor="#BDBDBD"),
    legend=dict(
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#E0E0E0",
        borderwidth=1,
    ),
    colorway=PALETTE,
)

# ── Ключевые числа (fallback) ────────────────────────────────────
TOTAL_CARDS = 981_467
PCT_WITH_STORY = 65.0
PCT_MAY = 57.4
HALFLIFE_DAYS = 7
MATTR_TREND = -0.003
NUM_LDA_TOPICS = 7
PCT_LOCAL_MEMORY = 53.9
DMI_GINI = 0.125
STORY_VS_AWARDS_R = -0.56
AGE_GAP_RANGE = "7 → 1.5 лет"
SAMPLE_SIZE = 50_000

# ── Пути к данным ─────────────────────────────────────────────────
import pathlib

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
AGG_DIR = DATA_DIR / "aggregated"
SAMPLE_DIR = DATA_DIR / "sample"
SAMPLE_FILE = SAMPLE_DIR / "soldiers_sample_50k.parquet"
FULL_SEARCH_DIR  = DATA_DIR / "full"
FULL_SEARCH_FILE = FULL_SEARCH_DIR / "soldiers_fts.parquet"  # single-file fallback
