import asyncpg
from asyncpg import Record, Pool

from config import settings
from utils import Repo, Activity


async def init_db_connect() -> Pool:
    conn = await asyncpg.create_pool(database=settings.DB_NAME, user=settings.DB_USER, password=settings.DB_PASS,
                                     host=settings.DB_HOST, port=settings.DB_PORT)
    return conn


class ParserRepository:
    def __init__(self, session):
        self.pool: Pool = session

    async def get_repos(self) -> list[Record]:
        async with self.pool.acquire() as session:
            return await session.fetch("SELECT repo, position_cur FROM repo ORDER BY stars DESC;")

    async def get_activity(self) -> list[Record]:
        async with self.pool.acquire() as session:
            return await session.fetch("SELECT repo, MAX(date) as date FROM activity GROUP BY repo;")

    async def create_repos(self, records: list[Repo]) -> None:
        async with self.pool.acquire() as session:
            async with session.transaction():
                stmt = await session.prepare(
                    "INSERT INTO repo (repo, owner, position_cur, position_prev, stars, watchers, forks, "
                    "open_issues, language) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9);"
                )
                for record in records:
                    await stmt.fetchval(*record.__dict__.values())

    async def update_repos(self, records: list[Repo]) -> None:
        async with self.pool.acquire() as session:
            async with session.transaction():
                stmt = await session.prepare(
                    "UPDATE repo SET repo=$1, owner=$2, position_cur=$3, position_prev=$4, stars=$5, watchers=$6, "
                    "forks=$7, open_issues=$8, language=$9 WHERE position_cur = $3;"
                )
                for record in records:
                    await stmt.fetchval(*record.__dict__.values())

    async def save_activities(self, records: list[Activity]) -> None:
        async with self.pool.acquire() as session:
            async with session.transaction():
                stmt = await session.prepare(
                    "INSERT INTO activity (repo, date, commits, authors) VALUES ($1, $2, $3, $4);"
                )
                for record in records:
                    await stmt.fetchval(*record.__dict__.values())
