from datetime import datetime

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID, uuid4
from enum import Enum

class Origin(str, Enum):
    home = "home"
    cafe = "cafe"

class RankedItem(BaseModel):
    name: str
    origin: Origin
    rating: float = Field(..., ge=0, le=5)
    cost_per_gram: float

    model_config ={
        "json_schema_extra" : {
            "example": {
                "name": "Ikuyo Ippodo Tea",
                "origin": "home",
                "rating": 3.9,
                "cost_per_gram": 0.8
            }

        }
    }

class RankedItemUpdate(BaseModel):
    name: Optional[str] = None
    origin: Optional[Origin] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    cost_per_gram: Optional[float] = None



class RankingBase(BaseModel):
    id: UUID
    user_id: UUID
    items: List[RankedItem]

    model_config =  {"json_schema_extra" : {
            "example": [{
                "id": "1d2c3b4a-1111-4222-8333-444455556666",
                "user_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "items": [
                    {
                        "name": "Ikuyo Ippodo Tea",
                        "origin": "home",
                        "rating": 3.9,
                        "cost_per_gram": 0.8
                    }
                ]
            }
            ]
        }
    }

class RankingCreate(BaseModel):
    id: UUID
    user_id: UUID
    items: List[RankedItem]

class RankingUpdate(BaseModel):
    items: List[RankedItem]

class RankingRead(RankingBase):
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp (UTC).",
        json_schema_extra={"example": "2025-01-15T10:20:30Z"},
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp (UTC).",
        json_schema_extra={"example": "2025-01-16T12:00:00Z"},
    )









