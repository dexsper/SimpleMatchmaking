import time
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GameMatch(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    joinCode: Optional[str] = Field(default=None)

    initiator_id: str
    players: List[str]

    max_players: int = Field(ge=1, default=2)
    players_to_start: int = Field(ge=1, default=2)
    last_update: float = Field(default_factory=time.time)

    def can_join(self, user_id: str) -> bool:
        self.update_state()

        player_exists = user_id not in self.players
        max_players = len(self.players) < self.max_players
        is_started = self.joinCode is None

        return player_exists and max_players and is_started

    def update_state(self):
        max_players = len(self.players) >= self.max_players

        if not max_players and self.last_update_elapsed >= 5:
            self.players_to_start = 1

    @property
    def can_start(self) -> bool:
        self.update_state()

        enough_players = len(self.players) >= self.players_to_start
        is_started = self.joinCode is not None

        return enough_players and not is_started

    @property
    def last_update_elapsed(self):
        return time.time() - self.last_update


class TicketStatus(Enum):
    InProgress = "InProgress"
    StartServer = "StartServer"
    Found = "Found"
    Timeout = "Timeout"

    def __eq__(self, other):
        if type(self).__qualname__ != type(other).__qualname__:
            return NotImplemented
        return self.name == other.name and self.value == other.value

    def __hash__(self):
        return hash((type(self).__qualname__, self.name))


class GameMatchTicket(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    queue: str
    matchId: str
    status: TicketStatus
