import asyncio
import random
import unittest

from fastapi.testclient import TestClient

from src.core.types.matchmaking import TicketStatus
from src.game.main import app
from src.schemas.matchmaking import TicketCreateRequest, TicketCreateResponse, TicketStatusResponse, \
    TicketUpdateServerRequest


class MatchmakingUser:
    name: str
    id: str

    def __init__(self, name: str, user_id: str):
        self.name = name
        self.id = user_id


class TestMatchmaking(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(app)

    def create_ticket(self, user: MatchmakingUser) -> TicketCreateResponse:
        response = self.client.post(
            f"/tickets?user_id={user.id}", json=TicketCreateRequest(queue="default").model_dump()
        )

        return TicketCreateResponse.model_validate_json(response.text)

    def get_ticket_status(self, user: MatchmakingUser, ticket_id: str) -> TicketStatusResponse:
        response = self.client.get(
            f"/tickets?user_id={user.id}&id={ticket_id}",
        )

        return TicketStatusResponse.model_validate_json(response.text)

    def update_match_server(self, user: MatchmakingUser, ticket_id: str, join_code: str):
        response = self.client.post(
            f"/tickets/update_server?user_id={user.id}",
            json=TicketUpdateServerRequest(
                id=ticket_id,
                joinCode=join_code
            ).model_dump()
        )

        return response.status_code

    async def test_one_user_match_timeout(self):
        user = MatchmakingUser("FirstUser", "user1")

        ticket = self.create_ticket(user)

        ticket_status = self.get_ticket_status(user, ticket.id)
        self.assertTrue(ticket_status.status == TicketStatus.InProgress, "Ticket InProgress")

        await asyncio.sleep(3)

        ticket_status = self.get_ticket_status(user, ticket.id)
        self.assertTrue(ticket_status.status == TicketStatus.InProgress, "Ticket progress after 3s")

        await asyncio.sleep(2)

        ticket_status = self.get_ticket_status(user, ticket.id)
        self.assertTrue(ticket_status.status == TicketStatus.StartServer, "Ticket server afters 5s")

        await asyncio.sleep(5)

        ticket_status = self.get_ticket_status(user, ticket.id)
        self.assertTrue(ticket_status.status == TicketStatus.Timeout, "Ticket timeout afters 5s")

    async def test_two_users_match_found(self):
        first_user = MatchmakingUser("FirstUser", "user1")
        second_user = MatchmakingUser("SecondUser", "user2")

        first_ticket = self.create_ticket(first_user)
        second_ticket = self.create_ticket(second_user)

        self.assertNotEqual(first_ticket.id, second_ticket.id, "Tickets equals")

        first_ticket_status = self.get_ticket_status(first_user, first_ticket.id)
        second_ticket_status = self.get_ticket_status(second_user, second_ticket.id)

        self.assertEqual(first_ticket_status.matchId, second_ticket_status.matchId, "Match id")
        self.assertTrue(first_ticket_status.status == TicketStatus.StartServer, "First ticket server")
        self.assertTrue(second_ticket_status.status == TicketStatus.InProgress, "Second ticket progress")

        second_user_update_server = self.update_match_server(second_user, second_ticket.id, "join")
        self.assertEqual(second_user_update_server, 403, "Second user update server")

        first_user_update_server = self.update_match_server(first_user, first_ticket.id, "join")
        self.assertEqual(first_user_update_server, 200, "First user update server")

        first_ticket_status = self.get_ticket_status(first_user, first_ticket.id)
        second_ticket_status = self.get_ticket_status(second_user, second_ticket.id)

        self.assertTrue(first_ticket_status.status == TicketStatus.Found, "First ticket found")
        self.assertTrue(second_ticket_status.status == TicketStatus.Found, "Second ticket found")

    async def test_five_users_match(self):
        users = []
        tickets = dict()

        for i in range(5):
            users.append(MatchmakingUser(f"UserName_{i}", f"user_id_{i}"))

        excess_user = random.choice(users)
        users.remove(excess_user)

        ticket = self.create_ticket(excess_user)
        await asyncio.sleep(5)
        excess_user_started = self.update_match_server(excess_user, ticket.id, "join")

        self.assertEqual(excess_user_started, 200, "Excess user started solo match")

        for user in users:
            ticket = self.create_ticket(user)
            tickets[user.id] = ticket

            await asyncio.sleep(random.random())

        self.assertEqual(len(set([tickets[user.id].id for user in users])), 4, "Four unique tickets")

        for user in users:
            ticket = self.get_ticket_status(user, tickets[user.id].id)
            tickets[user.id] = ticket

            await asyncio.sleep(random.random())

            if ticket.status == TicketStatus.StartServer:
                self.update_match_server(user, ticket.id, "join")
                tickets[user.id] = self.get_ticket_status(user, tickets[user.id].id)

        self.assertEqual(len(set([tickets[user.id].matchId for user in users])), 2, "Two unique game matches")
        self.assertTrue(all([tickets[user.id].status == TicketStatus.Found for user in users]),
                        "All tickets found match")


if __name__ == "__main__":
    unittest.main()
