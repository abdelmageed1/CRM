# Generated migration to fix the foreign key constraint

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm_calls_sales', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Add the requested_by foreign key pointing to accounts_user
            sql="""
            ALTER TABLE crm_client_edit_request
            ADD CONSTRAINT crm_client_edit_request_requested_by_id_fk
            FOREIGN KEY (requested_by_id)
            REFERENCES accounts_user (id) ON DELETE CASCADE
            """,
            reverse_sql="""
            ALTER TABLE crm_client_edit_request
            DROP CONSTRAINT IF EXISTS crm_client_edit_request_requested_by_id_fk
            """,
            state_operations=[],
        ),
        migrations.RunSQL(
            # Add the reviewed_by foreign key pointing to accounts_user
            sql="""
            ALTER TABLE crm_client_edit_request
            ADD CONSTRAINT crm_client_edit_request_reviewed_by_id_fk
            FOREIGN KEY (reviewed_by_id)
            REFERENCES accounts_user (id) ON DELETE SET NULL
            """,
            reverse_sql="""
            ALTER TABLE crm_client_edit_request
            DROP CONSTRAINT IF EXISTS crm_client_edit_request_reviewed_by_id_fk
            """,
            state_operations=[],
        ),
    ]
