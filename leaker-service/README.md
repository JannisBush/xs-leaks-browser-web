# Leaker service

## Attack page generator (APG)

- Generate attack pages for a wanted URL and a wanted inclusion method (several leak methods are used at once; some leak methods need special care).
- Get the attack page from `http://172.17.0.1:8001/apg/<inc_method>/?<params>`. 
- Additional query parameters: 
    - `url`: url that should be included on the site
    - `hash`: hash segment of the url to be included
    - `browser`: current browser to correctly log the results
    - `version:`: browser version to correctly log the results
    - `wait_time`: time in milliseconds the page should wait (for postMessages etc.) before the results get saved
    - `headless`: whether the current browser is headless or not
    - `url_dict_version`: current url_dict_version
- Env parameter: 
    - `log_server`: url of the log_server (where the results get send to)
- See `apg/inclusion_methods.py` for a list of supported methods/src.
    - 12 normal ones 
    - 5+ experimental ones