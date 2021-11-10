# Leaky service

Application that can echo wanted content and leak according to our needs.

## echo app
- Available at: http://172.17.0.1:8000/echo/ and https://172.17.0.1:44300/echo/
- Echos what you want, specified in GET (query) or POST (body) parameters, some settings do not work in query parameters as they contain forbidden chars
- GET takes precendence and if there are several params of the same name the first is used
- Example: http://172.17.0.1:8000/echo/?ecohd_status=404&X-Frame-Options=deny
- Supported values:
    - Delay: `ecodly=<delay in milliseconds>` 
    - Status Code: `ecohd_status=<status code>` (Code has to be between 200 and 999; Django limitation)
    - Body Content:
        - Html: `ecocnt_html=<details>`
            - `meta_refresh=<your content>`
            - `num_frames=<num of wanted frames>`
            - `div_id=<id you want to include in the dom on a div>`
            - `post_message=<content of postMessage sent to parent and opener>`
            - Example: `ecocnt_html=meta_refresh=0;url=http://test.com?url=abc&abc=abc,num_frames=5,div_id=try,post_message=hi"aa'`
        - CSS: `ecocnt_css=<css-content>`
            - Example: `ecocnt_css=p {color: red;}`
        - JS: `ecocnt_js=<js-content>`
            - Example: `ecocnt_js=var a=5;`
        - Image: `ecocnt_img=<img-specs>`
            - `height=<pixel>`
            - `width=<pixel>`
            - `type=<img type>`
            - Example: `ecocnt_img=width=200,height=300,type=png`
        - Video: `ecocnt_vid=<vid-specs>` (only mp4 supported)
            - `width=<pixel>` (Currently only 50 and 100 supported)
            - `height=<pixel>` (Currently only 50 and 100 supported)
            - `duration=<seconds>` (Currently only 1 and 2 supported)
            - Example: `ecocnt_vid=width=100,height=100,duration=2`
        - Audio: `ecocnt_audio=<audio-specs>` (only wav supported)
            - `duration=<seconds>` (Currently only 1 and 2 supported)
            - Example: `ecocnt_audio=duration=1`
    - Headers:
        - Just specify with `<wanted-header>=<wanted content>`
        - Example: `Content-Security-Policy=default-src 'self'; img-src * media-src media1.com media2.com; script-src userscripts.example.com`

## leaks app
- Leaky application, uses echo and the `url_dict` file.
- URL: `http://172.17.0.1:8000/leaks/<number in url_dict>/<auth_status>/`
    - Example: http://172.17.0.1:8000/leaks/525311/noauth/
- Possibility to check `SameSite` settings:
    - Quick abort: if `auth_status` == `auth` and request is not authenticated
    - Login: `leaks/login/`
    - Logout: `leaks/logout/`
    - Test Login: `leaks/test/` (Title should contain success if login was succesful)
- Details about the url_dict:
    - Get the version: `leaks/get_ver/`
    - Save everything in the postgres database (Warning this can take quite some time): `leaks/save_dict/`
    - Get info for one id: `leaks/get_info/<url_id>/?url_dict_version=<optionally specify url dict version here>`

## Additional content
### file_creator.py
- Can be used to create the wanted audio and video files

### url_creator.py
- Create all (necessary) combinations of headers and bodies we want to test and saves them in a dictionary (numbered), saved in `url_dict.pickle`
- How many combinations do we have?
    - 11+ individual inclusions [details here](../leaker-service/README.md)
        - possible to run several of them in one file/test? (do they interfere?) (small scale test to test this?)
    - 3+ Browsers 
    - 1+ Server Settings 
        - test without cookies == None, Secure (behavior wise)
        - for SameSite settings do not run an extensive test, just check for every inclusion method if cookies are attached or not on the ServerSide using one request for all methods
    - The actual URLs/endpoints (currently: 387072)
        - Content body variations (12)
            - empty (1)
            - html (4)
            - css (1)
            - js (2)
            - img (1) (we reduced to 1? for all media types if we use non default values; if we can read them, we can read all values)
            - vid (1) 
            - audio (1)
            - pdf (1)
            - additional interesting bodies (0+)
        - Headers&co (32256) 
            - the count always include not set, if possible
            - we excluded some default values or other irrelevant values (for the lookup later we need to add/merge these values again!)
            - Status codes (63) (this depends on the python version!)
            - XCTO (2)
            - XFO (2)
            - CT (8)
            - CD (2)
            - CORP (2)
            - COOP (2)
            - COEP (0) (only concerns embedding not being embedded?)
            - Location (2)
            - Additional interesting headers (cors, csp, ...)