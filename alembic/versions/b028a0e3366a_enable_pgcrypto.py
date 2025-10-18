"""enable pgcrypto"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b028a0e3366a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")


def downgrade():
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
