# Бессмертный полк — исследовательская витрина

Интерактивный Streamlit-дашборд для исследователей, историков и специалистов в области digital humanities. Предоставляет доступ к визуализации данных «Бессмертный полк» (~981 тыс. карточек ветеранов Великой Отечественной войны).

## Структура проекта

```
moypolk-explorer/
├── .streamlit/config.toml      # тема и настройки Streamlit
├── app/
│   ├── main.py                 # точка входа (streamlit run app/main.py)
│   ├── config.py               # цвета, PLOTLY_LAYOUT, константы
│   ├── data_loader.py          # @st.cache_data + @st.cache_resource
│   └── pages/
│       ├── 00_Обзор.py         # метрики, находки, навигация
│       ├── 01_Динамика.py      # временные ряды, сезонность, полураспад
│       ├── 02_Тексты.py        # нарративы, тональность, MATTR, LDA, NER
│       ├── 03_География.py     # матрица миграции, межрегиональные связи
│       ├── 04_Демография.py    # возраст × звание, конвергенция
│       ├── 05_DMI.py           # индекс цифровой памяти
│       └── 06_Поиск.py         # полнотекстовый поиск по сэмплу 50K
├── assets/style.css            # пользовательские стили
├── data/
│   ├── aggregated/             # предагрегаты (~1 MB, коммитятся)
│   └── sample/                 # сэмпл 50K (~80 MB, коммитится)
├── scripts/prepare_data.py     # генерация агрегатов из исходного CSV
└── requirements.txt
```

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Подготовка данных (один раз, локально)

Поместите исходный CSV (`polk_11_05_2025_done.csv`, ~1.3 GB) в корень проекта и запустите:

```bash
python scripts/prepare_data.py --input polk_11_05_2025_done.csv
```

Скрипт создаст:
- `data/aggregated/*.parquet` — 14 предагрегатов (~1 MB суммарно)
- `data/sample/soldiers_sample_50k.parquet` — стратифицированный сэмпл (~80 MB)

### 3. Запуск приложения

```bash
streamlit run app/main.py
```

## Деплой на Streamlit Community Cloud

1. Закоммитьте `data/` в репозиторий (исходный CSV в `.gitignore`).
2. На [share.streamlit.io](https://share.streamlit.io) укажите главный файл: `app/main.py`.

## Данные

Исходный файл `polk_11_05_2025_done.csv` (~1.3 GB, ~981 000 строк) не включён в репозиторий. В GitHub хранятся только предагрегаты (`data/`).

**Схема CSV:** `id`, `url`, `fio`, `title`, `story`, `region`, `locality`, `birthplace`, `rank`, `speciality`, `service_years`, `birthday`, `death`, `draft_place`, `draft_date`, `subdivision`, `battles`, `hospitals`, `awards_cnt`, `awards_txt`, `photos_cnt`, `author_txt`, `author_href`, `added_region`, `pub_date`

## Ключевые показатели

| Показатель | Значение |
|---|---|
| Карточек | 981 467 |
| С текстом | 65% |
| Публикаций в мае | 57.4% |
| Полураспад активности | 7 дней |
| LDA-тем | 7 |
| Локальная память | 53.9% |
| DMI Gini | 0.125 |
| Story vs Awards r | −0.56 |
| Возрастной разрыв | 7 → 1.5 лет |

## Как цитировать

```
Бессмертный полк: исследовательская витрина [Электронный ресурс].
// Данные «Мой полк» (moypolk.ru), 981 467 карточек.
URL: https://moypolk-explorer.streamlit.app (дата обращения: ДД.ММ.ГГГГ).
```

---

Данные собраны из открытых источников платформы moypolk.ru. Дашборд создан в исследовательских целях.
