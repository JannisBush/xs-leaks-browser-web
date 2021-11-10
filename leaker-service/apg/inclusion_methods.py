inclusion_methods = {
    "script": {
        "inc_tag": "script",
        "inc_src": "src",
    },
    "link-stylesheet": {
        "inc_tag": "link",
        "inc_src": "href",
        "extra": "rel=stylesheet",
    },
    "link-prefetch": {
        "inc_tag": "link",
        "inc_src": "href",
        "extra": "rel=prefetch",
    },
    "img": {
        "inc_tag": "img",
        "inc_src": "src",
    },
    "iframe": {
        "inc_tag": "iframe",
        "inc_src": "src",
    },
    "video": {
        "inc_tag": "video",
        "inc_src": "src",
    },
    "audio": {
        "inc_tag": "audio",
        "inc_src": "src",
    },
    "object": {
        "inc_tag": "object",
        "inc_src": "data",
        # Ignored by all browsers?
        # If plugin not supported, browsers fail differently and list of supported plugins is not the same
        #"extra": "type=application/x-shockwave-flash", 
    },
    "embed": {
        "inc_tag": "embed",
        "inc_src": "src",
    },
    "embed-img": {
        "inc_tag": "embed",
        "inc_src": "src",
        # Try different types?; Firefox seems to ignore them?, chromium throws error events for the wrong type? (only works for image?)
        # For unsupported plugins chromium shows "plugin unsupported", firefox fails silently (test this in an independent test?)
        "extra": "type=image/jpg", 
    },
    "window.open": {

    },
    # Can detect server-side (3XX) and client-side (meta-refresh, window.location) redirects (framing protections protect, but does not matter)
    "iframe-csp": {
        "inc_tag": "iframe",
        "inc_src": "src",
        "csp": "default-src 'self' 'unsafe-inline' <log_url> <test_url>",
    },

    #########################
    # Experimental ones below
    # Only works in chrome (onerror if ressource is not an image?), everthing else is always empty video? (directly using img leaks more info?)
    "video-poster": {
        "inc_tag": "video",
        "inc_src": "poster",
    },
    # The following three need some extra setup in `attack_page.html` as they need to be nested elements
    # Does not work as tracks can only be used with `crossorigin` and ACAO (also needs some setup with a video)
    # "track": {
    #     "inc_tag": "track",
    #     "inc_src": "src",
    # },
    # Can only be used to detect if a resource is valid audio/video (onerror thrown otherwise), type is "ignored" (directly using audio/video leaks more information)
    # "source": {
    #     "inc_tag": "source",
    #     "inc_src": "src",
    #     "extra": "type=video/mp4"
    # },
    # Can only be used to detect if a resource is a valid image (img fallback used instead, can leak data with js disabled) (directly using img tag leaks more information)
    # "source-pic" : {
    #     "inc_tag": "source",
    #     "inc_src": "srcset",
    #     "extra": "type=image/jpg media=(min-width:600px)",
    # }
    # Leaks the same information as img?
    "input": {
        "inc_tag": "input",
        "inc_src": "src",
        "extra": "type=image",
    },
    # In Chrome, this can leak error status codes vs non-error status codes, also non-std status codes (firefox always fires load)
    "link-preload": {
        "inc_tag": "link",
        "inc_src": "href",
        "extra": "rel=preload as=script" # as attribute does not make a difference for XS-leaks? https://developer.mozilla.org/en-US/docs/Web/HTML/Link_types/preload
    },
    # Does not do anything observable (not implemted in firefox, NoState prefetch in chrome)
    "link-prerender": {
        "inc_tag": "link",
        "inc_src": "href",
        "extra": "rel=prerender",   
    },
    # Needs ACAO and javascript mime type (then it can diff status codes in chrome, 3XX also fail)
    "link-modulepreload": {
        "inc_tag": "link",
        "inc_src": "href",
        "extra": "rel=modulepreload",
    },
    # rel=import; deprecated and removed (does not work anymore, but somewhat strange behavior)
}
