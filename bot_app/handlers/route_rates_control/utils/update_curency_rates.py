from bot_app.misc import box_exchanger_client


async def update_curency_rates(routesIdsToUpdate, usdRate):
    for routeId in routesIdsToUpdate:
        # Assuming we need to update the 'to' currency of the route.
        currency_id_to_update = routeId.to.currency.id
        await box_exchanger_client.update_curency_rates(currency_id_to_update, usdRate)
