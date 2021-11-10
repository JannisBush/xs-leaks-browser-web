events_fired = {
    # also includes error_none and none_load? same code should work
    # also include other events eg, loadedemetadata (it will be ignored on non working tags?)
    # which events to include?    
    # Wiki: Error Events, CORP Leaks, CORB Leaks 
    'error_load_loadedmetadata_stalled_suspend': {
        'script': 'src', # EF-CtMismatchScript, EF-StatusErrorScript, EF-XctoScript
        'img': 'src', # EF-CtMismatchImg
        'iframe': 'src', # EF-StatusErrorIFrame, EF-NonStdStatusErrorIFrame, EF-CDispIFrame, EF-CDispStatErrIFrame, EF-CDispAtmntIFrame,
        'video': 'src', # EF-CtMismatchVideo
        'audio': 'src', # EF-CtMismatchAudio
        'object': 'data', # type necessary??; EF-StatusErrorObject, EF-XctoObject, EF-CtMismatchObject, EF-XfoObject
        'embed': 'src', # type necessary??; EF-StatusErrorEmbed
        'link': ['href', ['prefetch', 'stylesheet']], # also preload/prerender, different types etc!!; EF-StatusErrorLink, EF-StatusErrorLinkCss, EF-RedirLink
        # other tags: 
        # 'applet': 'code', # only works in safari
        # 'frame': 'src', # deprecated, element ignored in chrome and firefox
        # 'video': 'poster', # image shown while loading
        # 'track': 'src', # webvtt
        # 'source': 'src', # identically to audio/video?
        # 'input': 'src', # type='image'
    }   
    # Not included EF-CacheLoadCheck (check how it works) 
    # Wiki: Cache Probing with Error Events
    # Server-Side Redirect using link tags? (Wiki)
    # Count onload for redirect count iframe?

}

object_properties = {
    # Wiki: FrameCounting
    'frame_count': [
        'iframe', # OP-FrameCount
        'window.open' # OP-WindowProperty (only property that works?)
    ],
    # Wiki: Window references
    'opener_defined': [
        'iframe', # need some special care?
        'window.open'
    ],
    # height, width, naturalHeight, naturalWidth, videoWidth, videoHeight, (duration), (networkState, readyState, buffered, paused, seekable)
    'dimensions': [
        'img', # OP-ImgDimension, OP-ImgCtMismatch
        'video', # OP-VideoDimension
        'frame', # OP-WindowDimension (needs pdf?)
        'audio', # OP-MediaDuration, OP-MediaCtMismatch
    ],
    # not working anymore? bug in legacy edge
    'sheet': [
        'link', # rel=stylesheet; OP-LinkSheet, OP-LinkSheetStatusError
    ]
    # not working anymore?
    'media_error': [
        'audio',
        'video', # OP-MediaStatus
    ],
    # Wiki: detecting download navigation
    'origin': [
        'iframe',
        'window.open'
    ]
    # https://docs.google.com/presentation/d/1rlnxXUYHY9CHgCMckZsCGH4VopLo4DYMvAcOltma0og/edit#slide=id.gae7bf0b4f7_0_1244
    # max redirect (with fetch?) for detecting redirect
    # manual redirect with fetch
}

global_properties = {
    'window.onerror': [
        'script',  # COSI-JSError
    ],
    'window.onblur': [
        'iframe', # Wiki: ID attribute
    ], 
    'window.addEventListener("message")': [
        'iframe', # COSI-postMessage, Wiki: postMessage Broadcasts
        'window.open',
    ],
    'window.getComputedStyle': [
        'link', # COSI-CSSPropRead
    ],
    # (simple) XSSI
    'window.hasOwnProperty': [
        'script', # COSI-JSObjectRead
    ],
    'download_bar': [
        'window.open', # Wiki: navigation DownloadBar
    ],
    # Cross-Origin Redirects
    # alternatively use report-to etc?
    'securitypolicyviolation': [
        'fetch',
        'iframe', # COSI-CSPViolation
        # ... all inclusion types possible?
    ],
    
    # Not included COSI-AppCacheError

}

timing = {
    # all inclusion methods possible and many different timing methods (cache)
    # COSI-Timing

}
