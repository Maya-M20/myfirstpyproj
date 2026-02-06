from app.database import SessionLocal


#ф-ия для получения сессии БД
def get_db():
    # новая сессия
    db = SessionLocal()
    try:
        #передаем сессию тому, кто запросил
        yield db
    finally:
        db.close()
