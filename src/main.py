import asyncio
import logging
import sys

from game import main as game_main


async def main() -> None:
    game_task = asyncio.create_task(game_main())
    await asyncio.gather(game_task)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
