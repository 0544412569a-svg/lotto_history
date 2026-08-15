def load_data():
    """Загрузка базы тиражей без использования вызова check()"""
    try:
        # Пытаемся сразу скачать файл
        client.download_sync(remote_path=FILENAME, local_path=FILENAME)
    except Exception:
        # Если скачивание не удалось (файла нет или первая загрузка)
        df_empty = pd.DataFrame(columns=COLUMNS)
        df_empty.to_csv(FILENAME, index=False)
        try:
            client.upload_sync(remote_path=FILENAME, local_path=FILENAME)
        except Exception as e:
            st.error(f"Не удалось загрузить стартовый файл в облако: {e}")

    # Чтение локальной копии
    if os.path.exists(FILENAME):
        try:
            df = pd.read_csv(FILENAME)
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = 0
            return df[COLUMNS]
        except Exception:
            return pd.DataFrame(columns=COLUMNS)

    return pd.DataFrame(columns=COLUMNS)
