from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BaseAuthSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class UserCreateSchema(BaseAuthSchema):
    name: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)


class UserLoginSchema(BaseAuthSchema):
    name: str
    password: str


class TokenRefreshSchema(BaseAuthSchema):
    refresh_token: str


class UserResponseSchema(BaseAuthSchema):
    id: UUID
    name: str


class TokenResponseSchema(BaseAuthSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
