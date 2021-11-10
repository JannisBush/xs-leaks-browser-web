import os

from selenium import webdriver

from get_abstract import Browsers


# Find a list of all available Browsers and settings here: https://www.browserstack.com/automate/capabilities
# Use W3C Protocol
caps = {

    # 0: {
    #     'bstack:options': {
    #         "os": "OS X",
    #         "osVersion": "Big Sur",
    #         "local": "true",
    #         "projectName" : "xs-leaks",
    #         "buildName" : "run1",
    #         "sessionName" : "safari", 
    #         # "debug": "true",
    #         # "consoleLogs": "verbose",
    #         # "networkLogs": "true",
    #         # "video": "false",
    #     },
    #     "browserName": "Safari",
    #     "browserVersion": "14.0",
    # },
    0: {
        'bstack:options' : {
            "os" : "Windows",
            "osVersion" : "10",
            "projectName" : "xs-leaks",
            "buildName" : "run1",
            "sessionName" : "chrome",
            "local" : "true",
            "seleniumVersion" : "4.0.0-beta-2",
        },
        "browserName" : "Chrome",
        "browserVersion" : "latest",
        },
    1: {
    'bstack:options' : {
        "os" : "Windows",
        "osVersion" : "10",
        "projectName" : "xs-leaks",
        "buildName" : "run1",
        "sessionName" : "firefox",
        "local" : "true",
        "seleniumVersion" : "3.10.0",
    },
    "browserName" : "Firefox",
    "browserVersion" : "latest",
    } 

}

username = os.getenv("BROWSERSTACK_USERNAME")
access_key = os.getenv("BROWSERSTACK_ACCESS_KEY")
parallel_limit = int(os.getenv("BROWSER_STACK_PARALLEL"))


class BrowserStack(Browsers):
    def __init__(self):
        super().__init__(caps=caps, parallel_limit=parallel_limit)

    def get_driver(self, cap_id):
        super().get_driver(cap_id)
        return webdriver.Remote(
            command_executor=f"https://{username}:{access_key}@hub-cloud.browserstack.com/wd/hub",
            desired_capabilities=self.caps[cap_id])


old_caps = {
    0: {
        "os": "OS X",
        "os_version": "Big Sur",
        "browser": "Safari",
        "browser_version": "14.0",
        "name": "Parallel Test1",
        "build": "browserstack-xs-leak",
        # enable localhost (need to run ./BrowserStackLocal)
        "browserstack.local": "false",  # "true",
        # "browserstack.debug": "true",  # for enabling visual logs
        # "browserstack.console": "verbose",  # to enable console logs at the info level. You can also use other log levels here
        # "browserstack.networkLogs": "true"  # to enable network logs to be logged
        # "browserstack.video" : "false"  # disable the video recording
    },
}
