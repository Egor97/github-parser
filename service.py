import asyncio
from datetime import datetime, timedelta
from logging import getLogger
from typing import Any

import aiohttp

from database import ParserRepository
from utils import Repo, Activity, mapping_repo, mapping_activity, headers

logger = getLogger(__name__)


async def get_data_from_github(url: str, x_headers: dict[str, str]):
    async with aiohttp.ClientSession() as http_session:
        async with http_session.get(url, headers=x_headers) as response:
            res = await response.json(content_type='application/json')
            if len(res) == 0:
                return []
            return res


def set_headers(x_headers, api_token) -> dict[str, str]:
    x_headers['Authorization'] += api_token
    return x_headers


class YandexCloudService:
    GITHUB_URL_TOP_100 = 'https://api.github.com/search/repositories?q=stars:>10000&sort=stars&order=desc&per_page=100'
    GITHUB_URL_REPO_ACTIVITY = 'https://api.github.com/repos/{}/commits?since={}&per_page=100&page={}'

    def __init__(self, api_token, parser_repository):
        self.old_top = None
        self.old_repo_activities = None
        self.api_token = api_token
        self.repository: ParserRepository = parser_repository
        self.headers = set_headers(headers, self.api_token)

    async def _parse_repos(self, x_headers) -> list[Repo]:
        return await self._get_and_prepare_repos_from_github(x_headers)

    async def _parse_repos_activities(self, repos_names, x_headers):
        activities = []

        repo_activities = await self._get_and_prepare_repos_activity(repos_names, self.old_repo_activities, x_headers)
        logger.debug('Trying to prepare repository activity')
        for activity in repo_activities:
            try:
                activity = await self._prepare_repo_activity(activity)
            except Exception as ex:
                logger.exception(ex)
                raise ex
            activities.extend(activity)
        logger.debug('Success')

        return activities

    async def _get_and_prepare_repos_from_github(self, x_headers) -> list[Repo]:
        raw_repos = await get_data_from_github(self.GITHUB_URL_TOP_100, x_headers)
        return await self._prepare_repos(raw_repos.get('items'))

    async def _get_old_top(self) -> dict:
        records = await self.repository.get_repos()
        return {record['repo']: record['position_cur'] for record in records}

    async def _get_and_prepare_repos_activity(self, repos_names: list[str],
                                              old_activities: dict[str, str],
                                              x_headers: dict[str, str]) -> list[dict[str, list[Activity]]]:
        dates = [old_activities[name] if name in old_activities else (datetime.utcnow() - timedelta(weeks=1)).date() for
                 name in repos_names]
        request_params = list(zip(repos_names, dates))

        logger.debug('Trying to get repository activity from github')
        repos_activity_tasks = [asyncio.create_task(self._get_repo_activity_from_github(*params,
                                                                                        x_headers=x_headers)) for
                                params in request_params]

        repos_activities = [activity for activity in await asyncio.gather(*repos_activity_tasks) if activity]
        logger.debug('Success')

        return repos_activities

    async def _get_repo_activity_from_github(self, repo_name: str, start_date: datetime.date,
                                             x_headers: dict[str, str]) -> dict[str, list[dict[str, Any]]] | None:
        activity = []
        page = 1

        while True:
            response = await get_data_from_github(self.GITHUB_URL_REPO_ACTIVITY.format(repo_name, start_date, page),
                                                  x_headers)
            if len(response) == 0:
                break

            activity.extend(response)
            page += 1

        if activity:
            return {repo_name: activity}

    async def _get_old_repos_activities(self):
        records = await self.repository.get_activity()
        return {record['repo']: record['date'] for record in records}

    @staticmethod
    async def _prepare_repos(repos: list) -> list[Repo]:
        records = []

        for i in range(len(repos)):
            entity = repos[i]
            record = (
                entity['full_name'], entity['owner']['login'], i + 1, i + 1, entity['stargazers_count'],
                entity['watchers_count'], entity['forks'], entity['open_issues'], entity['language']
            )
            records.append(mapping_repo(record))

        return records

    @staticmethod
    async def _update_top(old_top: dict[str, int | None], new_top: list[Repo]) -> list[Repo]:
        for repo in new_top:
            if repo.repo in old_top:
                repo.position_prev = old_top[repo.repo]

        return new_top

    @staticmethod
    async def _prepare_repo_activity(repo_activity: dict) -> list[Activity]:
        repo, activities = list(repo_activity.items())[0]
        daily_activity = {}

        for activity in activities:
            key = datetime.strptime(activity['commit']['author']['date'].split('T')[0], '%Y-%m-%d').date()

            if key not in daily_activity:
                daily_activity[key] = {'commits': 0, 'authors': set()}

            daily_activity[key]['commits'] += 1
            daily_activity[key]['authors'].add(activity['commit']['author']['name'])

        return mapping_activity(repo, daily_activity)

    async def start(self):
        logger.debug('Trying to get old top from db')
        self.old_top = await self._get_old_top()
        logger.debug('Success')
        logger.debug('Trying to parse repositories')
        new_top = await self._parse_repos(headers)
        logger.debug('Success')

        try:
            logger.debug('Trying to save repositories')
            if len(self.old_top) == 0:
                logger.debug('Create top')
                await self.repository.create_repos(new_top)
                logger.debug('Success')
            else:
                logger.debug('Update top')
                await self._update_top(self.old_top, new_top)
                await self.repository.update_repos(new_top)
                logger.debug('Success')
        except Exception as ex:
            logger.exception(ex)
            raise ex

        repos_names = [repo.repo for repo in new_top]
        try:
            logger.debug('Trying to get old repositories activities')
            self.old_repo_activities = await self._get_old_repos_activities()

        except Exception as ex:
            logger.exception(ex)
            raise ex
        logger.debug('Success')

        logger.debug('Trying to parse repositories commits')
        repos_activities = await self._parse_repos_activities(repos_names, headers)
        logger.debug('Success')

        try:
            logger.debug('Trying to save repositories activities')
            await self.repository.save_activities(repos_activities)
            logger.debug('Success')
        except Exception as ex:
            logger.exception(ex)
            raise ex
