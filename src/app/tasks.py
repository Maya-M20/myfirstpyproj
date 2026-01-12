from .celery_app import celery_app
from .database import SessionLocal
from .models import Molecule
import time


@celery_app.task(bind=True, name="substructure_search")
def substructure_search_task(self, search_data: dict):
    query = search_data.get("query")

    db = SessionLocal()

    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Поиск молекул", "progress": 30},
        )

        time.sleep(1)  # имитация долгой операции

        # 🔍 РЕАЛЬНЫЙ ПОИСК
        molecules = (
            db.query(Molecule)
            .filter(Molecule.smiles.ilike(f"%{query}%"))
            .all()
        )

        result = {
            "count": len(molecules),
            "matches": [
                {
                    "id": m.id,
                    "name": m.name,
                    "smiles": m.smiles,
                    "formula": m.formula,
                }
                for m in molecules
            ],
        }

        self.update_state(
            state="SUCCESS",
            meta={"progress": 100, "count": result["count"]},
        )

        return result

    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)},
        )
        raise

    finally:
        db.close()
