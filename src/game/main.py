import asyncio
import uvicorn

from fastapi import FastAPI
from .matchmaking import router as matchmaking_router

app = FastAPI(
    title="Pacman Demo Backend",
    version="0.0.1",
    contact={
        "name": "Dexsper",
        "url": "https://github.com/dexsper",
        "email": "dexsperpro@gmail.com"
    },
    docs_url="/api/docs"
)
app.include_router(matchmaking_router)


async def main() -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)

    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
