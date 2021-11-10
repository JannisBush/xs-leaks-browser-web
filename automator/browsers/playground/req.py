import requests
import os
LOG_URL = "http://localhost:8002/dbserver/v2/"

r = requests.post(LOG_URL, json={
    "browser": {
        "browser": "aa",
        "version": "aa",
        "headless": "True"
    },
    "test": {
        "test_url": "aaa",
        "inc_method": "uuu",
        "url_dict_version": "eee"
    },
    "loading_time": 1000,
    "timed_out": True,
    "apg_url": "http://172.17.0.1:8001/apg/audio/?url=https://172.17.0.1:44300/leaks/17920/noauth/&browser=MicrosoftEdge&version=91.0.864.1&wait_time=500&headless=False",
    "events": {
        "event_list": ["aaa"],
        "event_set": ["aaa"]
    },
    "gp": {
        'gp_window_onerror': [], 
        'gp_window_onblur': 'undefined', 
        'gp_window_postMessage': [], 
        'gp_window_getComputedStyle': {'H1': 'rgb(0, 0, 0)'}, 
        'gp_window_hasOwnProperty': {'a': 'Var a does not exist'}, 
        'gp_download_bar_height': -44, 
        'gp_securitypolicyviolation': 'undefined',
    },
    "op": {
        'op_frame_count': 'undefined', 
        'op_win_window': 'undefined', 
        'op_win_CSS2Properties': 'undefined', 
        'op_win_origin': 'undefined', 
        'op_win_opener': 'undefined', 
        'op_el_height': 'undefined', 
        'op_el_width': 'undefined', 
        'op_el_naturalHeight': 'undefined', 
        'op_el_naturalWidth': 'undefined', 
        'op_el_videoWidth': 'undefined', 
        'op_el_videoHeight': 'undefined', 
        'op_el_duration': 'undefined', 
        'op_el_networkState': 'undefined', 
        'op_el_readyState': 'undefined', 
        'op_el_buffered': 'undefined', 
        'op_el_paused': 'undefined', 
        'op_el_seekable': 'undefined', 
        'op_el_sheet': 'undefined', 
        'op_el_media_error': 'undefined',
    }
})
print(r.text)