from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0007_exchangetransaction_wallet_address_bank_name_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchangetransaction',
            name='bank_account',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
