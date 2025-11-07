from django.db import models


class User(models.Model):
    user_id = models.BigIntegerField(unique=True, null=False, primary_key=True)
    name = models.CharField(max_length=100)
    user_name = models.CharField(max_length=150, blank=True, null=True)
    senior_operator = models.BooleanField(
        default=False, verbose_name="Старший оператор"
    )
    bot_admin = models.BooleanField(default=False, verbose_name="Адміністратор бота")

    class Meta:
        db_table = "data_tg_user"
        verbose_name_plural = "Користувачі бота"

    def __str__(self):
        return f"{self.user_id} {self.user_name}"


class TgChat(models.Model):
    record_id = models.BigIntegerField(unique=True, null=False, primary_key=True)
    chat_tg_id = models.CharField(
        max_length=100, unique=True, verbose_name="ID чата в Telegram"
    )
    chat_title = models.CharField(
        max_length=150, blank=True, null=True, verbose_name="Название чата"
    )
    chat_user_name = models.CharField(
        max_length=150, blank=True, null=True, verbose_name="Username чата"
    )
    transaction_target = models.BooleanField(
        default=False, verbose_name="Публікуйте applications в цьому чаті"
    )

    class Meta:
        db_table = "tg_chat"
        verbose_name = "Telegram чат"
        verbose_name_plural = "Telegram чати"

    def __str__(self):
        return f"{self.chat_title} {self.chat_user_name}"

    ## custom save function to prevent having 2 application targets chats

    def save(self, *args, **kwargs):
        if self.transaction_target:
            TgChat.objects.filter(transaction_target=True).update(
                transaction_target=False
            )
        super().save(*args, **kwargs)


class Status(models.Model):
    record_id = models.BigIntegerField(unique=True, null=False, primary_key=True)
    status_code = models.CharField(max_length=100, unique=True)
    status_title = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "data_status"
        verbose_name = "Статус"
        verbose_name_plural = "Статуси"

    def __str__(self):
        return f"{self.status_title} ({self.status_code})"


class ExchangeTransaction(models.Model):
    uuid = models.CharField(null=False, max_length=36, primary_key=True)
    external_order_id = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    currency = models.CharField(max_length=36, blank=True, null=True)
    currency_xml_code = models.CharField(max_length=36, blank=True, null=True)
    amount = models.FloatField()
    full_name = models.CharField(max_length=250, null=True, blank=True)
    card_number = models.CharField(max_length=100, null=True, blank=True)
    posted_in_chat = models.ForeignKey(
        TgChat, on_delete=models.SET_NULL, null=True, blank=True
    )
    posted_message_id = models.BigIntegerField(null=True, blank=True)
    usdt_amount = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "exchange_transaction"
        verbose_name = "Заявка на обмін"
        verbose_name_plural = "Заявки на обмін"
