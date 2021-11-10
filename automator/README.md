# Leaker - BrowserAutomater with Selenium

- `get_abstract.py`:
    - Abstract interface all modes need to support.
    - Needs `caps` a dictionary with info on all the supported browsers. Dict needs numeric keys (0..n) and the capability info as values (either Options or DesiredCapabilities)
    - Instatiations need to overwrite `get_driver(self, cap_id)` and return a selenium driver object for the specified browser
- `get_local_grid.py`:
    - Specify the local grid URL in the `.env` file
    - Specify the supported browsers in the file
    - Run `docker-compose up`
- `get_browserstack.py`:
    - Specify your BrowserStack credentials in `.env`
    - Specify your wanted browsers and settings in the file
    - If you want to test local URLs, run `./BrowserStackLocal`
- `get_local_tor.py`:
    - Need tor installed `apt install tor`
    - Need geckodriver and tor browser installed
    - Specify the paths to them in `.env`
- `test_browsers.py`:
    - Actual automation code is here
