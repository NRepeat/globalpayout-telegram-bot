from datetime import datetime
import hashlib
import json
from pandas.core.util.numba_ import Callable
from typing_extensions import List
from bot_app.config import settings
import json
import hashlib
import asyncio
from typing import Optional, Any
from pydantic import BaseModel, ValidationError, Field
import aiohttp
from typing import Optional
from bot_app.utils import format_unix_timestamp


class Discount(BaseModel):
    amountMoreThan: Optional[float] = Field(None)
    discountPercent: Optional[float] = Field(None)


class ManualRateDetails(BaseModel):
    from_: float = Field(alias="from")
    to: float = Field(alias="to")
    update_at: float = Field(alias="updateAt")


class RouteFromCurrency(BaseModel):
    active: bool
    decimal: float
    deleted: bool
    fields: list
    id: str = Field(alias="_id")
    image: dict[str, Any]
    name: str
    payment_details: dict[str, Any] = Field(alias="paymentDetails")
    symbol: str
    usd: dict[str, Any]
    verification: dict[str, Any]
    xml: str


class RouteFromInformation(BaseModel):
    currency: RouteFromCurrency
    discounts: list[Discount]
    fee_amount: float = Field(alias="feeAmount")
    fee_percent: float = Field(alias="feePercent")
    max: float
    min: float
    min_fee: float = Field(alias="minFee")


# {
#     "_id": "67a3a7578f9ff4e2dacd5d32",
#     "route_name": "USDT/UAH",
#     "from_currency": "usdt",
#     "to_currency": "uah",
#     "rate_buy": 42.89,
#     "parser_id": "binance_p2p",
#     "updatedAt": "Fri Feb 07 2025 08:22:40 GMT+0000 (Coordinated Universal Time)"
# }


class RateParsers(BaseModel):
    id_: str = Field(alias="_id")
    route_name: str = Field()
    from_currency: str = Field()
    to_currency: str = Field()
    rate_buy: float = Field()
    parser_id: str = Field()
    updated_at: str = Field(alias="updatedAt")


class RouteRate(BaseModel):
    change_fee_amount: float = Field(alias="changeFeeAmount")
    change_fee_percent: float = Field(alias="changeFeePercent")
    change_percent_re_calculate: float = Field(alias="changePercentReCalculate")
    change_percent_re_calculate_up: float = Field(alias="changePercentReCalculateUp")
    enable_parser: bool = Field(alias="enableParser")
    limit_percent_from_start_to_re_calculate: float = Field(
        alias="limitPercentFromStartToReCalculate"
    )
    loss_fee_amount: float = Field(alias="lossFeeAmount")
    loss_fee_percent: float = Field(alias="lossFeePercent")
    manual: ManualRateDetails
    parsers: list[RateParsers]
    source_type: str = Field(alias="sourceType")
    type_calculate: str = Field(alias="typeCalculate")


class RouteToCurrency(BaseModel):
    active: bool
    decimal: float
    deleted: bool
    fields: list
    id: str = Field(alias="_id")
    image: dict[str, Any]
    name: str
    payout: Optional[Any]
    payout_enabled: bool = Field(alias="payoutEnabled")
    payment_details: Optional[dict[str, Any]] = Field(None, alias="paymentDetails")
    reserve: dict[str, Any]
    symbol: str
    usd: dict[str, Any]
    verification: Optional[dict[str, Any]] = None
    xml: str


class RouteToInformation(BaseModel):
    currency: RouteToCurrency
    fee_amount: float = Field(alias="feeAmount")
    fee_percent: float = Field(alias="feePercent")
    max: float
    min: float
    min_fee: float = Field(alias="minFee")


class RouteResponse(BaseModel):
    active: bool
    additional_reserve: float = Field(alias="additionalReserve")
    created_at: str = Field(alias="createdAt")
    deleted: bool
    disable_by_schedule: bool = Field(alias="disableBySchedule")
    disable_by_server: bool = Field(alias="disableByServer")
    errors: list[dict[str, Any]]
    fields: list[dict[str, Any]]
    from_: RouteFromInformation = Field(alias="from")
    id: str = Field(alias="_id")
    instructions: list
    insurance_rate: dict[str, Any] = Field(alias="insuranceRate")
    is_auto_payout: bool = Field(alias="isAutoPayout")
    is_available: bool = Field(alias="isAvailable")
    is_export: bool = Field(alias="isExport")
    is_show_bot: bool = Field(alias="isShowBot")
    is_show_web: bool = Field(alias="isShowWeb")
    order_ttl: float = Field(alias="orderTTL")
    priority_payment_details: dict[str, Any] = Field(alias="priorityPaymentDetails")
    rate: RouteRate
    required_documents: list = Field(alias="requiredDocuments")
    required_verification_user: dict[str, Any] = Field(alias="requiredVerificationUser")
    result_exchange: dict[str, Any] = Field(alias="resultExchange")
    schedule_id: Optional[str] = Field(None, alias="scheduleId")
    seo: dict[str, Any]
    to: RouteToInformation = Field()
    updated_at: str = Field(alias="updatedAt")
    verification: dict[str, Any]

    def get_formatted_route_name(self) -> str:
        return f"{self.from_.currency.name} ({self.from_.currency.xml}) ➡️ {self.to.currency.name} ({self.to.currency.xml})"

    def get_rate_information_in_text_format(self) -> str:
        parser_state = "✅ Працює" if self.rate.enable_parser else "❌ Вимкнено"
        if not self.rate.parsers:
            parsers_info = "<b>Парсерів не встановлено</b>\n"
        else:
            parsers_info = f"<b>Парсери ({parser_state}):</b>\n"
            for parser in self.rate.parsers:
                parsers_info += f"🤖 {parser.parser_id}\n💱 {parser.route_name}\n📅 {parser.updated_at}\n💹 {parser.rate_buy} \n\n"

        rate_info_text = f"""
<b>Встановлений вручну курс:</b>
💹 {self.rate.manual.from_} / {self.rate.manual.to}
📅 {format_unix_timestamp(self.rate.manual.update_at)}

{parsers_info}
"""
        return rate_info_text

    def get_current_discounts_text(self) -> str:
        current_discounts_text = "\n".join(
            [
                f"{discount.discountPercent}% для сум від {discount.amountMoreThan} <b>{self.from_.currency.xml}</b>"
                for discount in self.from_.discounts
            ]
        )
        if not current_discounts_text:
            discounts_info = "<b>Наразі діючих знижок не встановлено</b>"
        else:
            discounts_info = "Поточні знижки:\n" + current_discounts_text
        return discounts_info


# class GroupResponse(BaseModel):


class APIError(Exception):
    def __init__(self, message: str, error_code: float):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class Currency(BaseModel):
    id: str = Field(alias="_id")
    name: str
    symbol: str


class FromTo(BaseModel):
    currency: Currency


class RouteId(BaseModel):
    id: str = Field(alias="_id")
    from_: FromTo = Field(alias="from")
    to: FromTo

    def get_formatted_route_name(self) -> str:
        return f"{self.from_.currency.name} ({self.from_.currency.symbol}) ➡️ {self.to.currency.name} ({self.to.currency.symbol})"


class GroupResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    routeIds: List[RouteId]
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class GroupsListResponse(BaseModel):
    groups: List[GroupResponse]


class BoxExchanger:
    def __init__(self):
        self.base_url = settings.EXCHANGE_BASE_URL
        self.api_key = settings.EXCHANGE_API_KEY
        self.secret = settings.EXCHANGE_SECRET_KEY

    def generate_hash(self, get_params, post_params):
        for key in get_params:
            if isinstance(get_params[key], list):
                get_params[key] = [str(value) for value in get_params[key]]
            else:
                get_params[key] = str(get_params[key])

        params = {**get_params, **post_params}
        checksum_params = hashlib.sha256(
            json.dumps(params, separators=(",", ":")).encode()
        ).hexdigest()
        request_hash = hashlib.sha256(
            (checksum_params + self.secret).encode()
        ).hexdigest()
        return request_hash

    async def get_routes(self) -> list[RouteResponse]:
        try:
            response = await self.call(method="GET:admin/exchanger/route/get")
            return [RouteResponse(**route) for route in response.get("routes", [])]
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def get_route_by_id(self, route_id: str) -> RouteResponse:
        try:
            response = await self.call(
                method="GET:admin/exchanger/route/get/one",
                param={"get": {"id": route_id}},
            )
            return RouteResponse(**response)
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def change_parser_state(self, route_id: str, state: bool):
        try:
            response = await self.call(
                method="PUT:admin/exchanger/route/edit",
                param={"post": {"route_id": route_id, "enableParser": state}},
            )
            return response
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def get_order_info(self, order_id: str):
        try:
            response = await self.call(
                method="GET:admin/exchanger/order/get",
                param={"get": {"uid": order_id}},
            )
            return response
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def update_manual_rate(
        self, route_id: str, from_: float, to: float, updated_at: float
    ):
        try:
            response = await self.call(
                method="PUT:admin/exchanger/route/edit",
                # param={"post": {"route_id": route_id, "rateManual[from]": str(from_), "rateManual[to]": str(to)} },
                param={
                    "post": {
                        "route_id": route_id,
                        "rateManual": {"from": str(from_), "to": str(to)},
                    }
                },
            )
            return response
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def update_route_discounts(self, route_id: str, discounts: list[Discount]):
        payload = {}
        payload["fromDiscounts"] = []
        for idx, discount in enumerate(discounts):
            payload["fromDiscounts"].append(
                {
                    "amountMoreThan": str(discount.amountMoreThan),
                    "discountPercent": str(discount.discountPercent),
                }
            )
        payload["route_id"] = route_id
        try:
            response = await self.call(
                method="PUT:admin/exchanger/route/edit",
                param={"post": payload},
            )
            return response
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def get_groups(self) -> GroupsListResponse:
        try:
            response = await self.call(
                method="GET:admin/exchanger/route/group/get/list"
            )
            print(f"API Response: {response}")
            return GroupsListResponse(**response)

        except ValidationError as e:
            # This will catch errors if the API data doesn't match your models
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def get_group_by_id(self, group_external_id: str) -> GroupResponse:
        try:
            response = await self.call(
                method="GET:admin/exchanger/route/group/get/one",
                param={"get": {"id": group_external_id}},
            )
            return GroupResponse(**response["group"])

        except ValidationError as e:
            # This will catch errors if the API data doesn't match your models
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def update_manual_group_rate(
        self, group_id: str, from_: float, to: float, updated_at: float
    ):
        try:
            response = await self.call(
                method="PUT:admin/exchanger/route/editByGroup/",
                param={
                    "post": {
                        "group_id": group_id,
                        "rateManual": {"from": str(from_), "to": str(to)},
                    }
                },
            )
            return response
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)
        return

    async def change_parser_state_for_group(self, group_id: str, state: bool):
        try:
            response = await self.call(
                method="PUT:admin/exchanger/route/editByGroup/",
                param={"post": {"group_id": group_id, "enableParser": state}},
            )
            return response
        except ValidationError as e:
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def update_curency_rates(self, currency_id: str, rate):
        try:
            response = await self.call(
                method="PUT:admin/exchanger/currency/edit",
                param={"post": {"currency_id": currency_id, "manualRateUSD": rate}},
            )
            return response

        except ValidationError as e:
            # This will catch errors if the API data doesn't match your models
            raise APIError(message=f"Validation error: {str(e)}", error_code=400)

    async def call(self, method: str, param=None):
        if param is None:
            param = {}
        get = param.get("get", {})
        post = param.get("post", {})

        if not isinstance(get, dict):
            return {
                "errorCode": 20,
                "message": 'Error invalid "get" params must be object',
            }
        if not isinstance(post, dict):
            return {
                "errorCode": 21,
                "message": 'Error invalid "post" params must be object',
            }
        method_parts = method.split(":")
        typeMethod = "POST"
        if len(method_parts) == 2:
            typeMethod, method = method_parts[0].upper(), method_parts[1]
        else:
            method = method_parts[0]
        get["time"] = float(1000 * asyncio.get_event_loop().time())

        url_params = "&".join(
            f"{key}={value}"
            if not isinstance(value, list)
            else "&".join(f"{key}[]={item}" for item in value)
            for key, value in get.items()
        )
        url = f"{self.base_url}{method}?{url_params}"
        url_params += f"&time={get['time']}" if "time" in get else ""
        request_hash = self.generate_hash(get, post)

        async with aiohttp.ClientSession() as session:
            headers = {
                "content-type": "application/json",
                "cache-control": "no-cache",
                "apikey": self.api_key,
                "hash": request_hash,
            }
            async with session.request(
                typeMethod, url, headers=headers, json=post if post else None
            ) as response:
                print(f"API Response: {response}")
                if response.status != 200:
                    raise APIError(
                        message=f"Request failed with status {response.status}",
                        error_code=response.status,
                    )

                if "application/json" in response.headers.get("content-type", ""):
                    text = await response.text()
                    body: dict = json.loads(text)
                    if body.get("success") and body.get("data"):
                        return body["data"]
                    if body.get("result"):
                        return body["result"]
                    if body.get("success") == False:
                        error_body = body.get("error")
                        raise APIError(
                            message=error_body.get("message"),
                            error_code=error_body.get("errorCode"),
                        )
                    return

                else:
                    text = await response.text()
                    return {
                        "message": f"Error response not json: {text}",
                        "errorCode": response.status,
                    }
