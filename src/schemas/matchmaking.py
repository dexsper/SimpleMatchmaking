from typing import Optional, List

from pydantic import BaseModel
from core.types.matchmaking import TicketStatus


class TicketCreateRequest(BaseModel):
    queue: str


class TicketCreateResponse(BaseModel):
    id: str


class TicketStatusRequest(BaseModel):
    id: str


class TicketStatusResponse(BaseModel):
    id: str
    status: TicketStatus

    matchId: Optional[str]
    players: List[str]
    joinCode: Optional[str]


class TicketUpdateServerRequest(BaseModel):
    id: str
    joinCode: str
