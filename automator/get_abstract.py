from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class Browsers:
    def __init__(self, caps, parallel_limit=1):
        assert type(caps) == dict, "Caps is not a dictionary"
        assert all(type(key) == int for key in caps.keys()), "Not all keys in caps are integer"
        assert len(caps.keys()) > 0, "Empty caps"
        assert type(parallel_limit) == int, "Parallel limit has to be integer"
        assert parallel_limit >= 1, "Parralel limit has to be at least 1"
        self.caps = caps
        self.max_id = max(caps.keys())
        self.parallel_limit = parallel_limit

    def get_parallel_limit(self):
        return self.parallel_limit

    def get_parallel_limit_cap(self, cap_id):
        assert type(cap_id) == int, "Cap_id has to be an int"
        assert cap_id >= 0, "Cap_id is too small"
        assert cap_id <= self.max_id, "Cap_id is too large"
        return self.parallel_limit

    def get_caps(self):
        return self.caps

    def get_driver(self, cap_id):
        assert type(cap_id) == int, "Cap_id has to be an int"
        assert cap_id >= 0, "Cap_id is too small"
        assert cap_id <= self.max_id, "Cap_id is too large"