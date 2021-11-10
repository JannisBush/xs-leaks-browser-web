
{% elif "track" in inc_method %}
        <video src="http://localhost:8000/echo/?ecocnt_vid=a=a&access-control-allow-origin=*" crossorigin>
        <{{ inc_tag}} {{ inc_src}}="{{ test_url }}" {{ extra }} default id="test_elem" onerror="record_event(event)" onload="record_event(event)" onloadedmetadata="record_event(event)" onstalled="record_event(event)" onsuspend="record_event(event)"></{{ inc_tag}}>
        </video>
{% elif "source" in inc_method %}
        <picture>
        <{{ inc_tag}} {{ inc_src}}="{{ test_url }}#{{ hash }}" {{ extra }} id="test_elem" onerror="record_event(event)" onload="record_event(event)" onloadedmetadata="record_event(event)" onstalled="record_event(event)" onsuspend="record_event(event)"></{{ inc_tag}}>
        <img alt="no">
        </picture>