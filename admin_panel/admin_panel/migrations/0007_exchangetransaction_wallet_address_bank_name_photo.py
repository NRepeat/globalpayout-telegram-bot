from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0006_exchangetransaction_rates'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchangetransaction',
            name='wallet_address',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='bank_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='photo',
            field=models.TextField(blank=True, null=True),
        ),
    ]
