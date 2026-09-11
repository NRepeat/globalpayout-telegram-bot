from decimal import Decimal

from django.db import migrations, models


def seed_exchange_fees(apps, schema_editor):
    # стартовые строки справочника: 5 бирж с нулевой комиссией
    CloseFee = apps.get_model("admin_panel", "CloseFee")
    for account in ("binance", "okx", "htx", "bybit", "mexc"):
        CloseFee.objects.get_or_create(account=account, defaults={"fee": Decimal(0)})


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0009_exchangetransaction_payout_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchangetransaction',
            name='close_account',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='close_rate',
            field=models.DecimalField(blank=True, decimal_places=16, max_digits=32, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='close_fee',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='close_order_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.CreateModel(
            name='CloseFee',
            fields=[
                ('account', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('fee', models.DecimalField(decimal_places=8, default=0, max_digits=30)),
            ],
            options={
                'db_table': 'close_fees',
                'verbose_name': 'Комісія майданчика',
                'verbose_name_plural': 'Комісії майданчиків',
            },
        ),
        migrations.RunPython(seed_exchange_fees, migrations.RunPython.noop),
    ]
