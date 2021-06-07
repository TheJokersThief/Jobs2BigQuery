import html
from markdownify import markdownify as md
from typing import List

from jobs2bigquery.joblistings import BaseListing, Listing


class IntelListing(BaseListing):
    LISTING_URL = "https://jobs.intel.com/ListJobs"
    JOB_URL = "https://jobs.intel.com/ShowJob/Id/{job_id}/{job_title}"

    def get_jobs(self) -> List[Listing]:
        listings = self.reqs.get(self.LISTING_URL).json()['Data']
        return [
            Listing(
                company=self.company_id,
                url=self.JOB_URL.format(job_id=listing['JobID'], job_title=listing['JobTitle']),
                content=md(html.unescape(listing['JobDescription'])),
                location=[", ".join([listing['City'], listing['State'], listing['Country']])],
                department=[listing['JobCodeDescription']],
                last_updated=listing['UpdatedOn'], title=listing['OriginalJobTitle'].strip()
            ).__dict__
            for listing in listings
        ]
