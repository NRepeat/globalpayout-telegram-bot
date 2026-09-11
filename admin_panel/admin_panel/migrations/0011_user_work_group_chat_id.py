from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0010_close_fields"),
    ]

    operations = [
        # Особиста робоча група оператора. Nullable: поки не задана, бот працює
        # як раніше — у спільному чаті.
        migrations.AddField(
            model_name="user",
            name="work_group_chat_id",
            field=models.BigIntegerField(
                blank=True, null=True, verbose_name="Особиста робоча група (chat_id)"
            ),
        ),
    ]
