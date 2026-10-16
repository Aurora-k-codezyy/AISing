from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    username: str


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    phone: str | None = None
    credits: int
    status: str
    created_at: datetime | None = None


class AdminUserCreate(BaseModel):
    username: str
    password: str
    phone: str = ""
    credits: int = 480


class AdminUserUpdate(BaseModel):
    username: str | None = None
    phone: str | None = None
    credits: int | None = None
    status: str | None = None


class AdminPasswordReset(BaseModel):
    password: str


class AdminCreditAdd(BaseModel):
    amount: int
    note: str = ""


class AdminSupportUpdate(BaseModel):
    name: str
    qr_code_url: str = ""


class AdminConfigUpdate(BaseModel):
    signup_bonus_credits: int | None = None
    voice_train_cost: int | None = None
    song_process_cost: int | None = None
    recharge_price_per_credit: int | None = None
    daily_free_credits: int | None = None


class AdminPasswordUpdate(BaseModel):
    old_password: str
    new_password: str
