import itertools
import sys
import os
from http import HTTPStatus


url_dict = {
    1: {
        'content-type': ['application/javascript'],
        'Content-Security-Policy': ["default-src 'self'; img-src *; media-src media1.com media2.com; script-src userscripts.example.com"],
        'Cross-Origin-Opener-Policy': ['unsafe-none'],
        'Cross-Origin-Resource-Policy': ['same-site'],
        'X-Frame-Options': ['deny'],
        'X-Content-Type-Options': ['no-sniff'],
        'Content-Disposition': ['inline'],
        'Location': ['http://test.dev'],
        'ecocnt_html': ['meta_refresh=0;url=http://test.com?url=abc&abc=abc,num_frames=5,div_id=try,post_message=hi"aa\''],
        'ecohd_status': ['404'],
        'ecodly': ['100'],
    }
}

# Need a local URL to redirect to
redirect_url = os.getenv("REDIRECT_URL")
if redirect_url is None:
    sys.exit("REDIRECT_URL not defined")

resource_dict = {
    'content': {
        'ecocnt_html': [
            'num_frames=1,input_id=test1',
            'num_frames=2',
            'post_message=mes1', # num_frames 0
            f"meta_refresh=0;{redirect_url}",
        ],
        'ecocnt_css': [
            'h1 {color: blue}',  # Rule A
            #'h1 {color: red}'  # Rule B (reading one rule is enough)
        ],
        'ecocnt_js': [
            '.,,.',  # Syntax Error
            'var a=5;',  # Global var with value 1
            #'var a=6;',  # Global var with value 2 (reading one value is enough)
            # add more complicated stuff?
        ],
        'ecocnt_img': [
            'width=50,height=50,type=png',
            #'width=100,height=100,type=png'
        ],
        'ecocnt_vid': [
            #'width=50,height=50,duration=1',
            #'width=50,height=50,duration=2',
            #'width=100,height=100,duration=1',
            'width=100,height=100,duration=2',
        ],
        'ecocnt_audio': [
            'duration=1',
            #'duration=2',
        ],
        'ecocnt_pdf': [
            'a=a',
        ],
        'empty': None
        # add others (e.g., pdf later)
    },
    'headers': {
        'ecohd_status':
            # All status codes according to iana + one non-standard one (62+1)
            # https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml
            # Do not use all, because there are too many?
            [
                code.value for code in HTTPStatus
                #'100', '101', '200', '300', '301', '302', '303', '307', '308',
                #'400', '401', '402', '403', '404',
                #'500', '501', '502', '503'
            ]
        + ['999'],
        # https://developer.mozilla.org/de/docs/Web/HTTP/Headers/X-Content-Type-Options
        'X-Content-Type-Options': [
            'nosniff',
            None,
            # invalid?
            ],
        # https://developer.mozilla.org/de/docs/Web/HTTP/Headers/X-Frame-Options
        'X-Frame-Options': [
            'deny',
            None,
            # invalid?,
            #'sameorigin', #?
            # allow from?
        ],  
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        # https://www.iana.org/assignments/media-types/media-types.xhtml
        'Content-Type': [
            'text/html',
            'text/css',
            'application/javascript',
            'video/mp4', 
            'audio/wav',
            'image/png',
            'application/pdf',
            #'application/octet-stream',
            #'text/plain',
            #'text/javascript',
            None,
            # Add other ones? Which ones?
        ],
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition
        'Content-Disposition': [
            #'inline',
            'attachment',
            # 'attachment; filename="bad.exe"',
            None,
        ],
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Resource-Policy
        'Cross-Origin-Resource-Policy': [
            'same-origin',
            #'cross-origin',
            None,
            #'same-site' # we do not care about same-site/same-origin differences?
        ],
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Opener-Policy
        'Cross-Origin-Opener-Policy': [
            'same-origin',
            None, 
            #'unsafe-none', # default for now
            #'same-origin-allow-popups',
        ],
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Embedder-Policy
        'Cross-Origin-Embedder-Policy': [
            #'unsafe-none', # default
            #'require-corp',
            None,
        ], 
        'Location': [
            redirect_url, # Local CrossOrigin URL to gurantee fast loading time (db_server, leaker, and leaky are already allowed by CSP, so another URL is necessary)
            #'/relative', # interesting to check which methods can detect SameOrigin redirects and which methods can only detect CrossOrigin redirects (or SameSite CrossOrigin)
            None, 
        ]

        # other headers might be intersting too?
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Timing-Allow-Origin
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Origin
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Server-Timing

    },
    'special': {
        # Extra time the server needs for processing
        'ecodly': ['0', '50', '100'],
        # Location for redirect? 
        'location': [redirect_url]
    }
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Not enough parametern. Specify preview or create")
    mode = sys.argv[1]
    
    if mode == "create":
        url_dict = {}
        id_number = 0
        header_num = 0
        headers = resource_dict['headers'].keys()
        print(len(resource_dict['headers']['ecohd_status']))
        for vals in itertools.product(*resource_dict['headers'].values()):
            header_dict = {}
            header_num += 1
            for header, val in zip(headers, vals):
                if val is not None:
                    header_dict[header] = [val]   
            
            
            for content_option, content_values in resource_dict['content'].items():
                url = {}
                if content_values is None:
                    url_dict[id_number] = header_dict
                    id_number += 1
                elif type(content_values) == list:
                    for val in content_values:
                        header_dict_copy = header_dict.copy()
                        header_dict_copy[content_option] = [val]
                        url_dict[id_number] = header_dict_copy
                        id_number += 1
                elif type(content_values) == dict:
                    keys = content_values.keys()
                    for vals in itertools.product(*content_values.values()):
                        header_dict_copy = header_dict.copy()
                        entries = []
                        for key, val in zip(keys, vals):
                            if val is not None:
                                entries.append(f"{key}={val}")
                        if len(entries) != 0:
                            header_dict_copy[content_option] = [','.join(entries)]
                            url_dict[id_number] = header_dict_copy
                            id_number += 1
                else:
                    print("Error:")
                    print(type(content_values))
        
        length = len(url_dict)
        print(length)
        print(id_number)
        print(header_num)
        
        # Generate version info
        import uuid
        version = f"1.{uuid.uuid4()}.{length}"
        print(version) 
        url_dict["version"] = version


        import pickle
        try:
            with open("url_dict.pickle", "rb") as f:
                url_dict_old = pickle.load(f)
                ver = url_dict_old.get("version")
                with open(f"url_dict.{ver}.pickle", "wb") as f:
                    pickle.dump(url_dict_old,f)
        except Exception as e:
            print(e)

        with open('url_dict.pickle', 'wb') as f:
            pickle.dump(url_dict, f)
    
    elif mode == "preview":
        pass

    else: 
        sys.exit("Invalid mode. Specify create or preview")
