from app.database import SessionLocal

# Функция для получения сессии БД
def get_db():
    # Создаем новую сессию (подключение к БД)
    db = SessionLocal()
    try:
        # Отдаем сессию тому, кто её запросил
        yield db
    finally:
        # Всегда закрываем сессию, даже если была ошибка
        db.close()