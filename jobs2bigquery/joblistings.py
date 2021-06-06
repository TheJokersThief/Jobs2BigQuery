import html
import requests
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from markdownify import markdownify as md
from typing import List
from urllib.parse import urljoin

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
        listings = []
        next_page = self.LISTING_URL.format(company_id=self.company_id)
        while next_page:
            results = self.reqs.get(next_page).json()
            next_page = results['nextPage']
            listings.extend(results['jobs'])

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


class WorkableListing(BaseListing):
    LISTING_URL = "https://apply.workable.com/api/v1/widget/accounts/{company_id}?details=true"

    def get_jobs(self) -> List[Listing]:
        listings = self.reqs.get(self.LISTING_URL.format(company_id=self.company_id)).json()['jobs']
        return [
            Listing(
                company=self.company_id,
                url=listing['url'], content=md(listing['description']),
                location=[f"{listing['city']}, {listing['state']}, {listing['country']}"],
                department=[listing['department']],
                last_updated=listing['published_on'] + " 00:00", title=listing['title'].strip()
            ).__dict__
            for listing in listings
        ]


class WorkdayListing(BaseListing):
    def __init__(self, company_id, jobs_url) -> None:
        super().__init__(company_id)
        self.jobs_url = jobs_url

    def get_jobs(self) -> List[Listing]:
        listings = []
        for listing in self.get_all_job_listings():
            job_age = listing['subtitles'][2]['instances'][0]['text']
            if job_age == "Posted 30+ Days Ago":
                # If it's over 30 days old, we can't determine its date so we don't record those jobs
                continue

            job_url = urljoin(self.jobs_url, listing['title']['commandLink'])

            # If today, the datetime is now
            job_date = datetime.now()
            if job_age != "Posted Today":
                if job_age == "Posted Yesterday":
                    job_age = 1  # If "Yesterday", the age is 1 day
                else:
                    # If it's not today, and it's not yesterday then it must be some other day!
                    #                                           - Dr. Seuss, Computer Scientist
                    job_age = int(job_age.replace('Posted ', '').replace(' Days Ago', ''))
                job_date = datetime.now() - timedelta(days=job_age)
            job_date = job_date.strftime('%Y-%m-%d 00:00')

            listings.append(
                Listing(
                    company=self.company_id, url=job_url, content=None,
                    location=[listing['subtitles'][1]['instances'][0]['text']], department=[""],
                    last_updated=job_date, title=listing['title']['instances'][0]['text']
                ).__dict__
            )

        return listings

    def get_all_job_listings(self) -> list:
        listings = []
        next_page_url = self.jobs_url
        while next_page_url:
            try:
                results = self.reqs.get(next_page_url)
                results = results.json()
                listings.extend(results['body']['children'][0]['children'][0]['listItems'])

                endpoints = results['body']['children'][0]['endPoints']
                for endpoint in endpoints:
                    if endpoint['type'] == 'Pagination':
                        next_page_url = urljoin(self.jobs_url, endpoint['uri']) + "/" + str(len(listings))
                        break
            except requests.exceptions.HTTPError as e:
                # If the response was a 404, there's no more results, else it's a real error
                if e.response.status_code == 404:
                    next_page_url = None
                else:
                    raise e
        return listings
