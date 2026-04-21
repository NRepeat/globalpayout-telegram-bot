from django.contrib import admin

from .models import (
    ExchangeTransaction,
    TgChat,
    User,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("user_id", "name", "user_name", "senior_operator", "bot_admin")


@admin.register(TgChat)
class TgChatAdmin(admin.ModelAdmin):
    list_display = (
        "record_id",
        "chat_tg_id",
        "chat_title",
        "chat_user_name",
        "transaction_target",
    )




@admin.register(ExchangeTransaction)
class ExchangeOrderAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "external_order_id",
        "created_at",
        "currency",
        "amount",
        "status",
        "card_number",
        "usdt_amount",
    )
    readonly_fields = ("uuid", "currency", "status", "card_number", "posted_in_chat", "posted_message_id", "currency_xml_code", "amount", "full_name", "manager")
    list_filter = ("currency", "manager", "status")
    search_fields = ("uuid", "card_number", "external_order_id", "bank_account")
