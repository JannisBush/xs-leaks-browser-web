import os

from selenium import webdriver
from selenium.webdriver.opera.options import Options as OperaOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from get_abstract import Browsers

# Capabilities vs Options are confusing and the names also change depending on versions etc.
chrome_options = webdriver.ChromeOptions()
#chrome_options.headless = True # (do not use headless mode to enable download bar detection?)
chrome_options.set_capability("browser_version", "89.0.4389.90")  # Does not work? Or does not fail if not available only? (or works only for some selenium versions)
chrome_options.set_capability("acceptInsecureCerts", True)

firefox_options = webdriver.FirefoxOptions()
firefox_options.set_capability("acceptInsecureCerts", True)
#firefox_options.headless = True

opera_options = OperaOptions()
opera_options.set_capability("acceptInsecureCerts", True)
# opera_options.headless = True # does not work for some reason

edge_options = EdgeOptions()
edge_options.set_capability("acceptInsecureCerts", True)
#edge_options.headless = True # Does not work with selenium 3?, use selenium 4! (extra env for tor with selenium 3)
#edge_options.set_capability("platform", "LINUX") # Necessary for selenium 3, not allowed for dynamic grid?

browser_to_cap = {
        "chrome": 0,
        "firefox": 1,
        "edge": 2,
        # "opera": 3,
}

caps = {
    0: chrome_options,
    1: firefox_options,
    2: edge_options,    
    #3: opera_options,
}

parallel_caps = {
    0: 35,
    1: 35,
    2: 35,
    #3: 0, # Opera does not support W3C/Selenium 4
}

parallel_limit = 45 # sum(parallel_caps.values())
# Enhancement query the caps dynamically from the grid?

grid_url = os.getenv("LOCAL_GRID_URL")

class BrowserGrid(Browsers):

    def __init__(self, grid_url=grid_url, parallel_caps=parallel_caps):
        super().__init__(caps=caps, parallel_limit=parallel_limit)
        self.parallel_caps = parallel_caps
        self.grid_url = grid_url

    def get_parallel_limit_cap(self, cap_id):
        assert type(cap_id) == int, "Cap_id has to be an int"
        assert cap_id >= 0, "Cap_id is too small"
        assert cap_id <= self.max_id, "Cap_id is too large"
        return self.parallel_caps[cap_id]

    def get_driver(self, cap_id):
        super().get_driver(cap_id)
        return webdriver.Remote(
            command_executor=self.grid_url,
            options=self.caps[cap_id])
