from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0008_exchangetransaction_bank_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchangetransaction',
            name='country',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='sort_code',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='account_number',
            field=models.CharField(blank=True, max_length=34, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='idram_account',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='ifsc',
            field=models.CharField(blank=True, max_length=11, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='upi_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='paytm_wallet',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='pix_keys',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='cpf',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='cvu_cbu',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='separate_direction',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='exchangetransaction',
            name='telegram',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
