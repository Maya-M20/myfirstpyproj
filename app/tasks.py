from .celery_app import celery_app
from .database import SessionLocal
from .models import Molecule
import time


@celery_app.task(bind=True, name="substructure_search")
def substructure_search_task(self, search_data: dict):
    substructure = search_data.get("substructure")

    if not substructure:
        raise ValueError("substructure is required")

    db = SessionLocal()

    try:
        #стартуем
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "Запуск поиска",
                "progress": 10,
            },
        )

        time.sleep(0.5)

        #ищем в бд
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "Поиск молекул в базе данных",
                "progress": 50,
            },
        )

        molecules = (
            db.query(Molecule)
            .filter(Molecule.smiles.ilike(f"%{substructure}%"))
            .all()
        )

        time.sleep(0.5)

        #формировка рез-та
        results = [
            {
                "id": m.name,
                "smiles": m.smiles,
            }
            for m in molecules
        ]

        #конец
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "Формирование результата",
                "progress": 90,
            },
        )

        return {
            "molecules": results,
            "found_count": len(results),
        }

    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)},
        )
        raise

    finally:
        db.close()
