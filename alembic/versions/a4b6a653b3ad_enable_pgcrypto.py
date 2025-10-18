"""enable pgcrypto

Revision ID: a4b6a653b3ad
Revises: 
Create Date: 2025-10-18 17:30:23.544011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b6a653b3ad'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

def downgrade():
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
    