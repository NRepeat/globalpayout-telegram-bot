from fastapi.routing import APIRouter

from bot_app.exchange_methods import BoxExchanger


rates_router = APIRouter(
    prefix="/rates",
    tags=["rates"],
)


@rates_router.get("/")
async def get_rates(
    uid: str
):
    print(uid)

    return {"rates": ''}


@rates_router.post("/update")
async def get_current_rate():
    return {"current_rate": "data"}
