"""Initial schema

Revision ID: ef359456e494
Revises: 
Create Date: 2026-01-05 16:13:18.526998

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ef359456e494"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Код создания таблицы molecules
    op.create_table(
        "molecules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("formula", sa.String(length=100), nullable=False),
        sa.Column("molecular_weight", sa.Float(), nullable=False),
        sa.Column("smiles", sa.Text(), nullable=False),
        sa.Column("inchi", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_molecule_name_formula", "name", "formula"),
        sa.Index("idx_molecular_weight", "molecular_weight"),
    )
    op.create_index(op.f("ix_molecules_id"), "molecules", ["id"], unique=False)
    op.create_index(op.f("ix_molecules_name"), "molecules", ["name"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("molecules")
