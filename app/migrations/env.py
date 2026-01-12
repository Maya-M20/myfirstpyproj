from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# Alembic config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================================================
# КРИТИЧЕСКИ ВАЖНО: Настраиваем пути для импорта
# ============================================================================

# Получаем путь к директории migrations
migrations_dir = os.path.dirname(os.path.abspath(__file__))

# Путь к директории app (на уровень выше migrations)
app_dir = os.path.dirname(migrations_dir)

# Путь к корню проекта (на уровень выше app)
project_root = os.path.dirname(app_dir)

# Добавляем пути в sys.path в правильном порядке
sys.path.insert(0, project_root)  # Сначала корень проекта
sys.path.insert(0, app_dir)       # Затем директорию app

# Для отладки (можно закомментировать после настройки)
print(f"[Alembic] Project root: {project_root}")
print(f"[Alembic] App dir: {app_dir}")
print(f"[Alembic] Migrations dir: {migrations_dir}")
print(f"[Alembic] sys.path: {sys.path}")

# ============================================================================
# ИМПОРТ МОДЕЛЕЙ
# ============================================================================

try:
    # Импортируем модели из app
    from app.models import Base
    print("[Alembic] Models imported successfully")
except ImportError as e:
    print(f"[Alembic] Import error: {e}")
    print("[Alembic] Trying alternative import...")
    
    # Альтернативный импорт
    try:
        from models import Base
        print("[Alembic] Models imported via alternative path")
    except ImportError as e2:
        print(f"[Alembic] Alternative import also failed: {e2}")
        raise

target_metadata = Base.metadata

# ============================================================================
# ФУНКЦИИ МИГРАЦИЙ
# ============================================================================

def run_migrations_offline() -> None:
    """Запуск миграций в офлайн режиме."""
    url = config.get_main_option("sqlalchemy.url")
    
    # Используем DATABASE_URL из .env если есть
    if not url and "DATABASE_URL" in os.environ:
        url = os.environ["DATABASE_URL"]
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,           # Сравниваем типы столбцов
        compare_server_default=True, # Сравниваем значения по умолчанию
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в онлайн режиме."""
    # Проверяем DATABASE_URL из переменных окружения
    if "DATABASE_URL" in os.environ:
        print(f"[Alembic] Using DATABASE_URL from environment")
        config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()