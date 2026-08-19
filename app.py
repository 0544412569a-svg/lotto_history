from collections import Counter
from io import BytesIO, StringIO
from itertools import combinations
import os
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import streamlit as st

st.set_page_config(
    page_title="Анализатор Лотереи 6/37", page_icon="🎰", layout="wide"
)

# --- Настройки Облака Mail.ru из Secrets ---
WEBDAV_HOSTNAME = "https://webdav.mail.ru"
WEBDAV_LOGIN = st.secrets.get("WEBDAV_LOGIN", "")
WEBDAV_PASSWORD = st.secrets.get("WEBDAV_PASSWORD", "")

FILENAME = "lotto_history.csv"
COLUMNS = ["n1", "n2", "n3", "n4", "n5", "n6", "strong_number"]


def get_auth():
    return HTTPBasicAuth(WEBDAV_LOGIN, WEBDAV_PASSWORD)


# --- Функции чтения и записи ---
def load_data():
    """Автоматическая загрузка данных при запуске приложения"""
    url = f"{WEBDAV_HOSTNAME}/{FILENAME}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        res = requests.get(
            url, auth=get_auth(), headers=headers, timeout=10
        )
        if res.status_code == 200:
            df = pd.read_csv(StringIO(res.text))
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = 0
            return df[COLUMNS]
    except Exception:
        pass

    # Резервная загрузка из локальной копии, если облако временно недоступно
    if os.path.exists(FILENAME):
        try:
            return pd.read_csv(FILENAME)[COLUMNS]
        except Exception:
            pass

    return pd.DataFrame(columns=COLUMNS)


def save_data(df):
    """Автоматическое сохранение данных в Облако Mail.ru"""
    url = f"{WEBDAV_HOSTNAME}/{FILENAME}"

    csv_data = df.to_csv(index=False).encode("utf-8")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Length": str(len(csv_data)),
    }

    try:
        res = requests.put(
            url,
            data=BytesIO(csv_data),
            auth=get_auth(),
            headers=headers,
            timeout=10,
        )

        if res.status_code in [200, 201, 204]:
            # Кэшируем успешную запись локально
            df.to_csv(FILENAME, index=False)
            return True
        else:
            st.error(
                f"Ошибка сохранения (Код {res.status_code}). Убедитесь, что файл '{FILENAME}' вручную создан в Облаке Mail.ru."
            )
            return False
    except Exception as e:
        st.error(f"Ошибка сети при отправке в Облако: {e}")
        return False


# Инициализация базы данных
df_draws = load_data()

st.title("🎰 Анализатор лотерейных тиражей (6/37 + Сильное число)")

# --- Боковая панель: Ввод тиража ---
with st.sidebar:
    st.header("➕ Добавить новый тираж")

    with st.form("add_draw_form", clear_on_submit=True):
        st.subheader("6 основных чисел (1–37):")
        cols = st.columns(3)

        n1 = cols[0].number_input(
            "№1", min_value=1, max_value=37, value=None, placeholder="1-37"
        )
        n2 = cols[1].number_input(
            "№2", min_value=1, max_value=37, value=None, placeholder="1-37"
        )
        n3 = cols[2].number_input(
            "№3", min_value=1, max_value=37, value=None, placeholder="1-37"
        )
        n4 = cols[0].number_input(
            "№4", min_value=1, max_value=37, value=None, placeholder="1-37"
        )
        n5 = cols[1].number_input(
            "№5", min_value=1, max_value=37, value=None, placeholder="1-37"
        )
        n6 = cols[2].number_input(
            "№6", min_value=1, max_value=37, value=None, placeholder="1-37"
        )

        st.subheader("Сильное число (1–7):")
        strong = st.number_input(
            "Сильное число",
            min_value=1,
            max_value=7,
            value=None,
            placeholder="1-7",
        )

        submit = st.form_submit_button("Сохранить тираж")

    if submit:
        nums = [n1, n2, n3, n4, n5, n6]
        if any(v is None for v in nums) or strong is None:
            st.error("❌ Заполните все 6 чисел и сильное число!")
        elif len(set(nums)) < 6:
            st.error("❌ Основные числа не должны повторяться!")
        else:
            nums_sorted = sorted([int(x) for x in nums])
            new_row = pd.DataFrame(
                [[*nums_sorted, int(strong)]], columns=COLUMNS
            )
            df_draws = pd.concat([df_draws, new_row], ignore_index=True)
            if save_data(df_draws):
                st.success("✅ Тираж успешно сохранен в Облако Mail.ru!")
                st.rerun()

    st.markdown("---")
    st.metric("Всего тиражей в базе", len(df_draws))

# --- Главный экран ---
if df_draws.empty:
    st.info(
        "👋 База данных пуста. Заполните и сохраните первый тираж в боковой панели!"
    )
else:
    tab_check, tab_stat, tab_patterns, tab_history = st.tabs(
        [
            "🎯 Проверка 24 комбинаций",
            "📊 Частотный анализ (Последние 50)",
            "🧩 Повторяющиеся паттерны",
            "📜 История тиражей",
        ]
    )

    # ==================== ВКЛАДКА 1: ПРОВЕРКА 24 КОМБИНАЦИЙ ====================
    with tab_check:
        st.header("🎯 Сравнение ваших комбинаций с выпавшим тиражом")

        draw_options = {
            idx: f"Тираж #{idx+1}: {row['n1']}, {row['n2']}, {row['n3']}, {row['n4']}, {row['n5']}, {row['n6']} (Сильное: {row['strong_number']})"
            for idx, row in df_draws.iterrows()
        }
        selected_draw_idx = st.selectbox(
            "Выберите тираж из базы для проверки:",
            options=list(reversed(list(draw_options.keys()))),
            format_func=lambda x: draw_options[x],
        )

        target_draw = df_draws.loc[selected_draw_idx]
        target_nums = set(
            [
                target_draw["n1"],
                target_draw["n2"],
                target_draw["n3"],
                target_draw["n4"],
                target_draw["n5"],
                target_draw["n6"],
            ]
        )
        target_strong = target_draw["strong_number"]

        st.caption(
            "Вставьте до 24 комбинаций. Формат: **6 чисел через запятую или пробел : сильное число** (Пример: `3, 12, 18, 22, 29, 35 : 4`). Каждая комбинация с новой строки."
        )

        default_text = "1, 2, 3, 4, 5, 6 : 1\n7, 8, 9, 10, 11, 12 : 2"
        user_input = st.text_area(
            "Ваши комбинации (до 24 строк):",
            value=default_text,
            height=250,
        )

        if st.button("🔍 Проверить совпадения"):
            lines = [
                line.strip() for line in user_input.split("\n") if line.strip()
            ][:24]
            results = []

            for i, line in enumerate(lines, 1):
                try:
                    if ":" in line:
                        main_part, strong_part = line.split(":")
                        user_strong = int(strong_part.strip())
                    else:
                        main_part = line
                        user_strong = None

                    raw_nums = main_part.replace(",", " ").split()
                    user_main = set([int(x) for x in raw_nums])

                    if len(user_main) != 6:
                        results.append(
                            {
                                "№": i,
                                "Введенная комбинация": line,
                                "Совпало основных": "Ошибка (нужно 6 чисел)",
                                "Сильное число": "-",
                                "Результат": "❌ Некорректно",
                            }
                        )
                        continue

                    matched_main = user_main.intersection(target_nums)
                    count_main = len(matched_main)
                    strong_match = (
                        "✅ Да"
                        if (user_strong and user_strong == target_strong)
                        else ("❌ Нет" if user_strong else "Не указано")
                    )

                    matched_str = (
                        ", ".join(map(str, sorted(matched_main)))
                        if matched_main
                        else "Нет"
                    )

                    results.append(
                        {
                            "№": i,
                            "Введенная комбинация": line,
                            "Совпало основных": f"{count_main} из 6 ({matched_str})",
                            "Сильное число": strong_match,
                            "Результат": f"🎯 {count_main} + {'1' if user_strong == target_strong else '0'}",
                        }
                    )
                except Exception:
                    results.append(
                        {
                            "№": i,
                            "Введенная комбинация": line,
                            "Совпало основных": "Ошибка формата",
                            "Сильное число": "-",
                            "Результат": "❌ Ошибка",
                        }
                    )

            st.dataframe(
                pd.DataFrame(results),
                use_container_width=True,
                hide_index=True,
            )

    # ==================== ВКЛАДКА 2: ЧАСТОТНЫЙ АНАЛИЗ ====================
    with tab_stat:
        st.header("📊 Анализ последних 50 тиражей")

        df_last50 = df_draws.tail(50)
        total_games = len(df_last50)

        st.caption(f"Анализируется тиражей: **{total_games}**")

        main_cols = ["n1", "n2", "n3", "n4", "n5", "n6"]
        all_main_numbers = df_last50[main_cols].values.flatten()
        main_counts = Counter(all_main_numbers)

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

        df_strong_all = pd.DataFrame(
            sorted_strong, columns=["Сильное число", "Выпадений"]
        )
        st.write("Все сильные числа за 50 игр:")
        st.dataframe(df_strong_all.transpose(), use_container_width=True)

    # ==================== ВКЛАДКА 3: ПАТТЕРНЫ ====================
    with tab_patterns:
        st.header("🧩 Повторяющиеся комбинации (Паттерны)")

        pattern_size = st.radio(
            "Выберите размер паттерна:",
            options=[3, 4, 5, 6],
            format_func=lambda x: f"Паттерны из {x} чисел",
            horizontal=True,
        )

        pattern_counter = Counter()

        for _, row in df_draws.iterrows():
            draw_nums = sorted(
                [
                    row["n1"],
                    row["n2"],
                    row["n3"],
                    row["n4"],
                    row["n5"],
                    row["n6"],
                ]
            )
            for comb in combinations(draw_nums, pattern_size):
                pattern_counter[comb] += 1

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
                f"Совпадений комбинаций из {pattern_size} чисел пока не найдено."
            )

    # ==================== ВКЛАДКА 4: ИСТОРИЯ ====================
    with tab_history:
        st.header("📜 Введенные тиражи")

        df_display = df_draws.copy()
        df_display["Основные числа"] = df_display.apply(
            lambda r: f"{r['n1']}, {r['n2']}, {r['n3']}, {r['n4']}, {r['n5']}, {r['n6']}",
            axis=1,
        )

        st.dataframe(
            df_display[["Основные числа", "strong_number"]].rename(
                columns={"strong_number": "Сильное число"}
            ),
            use_container_width=True,
        )

        st.markdown("---")
        st.subheader("🗑️ Удалить последний тираж")
        if st.button("Удалить последнюю запись"):
            if not df_draws.empty:
                df_draws = df_draws.iloc[:-1]
                if save_data(df_draws):
                    st.success("Запись удалена из Облака Mail.ru!")
                    st.rerun()
