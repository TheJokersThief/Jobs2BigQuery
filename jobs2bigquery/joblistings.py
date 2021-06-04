from abc import ABC, abstractmethod
from dataclasses import dataclass

from jobs2bigquery.http import HTTPRequests


@dataclass
class Listing(object):
    title: str
    url: str
    content: str
    locations: list[str]
    departments: list[str]

    last_updated: str = None


class BaseListing(ABC):
    def __init__(self, url) -> None:
        self.url = url
        self.reqs = HTTPRequests()

    @abstractmethod
    def get_jobs(self) -> list[Listing]:
        pass


class GreenHouseListing(BaseListing):
    LISTING_URL = "https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs?content=true"

    def get_jobs(self) -> list[Listing]:
        listings = self.reqs.get(self.LISTING_URL.format(company_id=self.url)).json()
        return [
            Listing(
                url=listing['absolute_url'], content=listing['content'],
                locations=[loc['name'] for loc in listing['locations']],
                departments=[dep['name'] for dep in listing['departments']]
            )
            for listing in listings
        ]
