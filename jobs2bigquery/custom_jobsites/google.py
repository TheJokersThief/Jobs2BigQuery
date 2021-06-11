import html
from markdownify import markdownify as md
from typing import List

from jobs2bigquery.joblistings import BaseListing, Listing


class GoogleListing(BaseListing):
    LISTING_URL = "https://careers.google.com/api/v3/search/"

    def get_jobs(self) -> List[Listing]:
        first_page = self.reqs.get(self.LISTING_URL).json()
        listings = first_page['jobs']
        max_pages = (first_page['count'] // first_page['page_size']) + 1
        for page in range(2, max_pages):
            results = self.reqs.get(self.LISTING_URL + f"?page={str(page)}").json()
            listings.extend(results['jobs'])

        return [
            Listing(
                company=self.company_id,
                url=listing['apply_url'], content=md(html.unescape(listing['description'])),
                location=[location['display'] for location in listing['locations']],
                department=listing['categories'],
                last_updated=listing['modified'], title=listing['title'].strip()
            ).__dict__
            for listing in listings
        ]
