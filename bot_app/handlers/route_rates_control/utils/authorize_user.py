from bot_app.data_queries.user import get_user_by_id, save_user


async def authorize(db_connection, call, callback_data):
    if not await get_user_by_id(db_connection, call.from_user.id):
        await save_user(db_connection, call.from_user)
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return False

    if callback_data.user_caller_id != call.from_user.id:
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return False

    return True
