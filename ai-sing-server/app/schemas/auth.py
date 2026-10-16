from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user_id: int
    username: str
    token: str
    phone: str = ""
    credits: int = 0
    z9q: str = "X1lYVk5ZU0NUHEVKQ1NHQBcHCQ=="


class MeResponse(BaseModel):
    user_id: int
    username: str
    phone: str
    credits: int
    z9q: str = "X1lYVk5ZU0NUHEVKQ1NHQBcHCQ=="

