import asyncio
import time
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from contextlib import asynccontextmanager

from core.types.matchmaking import TicketStatus, GameMatchTicket, GameMatch
from schemas.matchmaking import TicketCreateRequest, TicketCreateResponse, TicketStatusRequest, TicketStatusResponse, \
    TicketUpdateServerRequest

game_matches: Dict[str, Dict[str, GameMatch]] = dict()
tickets: Dict[str, GameMatchTicket] = dict()

router = APIRouter()


@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(update_tickets())
    yield


def update_ticket(ticket: GameMatchTicket, match: GameMatch):
    if ticket.status is TicketStatus.InProgress and match.can_start:
        match.last_update = time.time()
        ticket.status = TicketStatus.StartServer

        return

    if ticket.status is TicketStatus.StartServer and match.joinCode is None and match.last_update_elapsed >= 5:
        game_matches[ticket.queue].pop(str(match.id))
        ticket.status = TicketStatus.Timeout

        return

    if ticket.status is not TicketStatus.Found and match.joinCode is not None:
        ticket.status = TicketStatus.Found


async def update_tickets():
    while True:
        for ticket in tickets.values():
            match_queue = game_matches.get(ticket.queue, None)
            match = match_queue.get(ticket.matchId, None) if match_queue is not None else None

            if match is None:
                ticket.status = TicketStatus.Timeout
                continue

            update_ticket(ticket, match)

        await asyncio.sleep(1)


def get_free_match(queue: str, user_id: str) -> GameMatch:
    match: Optional[GameMatch] = None

    if queue in game_matches:
        for match_id in game_matches[queue]:
            temp_match = game_matches[queue][match_id]

            if temp_match.can_join(user_id):
                match = temp_match
                break

    if match is not None:
        match.players.append(user_id)
        match.last_update = time.time()
    else:
        match = GameMatch(
            initiator_id=user_id,
            players=[user_id]
        )

        if queue not in game_matches:
            game_matches[queue] = dict()

        game_matches[queue][str(match.id)] = match

    return match


@router.post("/tickets")
async def create_match_ticket(ticket_request: TicketCreateRequest, user_id: str) -> TicketCreateResponse:
    queue = ticket_request.queue
    match = get_free_match(queue, user_id)

    ticket = GameMatchTicket(
        queue=queue,
        status=TicketStatus.InProgress,
        matchId=str(match.id)
    )

    tickets[str(ticket.id)] = ticket

    return TicketCreateResponse(
        id=str(ticket.id)
    )


@router.get("/tickets")
async def get_match_ticket(user_id: str, ticket_request: TicketStatusRequest = Depends()) -> TicketStatusResponse:
    ticket = tickets.get(ticket_request.id, None)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    if ticket.status is TicketStatus.Timeout:
        return TicketStatusResponse(
            id=str(ticket.id),
            status=ticket.status,
            matchId=None,
            players=[],
            joinCode=None
        )

    match_queue = game_matches.get(ticket.queue, None)
    match = match_queue.get(ticket.matchId, None) if match_queue is not None else None

    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found"
        )

    update_ticket(ticket, match)

    is_initiator = match.initiator_id == user_id
    response_status = TicketStatus.InProgress if ticket.status is TicketStatus.StartServer and not is_initiator else ticket.status

    return TicketStatusResponse(
        id=str(ticket.id),
        status=response_status,
        matchId=ticket.matchId,
        players=match.players,
        joinCode=match.joinCode
    )


@router.post("/tickets/update_server")
async def update_match_server(server_request: TicketUpdateServerRequest, user_id: str) -> TicketStatusResponse:
    ticket = tickets.get(server_request.id, None)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    if ticket.status is TicketStatus.Timeout:
        raise HTTPException(
            status_code=400,
            detail="The ticket has expired"
        )

    match_queue = game_matches.get(ticket.queue, None)
    match = match_queue.get(ticket.matchId, None) if match_queue is not None else None

    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found"
        )

    if match.initiator_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can't update server for this match"
        )

    if ticket.status is TicketStatus.Found or match.joinCode is not None:
        raise HTTPException(
            status_code=409,
            detail="Server for this match already set"
        )

    if not match.can_start:
        raise HTTPException(
            status_code=400,
            detail="This match can't start now"
        )

    ticket.status = TicketStatus.Found

    match.joinCode = server_request.joinCode
    match.last_update = time.time()

    return TicketStatusResponse(
        id=str(ticket.id),
        status=ticket.status,
        matchId=ticket.matchId,
        players=match.players,
        joinCode=match.joinCode
    )
