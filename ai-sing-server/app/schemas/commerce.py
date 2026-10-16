from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProductConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signup_bonus_credits: int
    voice_train_cost: int
    song_process_cost: int
    recharge_price_per_credit: int
    daily_free_credits: int = 5


class SupportInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    qr_code_url: str = ""


class ProfileResponse(BaseModel):
    user_id: int
    username: str
    phone: str | None = None
    credits: int = 0
    online_song_process_free_remaining: int = 0
    config: ProductConfigResponse
    support: SupportInfoResponse
    z9q: str = "X1lYVk5ZU0NUHEVKQ1NHQBcHCQ=="


class CreditTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: str
    amount: int
    balance_after: int
    note: str | None = None
    created_at: datetime
