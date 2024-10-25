from dataclasses import dataclass
from datetime import date

headers = {
    'Accept': 'application/vnd.github+json',
    'Authorization': 'Bearer ',
    'X-GitHub-Api-Version': '2022-11-28'
}


@dataclass
class Repo:
    repo: str
    owner: str
    position_cur: int
    position_prev: int
    stars: int
    watchers: int
    forks: int
    open_issues: int
    language: str | None


@dataclass
class Activity:
    repo: str
    date: date
    commits: int
    authors: list[str]


def mapping_repo(repo: tuple) -> Repo:
    return Repo(*repo)


def mapping_activity(repo_name: str, activity: dict[date, dict[str, int | set]]) -> list[Activity]:
    activities = []

    for k, v in activity.items():
        activities.append(Activity(repo=repo_name, date=k, commits=v['commits'], authors=list(v['authors'])))

    return activities
