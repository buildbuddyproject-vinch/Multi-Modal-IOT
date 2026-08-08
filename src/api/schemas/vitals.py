from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, create_model

from src.api.schemas.common import VitalsSource
from src.data.schema import CLINICAL_CHANNELS

# Built dynamically from the canonical channel list (src/data/schema.py) so this
# schema can never drift from what the model/pipeline actually expects -- adding a
# channel there automatically shows up here, in validation and in Swagger.
# extra="forbid" so a typo'd or unknown channel name is a 422, not silently dropped.
ChannelsIn = create_model(
    "ChannelsIn",
    __config__=ConfigDict(extra="forbid"),
    **{channel: (Optional[float], None) for channel in CLINICAL_CHANNELS},
)


class VitalsIn(BaseModel):
    patient_id: str
    timestamp: datetime
    source: VitalsSource
    channels: ChannelsIn
    ingest_seq: Optional[int] = None


class VitalsOut(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    source: str
    channels: dict
    ingest_seq: Optional[int] = None
    created_at: Optional[datetime] = None
