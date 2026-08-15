def save_data(df):
    """Надежное сохранение базы тиражей в Mail.ru Cloud"""
    try:
        # 1. Принудительно сохраняем локальную копию
        df.to_csv(FILENAME, index=False)

        # 2. Перезаписываем файл в облаке
        client.upload_sync(
            remote_path=FILENAME, local_path=FILENAME, overwrite=True
        )
        return True
    except Exception as e:
        st.error(f"Не удалось сохранить данные в облако: {e}")
        return False
