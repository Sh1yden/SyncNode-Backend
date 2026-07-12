from pydantic import BaseModel


class DefaultSchema(BaseModel):
    status: bool
