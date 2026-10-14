from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('INVENTORY', '0004_stock_created_at'),
    ]
    operations = [
        migrations.RemoveField(
            model_name='stock',
            name='created_at',
        ),
    ]
