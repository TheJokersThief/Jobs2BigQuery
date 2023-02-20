import requests
from urllib3.util import Retry


class HTTPSession(requests.Session):
    """
    Wrap a regular session to use a base URL and add a user-agent header
    """
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0"

    def __init__(self, prefix_url=None, user_agent=None, *args, **kwargs):
        super(HTTPSession, self).__init__(*args, **kwargs)
        self.prefix_url = prefix_url

        if not user_agent:
            user_agent = HTTPSession.DEFAULT_USER_AGENT

        self.headers.update({'User-Agent': user_agent, 'Accept': 'application/json'})


class HTTPRequests():

    def __init__(self, user_agent=None, enable_retries=True):
        self.site = HTTPSession(user_agent=user_agent)

        if enable_retries:
            retry_strategy = Retry(
                total=3,
                status_forcelist=[500, 502, 503, 504],
                backoff_factor=0.1
            )
            adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
            self.site.mount("https://", adapter)

    def get(self, url, params=None):
        req = self.site.get(url, params=params)
        req.raise_for_status()
        return req

    def post(self, url, data=None):
        req = self.site.post(url, json=data)
        req.raise_for_status()
        return req
