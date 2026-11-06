"""Initial MVP schema. Frozen table definitions for reproducible migration."""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    tables = {
        'sources': [('id', 's', True), ('name', 's'), ('url', 't'), ('method', 's'), ('enabled', 'b'), ('last_checked_at', 's', False, True), ('last_status', 's'), ('audit_json', 't')],
        'events': [('id', 'i', True), ('canonical_url', 't'), ('title', 't'), ('source_id', 's'), ('published_at', 's', False, True), ('fetched_at', 's'), ('updated_at', 's'), ('data_mode', 's'), ('content_hash', 's'), ('event_type', 's'), ('countries_json', 't'), ('ports_json', 't'), ('policy_status', 's'), ('effective_at', 's', False, True), ('risk_level', 's'), ('risk_reasons_json', 't'), ('review_status', 's'), ('topic', 's')],
        'raw_revisions': [('id', 'i', True), ('event_id', 'i'), ('title', 't'), ('body', 't'), ('source_url', 't'), ('published_at', 's', False, True), ('fetched_at', 's'), ('content_hash', 's')],
        'analyses': [('id', 'i', True), ('event_id', 'i'), ('revision_id', 'i'), ('provider', 's'), ('analyzed_at', 's'), ('payload_json', 't'), ('error', 't', False, True)],
        'collection_logs': [('id', 'i', True), ('source_id', 's'), ('started_at', 's'), ('finished_at', 's'), ('status', 's'), ('collected', 'i'), ('inserted', 'i'), ('updated', 'i'), ('error', 't', False, True), ('details_json', 't')],
        'review_logs': [('id', 'i', True), ('target_type', 's'), ('target_id', 's'), ('actor', 's'), ('action', 's'), ('reason', 't'), ('created_at', 's'), ('data_mode', 's')],
        'port_overrides': [('id', 'i', True), ('port', 's'), ('data_mode', 's'), ('risk_level', 's'), ('reason', 't'), ('actor', 's'), ('updated_at', 's'), ('expires_at', 's')],
        'port_metrics': [('id', 'i', True), ('port', 's'), ('observed_at', 's'), ('waiting_hours', 'f'), ('source_url', 't'), ('data_mode', 's')],
        'shipment_snapshots': [('id', 'i', True), ('container_number', 's'), ('vessel', 's'), ('voyage', 's'), ('shipping_line', 's'), ('pol', 's'), ('pod', 's'), ('etd', 's', False, True), ('eta', 's'), ('atd', 's', False, True), ('ata', 's', False, True), ('status', 's'), ('updated_at', 's'), ('imported_at', 's'), ('data_mode', 's')],
        'reports': [('id', 'i', True), ('kind', 's'), ('period_start', 's'), ('period_end', 's'), ('data_mode', 's'), ('created_at', 's'), ('html', 't')],
    }
    types = {'s': sa.String, 't': sa.Text, 'i': sa.Integer, 'f': sa.Float, 'b': sa.Boolean}
    unique = {
        'events': ('canonical_url', 'data_mode'), 'raw_revisions': ('event_id', 'content_hash'),
        'port_overrides': ('port', 'data_mode'), 'port_metrics': ('port', 'observed_at', 'source_url', 'data_mode'),
        'shipment_snapshots': ('container_number', 'vessel', 'voyage', 'pol', 'pod', 'updated_at', 'data_mode'),
        'reports': ('kind', 'period_start', 'period_end', 'data_mode'),
    }
    foreign = {'events': [('source_id', 'sources', 'id')], 'raw_revisions': [('event_id', 'events', 'id')], 'analyses': [('event_id', 'events', 'id'), ('revision_id', 'raw_revisions', 'id')], 'collection_logs': [('source_id', 'sources', 'id')]}
    for name, fields in tables.items():
        columns = [sa.Column(f[0], types[f[1]](), primary_key=f[2] if len(f) > 2 else False, nullable=f[3] if len(f) > 3 else False) for f in fields]
        constraints = [sa.UniqueConstraint(*unique[name])] if name in unique else []
        constraints += [sa.ForeignKeyConstraint([col], [f'{target}.{key}']) for col, target, key in foreign.get(name, [])]
        op.create_table(name, *columns, *constraints)
    op.create_index('ix_events_content_hash', 'events', ['content_hash'])
    op.create_index('ix_analyses_event_id', 'analyses', ['event_id'])


def downgrade():
    for name in ['reports', 'shipment_snapshots', 'port_metrics', 'port_overrides', 'review_logs', 'collection_logs', 'analyses', 'raw_revisions', 'events', 'sources']:
        op.drop_table(name)
