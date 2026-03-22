from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0007_exchangetransaction_wallet_address_bank_name_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exchangetransaction',
            name='photo',
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
    ]
