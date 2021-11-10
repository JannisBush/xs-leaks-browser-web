import os

from selenium import webdriver
from selenium.webdriver import Chrome
from get_abstract import Browsers


chrome_path = os.getenv("LOCAL_CHROME_PATH")
chromedriver_path = os.getenv("LOCAL_CHROMEDRIVER_PATH")


# Capabilities vs Options are confusing and the names also change depending on versions etc.
chrome_options = webdriver.ChromeOptions()
#chrome_options.headless = True
chrome_options.binary_location = chrome_path
chrome_options.set_capability("acceptInsecureCerts", True)


caps = {
    0: chrome_options,
}

parallel_caps = {
    0: 1,
}

parallel_limit = sum(parallel_caps.values())

class BrowserChrome(Browsers):

    def __init__(self, parallel_caps=parallel_caps):
        super().__init__(caps=caps, parallel_limit=parallel_limit)
        self.parallel_caps = parallel_caps

    def get_parallel_limit_cap(self, cap_id):
        assert type(cap_id) == int, "Cap_id has to be an int"
        assert cap_id >= 0, "Cap_id is too small"
        assert cap_id <= self.max_id, "Cap_id is too large"
        return self.parallel_caps[cap_id]

    def get_driver(self, cap_id):
        super().get_driver(cap_id)
        return webdriver.Chrome(
            chromedriver_path,
            chrome_options=self.caps[cap_id])