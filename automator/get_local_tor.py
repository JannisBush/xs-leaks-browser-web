import os
# Requires Selenium 3.141 (does not work with selenium 4, other code works with both versions, so we just use selenium 3?)
from tbselenium.tbdriver import TorBrowserDriver

from get_abstract import Browsers



tor_browser_path = os.getenv("TOR_BROWSERPATH")
gecko_path = os.getenv("GECKO_PATH")
log_path = os.getenv("TOR_LOG")

# Supports "firefox" capabilities
caps = {
    0: {
        'tor': 'tor'
    }
}


class BrowserTor(Browsers):
    def __init__(self):
        super().__init__(caps=caps, parallel_limit=1)

    def get_driver(self, cap_id):
        super().get_driver(cap_id)
        return TorBrowserDriver(tor_browser_path, executable_path=gecko_path, headless=True, tbb_logfile_path=log_path)