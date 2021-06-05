import html
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from markdownify import markdownify as md
from typing import List

from jobs2bigquery.http import HTTPRequests


@dataclass
class Listing(object):
    company: str
    title: str
    url: str
    content: str
    location: List[str]
    department: List[str]

    last_updated: str = None
    logged_at: int = int(time.time())


class BaseListing(ABC):
    def __init__(self, company_id) -> None:
        self.company_id = company_id
        self.reqs = HTTPRequests()

    @abstractmethod
    def get_jobs(self) -> List[Listing]:
        pass


class GreenHouseListing(BaseListing):
    LISTING_URL = "https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs?content=true"

    def get_jobs(self) -> List[Listing]:
        listings = self.reqs.get(self.LISTING_URL.format(company_id=self.company_id)).json()['jobs']
        return [
            Listing(
                company=self.company_id,
                url=listing['absolute_url'], content=md(html.unescape(listing['content'])),
                location=[loc['name'] for loc in listing['offices']],
                department=[dep['name'] for dep in listing['departments']],
                last_updated=listing['updated_at'], title=listing['title'].strip()
            ).__dict__
            for listing in listings
        ]


class LeverListing(BaseListing):
    LISTING_URL = "https://api.lever.co/v0/postings/{company_id}"

    def get_jobs(self) -> List[Listing]:
        listings = self.reqs.get(self.LISTING_URL.format(company_id=self.company_id)).json()
        return [
            Listing(
                company=self.company_id,
                url=listing['hostedUrl'], content=listing['descriptionPlain'],
                location=listing['categories']['location'].split(' or '),
                department=[listing['categories']['team']],
                last_updated=listing['createdAt'] // 1000, title=listing['text'].strip()
            ).__dict__
            for listing in listings
        ]


class HireHiveListing(BaseListing):
    LISTING_URL = "https://{company_id}.hirehive.com/api/v1/jobs"

    def get_jobs(self) -> List[Listing]:
        listings = self.reqs.get(self.LISTING_URL.format(company_id=self.company_id)).json()['jobs']
        return [
            Listing(
                company=self.company_id,
                url=listing['hostedUrl'], content=listing['description']['text'],
                location=[listing['location'], listing['country']['name']],
                department=[listing['category'] or ""],
                last_updated=listing['publishedDate'], title=listing['title'].strip()
            ).__dict__
            for listing in listings
        ]
