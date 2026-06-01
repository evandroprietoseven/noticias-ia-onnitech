"""init"""

from alembic import op
import sqlalchemy as sa

revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company', sa.String(length=120), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('url', sa.String(length=1200), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('title_fingerprint', sa.String(length=256), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('url', name='uq_articles_url'),
    )
    op.create_index('ix_articles_company', 'articles', ['company'])
    op.create_index('ix_articles_published_at', 'articles', ['published_at'])
    op.create_index('ix_articles_title_fingerprint', 'articles', ['title_fingerprint'])

    op.create_table(
        'report_articles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('article_fingerprint', sa.String(length=256), nullable=False),
        sa.UniqueConstraint('report_date', 'article_fingerprint', name='uq_report_article_once_per_day'),
    )
    op.create_index('ix_report_articles_report_date', 'report_articles', ['report_date'])
    op.create_index('ix_report_articles_article_fingerprint', 'report_articles', ['article_fingerprint'])


def downgrade() -> None:
    op.drop_table('report_articles')
    op.drop_table('articles')
