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
        print(f"Processing Jobs For: {company_id}")

    @abstractmethod
    def get_jobs(self) -> List[Listing]:
        pass

    def check_url(self) -> bool:
        if hasattr(self, "LISTING_URL") and self.LISTING_URL:
            try:
                resp = self.reqs.get(self.LISTING_URL.format(company_id=self.company_id))
                return resp.status_code == 200
            except requests.exceptions.HTTPError as e:
                return e.response.status_code == 200


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
            if "location" in listing['categories']
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
                department=[listing['category'] or "None"],
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
                department=[listing['department'] or "None"],
                last_updated=listing['published_on'] + " 00:00", title=listing['title'].strip()
            ).__dict__
            for listing in listings
        ]


class RecruiteeListing(BaseListing):
    LISTING_URL = "https://{company_id}.recruitee.com/api/offers/"

    def get_jobs(self) -> List[Listing]:
        listings = self.reqs.get(self.LISTING_URL.format(company_id=self.company_id)).json()['offers']
        return [
            Listing(
                company=self.company_id,
                url=listing['careers_url'], content=md(listing['description']),
                location=[listing['location']],
                department=[listing['department'] or "None"],
                last_updated=listing['created_at'], title=listing['title'].strip()
            ).__dict__
            for listing in listings
        ]


class WorkdayListing(BaseListing):
    def __init__(self, company_id, jobs_url) -> None:
        super().__init__(company_id)
        self.jobs_url = jobs_url

    def get_jobs(self) -> List[Listing]:
        listings = []
        for listing in self._get_all_job_listings():
            job_age = listing['postedOn']

            if job_age == "Posted 30+ Days Ago" or not job_age:
                # If it's over 30 days old, we can't determine its date so we don't record those jobs
                continue

            job_url = urljoin(self.jobs_url, listing['externalPath'])

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
                    location=[listing['locationsText']], department=["None"],
                    last_updated=job_date, title=listing['title']
                ).__dict__
            )

        return listings

    def _get_all_job_listings(self) -> list:
        listings = []

        *url_pieces, final_piece = self.jobs_url.split('/')
        url = urljoin('/'.join(url_pieces), f"/wday/cxs/{self.company_id}/{final_piece}/jobs")

        next_page_url = url
        offset = 0
        per_page = 20
        total = 999
        while total >= offset:
            results = self.reqs.post(next_page_url, data={'searchText': '', 'offset': offset})
            results = results.json()

            jobs = results['jobPostings']
            total = results['total']

            listings.extend(jobs)
            offset += per_page

        return listings


class SmartRecruiterListing(BaseListing):
    LISTING_URL = "https://api.smartrecruiters.com/v1/companies/{company_id}/postings"

    def get_jobs(self) -> List[Listing]:
        listings = []
        url = self.LISTING_URL.format(company_id=self.company_id)
        stop_running = False
        while not stop_running:
            results = self.reqs.get(url, params={'offset': len(listings)}).json()
            listings.extend(results['content'])

            if len(listings) >= results['totalFound']:
                stop_running = True

        return [
            Listing(
                company=self.company_id,
                url=listing['ref'], content=None,
                location=[
                    f"{listing['location']['city']}, {listing['location']['country']}"
                    + " Remote" if listing['location']['remote'] else ""
                ],
                department=[listing['department'].get('label', "None")],
                last_updated=listing['releasedDate'], title=listing['name'].strip()
            ).__dict__
            for listing in listings
        ]


class ComeetListing(BaseListing):
    LISTING_URL_TMPL = "https://www.comeet.co/careers-api/2.0/company/{company_id}/positions?token={token}"

    def __init__(self, company_name, company_id, token) -> None:
        super().__init__(company_name)
        self.company_name = company_name
        self.company_id = company_id
        self.token = token
        self.LISTING_URL = self.LISTING_URL_TMPL.format(
                company_id=self.company_id,
                token=self.token,
            )

    def get_jobs(self) -> List[Listing]:
        listings = self.reqs.get(self.LISTING_URL).json()
        return [
            Listing(
                company=self.company_name,
                url=listing['url_comeet_hosted_page'], content="None",
                location=[listing['location']['name'] if listing['location'] is not None else "None"],
                department=[listing['department'] or "None"],
                last_updated=listing['time_updated'], title=listing['name'].strip()
            ).__dict__
            for listing in listings
        ]
