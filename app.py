from collections import Counter
from itertools import combinations
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Анализатор Лотереи 6/37", page_icon="🎰", layout="wide"
)

DB_NAME = "lotto_history.db"


# --- Инициализация локальной базы данных SQLite ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            n1 INTEGER, n2 INTEGER, n3 INTEGER, n4 INTEGER, n5 INTEGER, n6 INTEGER,
            strong_number INTEGER
        )
    """)
    conn.commit()
    conn.close()


init_db()


# --- Функции работы с БД ---
def add_draw(numbers, strong):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    sorted_nums = sorted(numbers)
    cursor.execute(
        """
        INSERT INTO draws (n1, n2, n3, n4, n5, n6, strong_number)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (*sorted_nums, strong),
    )
    conn.commit()
    conn.close()


def load_draws():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(
        "SELECT * FROM draws ORDER BY draw_date DESC, id DESC", conn
    )
    conn.close()
    return df


def delete_draw(draw_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM draws WHERE id = ?", (draw_id,))
    conn.commit()
    conn.close()


# --- Загрузка данных ---
df_draws = load_draws()

st.title("🎰 Анализатор лотерейных тиражей (6/37 + Сильное число)")

# --- Боковая панель: Ввод тиража ---
with st.sidebar:
    st.header("➕ Добавить новый тираж")

    with st.form("add_draw_form", clear_on_submit=True):
        st.subheader("6 основных чисел (1–37):")
        cols = st.columns(3)
        n1 = cols[0].number_input("№1", 1, 37, 1)
        n2 = cols[1].number_input("№2", 1, 37, 2)
        n3 = cols[2].number_input("№3", 1, 37, 3)
        n4 = cols[0].number_input("№4", 1, 37, 4)
        n5 = cols[1].number_input("№5", 1, 37, 5)
        n6 = cols[2].number_input("№6", 1, 37, 6)

        st.subheader("Сильное число (1–7):")
        strong = st.number_input("Сильное число", 1, 7, 1)

        submit = st.form_submit_button("Сохранить тираж")

    if submit:
        nums = [n1, n2, n3, n4, n5, n6]
        if len(set(nums)) < 6:
            st.error("❌ Основные числа не должны повторяться!")
        else:
            add_draw(nums, strong)
            st.success("✅ Тираж успешно сохранен!")
            st.rerun()

    st.markdown("---")
    st.metric("Всего тиражей в базе", len(df_draws))

# --- Главный экран ---
if df_draws.empty:
    st.info("👋 База данных пуста. Введите первый тираж в левой панели!")
else:
    tab_stat, tab_patterns, tab_history = st.tabs(
        [
            "📊 Частотный анализ (Последние 50)",
            "🧩 Повторяющиеся паттерны",
            "📜 История и управление",
        ]
    )

    # ==================== ВКЛАДКА 1: ЧАСТОТНЫЙ АНАЛИЗ ====================
    with tab_stat:
        st.header("📊 Анализ последних 50 тиражей")

        # Берем последние 50 тиражей
        df_last50 = df_draws.head(50)
        total_games = len(df_last50)

        st.caption(f"Анализируется тиражей: **{total_games}**")

        # Извлекаем все основные числа
        main_cols = ["n1", "n2", "n3", "n4", "n5", "n6"]
        all_main_numbers = df_last50[main_cols].values.flatten()
        main_counts = Counter(all_main_numbers)

        # Полная частота всех чисел от 1 до 37
        full_main_freq = {num: main_counts.get(num, 0) for num in range(1, 38)}
        sorted_main = sorted(
            full_main_freq.items(), key=lambda x: x[1], reverse=True
        )

        top10_frequent = sorted_main[:10]
        top10_rare = sorted(full_main_freq.items(), key=lambda x: x[1])[:10]

        col_top, col_rare = st.columns(2)

        with col_top:
            st.subheader("🔥 Топ-10 частых чисел")
            df_top = pd.DataFrame(
                top10_frequent, columns=["Число", "Количество выпадений"]
            )
            df_top["% от игр"] = (
                (df_top["Количество выпадений"] / total_games * 100)
                .round(1)
                .astype(str)
                + "%"
            )
            st.dataframe(df_top, use_container_width=True, hide_index=True)

        with col_rare:
            st.subheader("❄️ Топ-10 редких чисел")
            df_rare = pd.DataFrame(
                top10_rare, columns=["Число", "Количество выпадений"]
            )
            df_rare["% от игр"] = (
                (df_rare["Количество выпадений"] / total_games * 100)
                .round(1)
                .astype(str)
                + "%"
            )
            st.dataframe(df_rare, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("⭐ Статистика Сильного числа (1–7)")

        strong_counts = Counter(df_last50["strong_number"])
        full_strong_freq = {
            num: strong_counts.get(num, 0) for num in range(1, 8)
        }
        sorted_strong = sorted(
            full_strong_freq.items(), key=lambda x: x[1], reverse=True
        )

        most_strong = sorted_strong[0]
        least_strong = sorted_strong[-1]

        c_s1, c_s2 = st.columns(2)
        c_s1.metric(
            "Самое частое сильное число",
            f"№ {most_strong[0]}",
            f"Выпало {most_strong[1]} раз(а)",
        )
        c_s2.metric(
            "Самое редкое сильное число",
            f"№ {least_strong[0]}",
            f"Выпало {least_strong[1]} раз(а)",
        )

        # Полная раскладка по сильным числам
        df_strong_all = pd.DataFrame(
            sorted_strong, columns=["Сильное число", "Выпадений"]
        )
        st.write("Все сильные числа за 50 игр:")
        st.dataframe(
            df_strong_all.transpose(),
            use_container_width=True,
        )

    # ==================== ВКЛАДКА 2: ПАТТЕРНЫ ====================
    with tab_patterns:
        st.header("🧩 Повторяющиеся комбинации (Паттерны)")
        st.caption(
            "Поиск пар, троек, четверок, пятерок и шестерок, которые выпадали вместе более 1 раза."
        )

        pattern_size = st.radio(
            "Выберите размер паттерна:",
            options=[3, 4, 5, 6],
            format_func=lambda x: f"Паттерны из {x} чисел",
            horizontal=True,
        )

        # Сбор всех комбинаций из всех тиражей
        pattern_counter = Counter()

        for _, row in df_draws.iterrows():
            draw_nums = sorted(
                [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]]
            )
            for comb in combinations(draw_nums, pattern_size):
                pattern_counter[comb] += 1

        # Фильтруем только повторяющиеся (более 1 раза)
        repeated_patterns = [
            (list(comb), count)
            for comb, count in pattern_counter.items()
            if count > 1
        ]
        repeated_patterns.sort(key=lambda x: x[1], reverse=True)

        if repeated_patterns:
            st.success(
                f"Найдено совпадений из {pattern_size} чисел: **{len(repeated_patterns)}**"
            )

            formatted_data = []
            for pat, count in repeated_patterns:
                formatted_data.append(
                    {
                        "Комбинация чисел": ", ".join(map(str, pat)),
                        "Количество повторений": count,
                    }
                )

            st.dataframe(
                pd.DataFrame(formatted_data),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                f"Совпадений комбинаций из {pattern_size} чисел пока не найдено (нужно больше тиражей в базе)."
            )

    # ==================== ВКЛАДКА 3: ИСТОРИЯ ====================
    with tab_history:
        st.header("📜 Введенные тиражи")

        df_display = df_draws.copy()
        df_display["Основные числа"] = df_display.apply(
            lambda r: f"{r['n1']}, {r['n2']}, {r['n3']}, {r['n4']}, {r['n5']}, {r['n6']}",
            axis=1,
        )

        st.dataframe(
            df_display[
                [
                    "id",
                    "draw_date",
                    "Основные числа",
                    "strong_number",
                ]
            ].rename(
                columns={
                    "id": "ID",
                    "draw_date": "Дата добавления",
                    "strong_number": "Сильное число",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.subheader("🗑️ Удаление тиража")
        del_id = st.number_input(
            "Введите ID тиража для удаления:",
            min_value=1,
            step=1,
        )
        if st.button("Удалить запись"):
            delete_draw(del_id)
            st.success(f"Запись ID {del_id} удалена.")
            st.rerun()
