from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    mongo_connected: bool
    version: str
