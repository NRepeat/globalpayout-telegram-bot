from fastapi import Depends, Header, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel

from bot_app.data_queries import Connection, get_db_connection
from bot_app.data_queries.api_allowed_keys import get_access_key
from bot_app.exchange_methods import GroupResponse
from bot_app.handlers.route_rates_control.utils import update_curency_rates
from bot_app.misc import box_exchanger_client


class RateUpdateRequest(BaseModel):
    type: str
    rate_from: float
    rate_to: float


rates_router = APIRouter(
    prefix="/rates",
    tags=["rates"],
)


@rates_router.get("/")
async def get_rates(uid: str):
    print(uid)

    return {"rates": ""}


@rates_router.post("/update")
async def update_rate(
    data: RateUpdateRequest,
    db_connection: Connection = Depends(get_db_connection),
    authorization: str | None = Header(default=None),
):
    print(authorization)
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )

    key_data = await get_access_key(db_connection, authorization.split(" ")[1])
    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access key is not valid",
        )

    groups = {
        "iban_uah": "65f337eb0298bbbe86d7d9c8",
        "card_uah": "691ae0a95de47f64ab1f98b7",
        "usdt_trc20": "6909d72b995c6afb48a4199a",
        "usdt_trc20_kzt": "690b1a4b12cbddc25ad34be3",
        "usdt_trc20_eur": "690b289b12cbddc25ad393d6",
    }

    target_group_id = groups.get(data.type)

    if not target_group_id:
        return {"error": f"ID для типа '{data.type}' не найден"}, 400

    try:
        await box_exchanger_client.update_manual_group_rate(
            target_group_id, data.rate_from, data.rate_to, 1
        )
        print(f"Группа {target_group_id} обновлена: {data.rate_from} -> {data.rate_to}")

        group: GroupResponse = await box_exchanger_client.get_group_by_id(
            target_group_id
        )

        if not group or not group.routeIds:
            return {"error": "Направления в группе не найдены"}, 404

        await update_curency_rates.update_curency_rates(group.routeIds, data.rate_to)
        print(f"Все направления ({len(group.routeIds)}) внутри группы обновлены.")

    except Exception as e:
        print(f"Ошибка при обновлении: {e}")
        return {"error": str(e)}, 500

    return {
        "status": "success",
        "group_id": target_group_id,
        "routes_count": len(group.routeIds),
        "new_rate": data.rate_to,
    }
