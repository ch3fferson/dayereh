import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class Fetcher:

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )

    def __init__(self, timeout: int = 15, enable_browser: bool = False):
        self.timeout = timeout
        self.driver = None

        self.session = self._create_session()

        if enable_browser:
            self.driver = self._create_driver()

    def _create_session(self) -> requests.Session:
        session = requests.Session()

        session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
        )

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=False,
        )

        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=retry,
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _create_driver(self):
        options = Options()

        options.add_argument("--headless=new")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=en-US")
        options.add_argument(f"--user-agent={self.USER_AGENT}")

        options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation"],
        )
        options.add_experimental_option(
            "useAutomationExtension",
            False,
        )

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {
                "userAgent": self.USER_AGENT,
                "platform": "Windows",
            },
        )

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
Object.defineProperty(navigator,'platform',{get:()=>'Win32'});
Object.defineProperty(navigator,'language',{get:()=>'en-US'});
Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});
"""
            },
        )

        return driver

    def _wait(self):
        WebDriverWait(
            self.driver,
            self.timeout,
        ).until(
            lambda d: d.execute_script(
                "return document.readyState"
            )
            == "complete"
        )

    def get_text_by_selenium_by_css(
        self,
        url: str,
        css_selector_visibility_element: str = "body",
    ) -> str:
        if not self.driver:
            raise RuntimeError("Browser is disabled")

        self.driver.get(url)
        self._wait()

        WebDriverWait(
            self.driver,
            self.timeout,
        ).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, css_selector_visibility_element)
            )
        )

        return self.driver.page_source

    def get_text_by_selenium_by_xpath(
        self,
        url: str,
        xpath_visibility_element: str,
    ) -> str:
        if not self.driver:
            raise RuntimeError("Browser is disabled")

        self.driver.get(url)
        self._wait()

        WebDriverWait(
            self.driver,
            self.timeout,
        ).until(
            EC.visibility_of_element_located(
                (By.XPATH, xpath_visibility_element)
            )
        )

        return self.driver.page_source

    def get_text_by_requests(self, url: str) -> str:
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text

    def get_json_by_requests(self, url: str) -> dict:
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def close(self):
        self.session.close()

        if self.driver:
            self.driver.quit()