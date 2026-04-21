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
    status = models.ForeignKey(
        Status, on_delete=models.SET_NULL, null=True, related_name="transactions"
    )
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="managed_transactions"
    )
    currency = models.CharField(max_length=36, blank=True, null=True)
    currency_xml_code = models.CharField(max_length=36, blank=True, null=True)
    amount = models.FloatField()
    rates = models.FloatField(blank=True, null=True)

    full_name = models.CharField(max_length=250, null=True, blank=True)
    card_number = models.CharField(max_length=100, null=True, blank=True)
    posted_in_chat = models.ForeignKey(
        TgChat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    posted_message_id = models.BigIntegerField(null=True, blank=True)
    usdt_amount = models.FloatField(null=True, blank=True)

    method_type = models.IntegerField(null=True, blank=True)
    service_name = models.CharField(max_length=50, null=True, blank=True)
    iban = models.CharField(max_length=34, null=True, blank=True)
    inn = models.CharField(max_length=12, null=True, blank=True)
    recipient_name = models.CharField(max_length=255, null=True, blank=True)
    payment_note = models.CharField(max_length=255, null=True, blank=True)
    payout_email = models.EmailField(null=True, blank=True)
    revtag = models.CharField(max_length=50, null=True, blank=True)
    wallet_address = models.CharField(max_length=200, null=True, blank=True)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    photo = models.TextField(null=True, blank=True)
    bank_account = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        db_table = "exchange_transaction"
        verbose_name = "Заявка на обмін"
        verbose_name_plural = "Заявки на обмін"

    def __str__(self):
        return f"Заявка {self.external_order_id} ({self.amount} {self.currency})"

    def get_telegram_formatted_application(self) -> str:
        details = []

        # Method 0: Карта
        if self.method_type == 0:
            if self.bank_account:
                details.append(f"🏦 Банк. счет: `{self.bank_account}`")
                if self.payout_email:
                    details.append(f"📧 Email: `{self.payout_email}`")
            else:
                details.append(f"💳 Карта: `{self.card_number}`")
                details.append(f"👤 ФИО: `{self.full_name}`")
            if self.bank_name:
                details.append(f"🏦 Банк: `{self.bank_name}`")
            if self.iban:
                details.append(f"🏦 IBAN: `{self.iban}`")
            if self.payment_note:
                details.append(f"📝 Призначення: `{self.payment_note}`")

        # Method 1: IBAN UAH
        elif self.method_type == 1:
            details.append(f"🏦 IBAN: `{self.iban}`")
            details.append(f"👤 ФИО: `{self.full_name}`")
            details.append(f"📄 ИНН: `{self.inn}`")

        # Method 2: SEPA
        elif self.method_type == 2:
            details.append(f"🇪🇺 SEPA IBAN: `{self.iban}`")
            details.append(f"👤 Имя (ФОП/ТОВ): `{self.recipient_name}`")
            details.append(f"📝 Назначение: `{self.payment_note}`")

        # Method 3: Email-кошелек
        elif self.method_type == 3:
            service = self.service_name.capitalize() if self.service_name else "Email"
            details.append(f"📧 {service} Email: `{self.payout_email}`")
            details.append(f"👤 ФИО: `{self.full_name}`")

        # Method 4: Revtag
        elif self.method_type == 4:
            details.append(f"📱 Revtag: `{self.revtag}`")
            details.append(f"👤 ФИО: `{self.full_name}`")
            if self.card_number:
                details.append(f"💳 Карта: `{self.card_number}`")

        # Method 5: Crypto
        elif self.method_type == 5:
            details.append(f"🔐 Гаманець: `{self.wallet_address}`")

        # Method 6: IBAN International
        elif self.method_type == 6:
            details.append(f"🌐 IBAN (міжнар.): `{self.iban}`")
            details.append(f"👤 ФИО: `{self.full_name}`")
            if self.bank_name:
                details.append(f"🏦 Банк: `{self.bank_name}`")

        # Method 7: CNY AliPay
        elif self.method_type == 7:
            details.append(f"🏦 Банк. счет: `{self.bank_account}`")
            if self.payout_email:
                details.append(f"📧 Email: `{self.payout_email}`")
            if self.payment_note:
                details.append(f"📝 Призначення: `{self.payment_note}`")

        # Method 8: CNY WeChat
        elif self.method_type == 8:
            details.append(f"🏦 Банк. счет: `{self.bank_account}`")
            if self.payout_email:
                details.append(f"📧 Email: `{self.payout_email}`")
            if self.payment_note:
                details.append(f"📝 Призначення: `{self.payment_note}`")

        else:
            # Обработка старых заявок, где method_type = None
            if self.card_number:
                details.append(f"💳 Карта: `{self.card_number}`")
            if self.full_name:
                details.append(f"👤 ФИО: `{self.full_name}`")
            if not details:
                details.append("❗️ Реквизиты не распознаны (старый формат).")

        details_block = "\n".join(details)

        text = f"""
        *Новая заявка на выплату*
        ---
        *ID Заявки:* `{self.external_order_id}`
        *ID Транзакции:* `{self.uuid}`
        *Сумма:* `{self.amount} {self.currency}`
        *Сервис:* `{self.service_name or "N/A"}`
        ---
        *Реквизиты:*
        {details_block}
        """
        return "\n".join([line.strip() for line in text.splitlines()])
