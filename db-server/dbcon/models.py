from django.db import models


class Browser(models.Model):
    """The schema of a Browser."""
    browser = models.TextField()
    version = models.TextField()
    headless = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["browser", "version", "headless"], name="browser")
        ]


class Test(models.Model):
    """The schema of a test."""
    test_url = models.TextField()
    inc_method = models.TextField()
    url_dict_version = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["test_url", "inc_method", "url_dict_version"], name="test")
        ]


class Events(models.Model):
    """The schema of the events."""
    event_set = models.TextField()
    event_list = models.TextField()
    load_count = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event_set", "event_list", "load_count"], name="events")
        ]


class WindowProperties(models.Model):
    """The schem of the window properties."""
    op_frame_count = models.TextField()
    op_win_window = models.TextField()
    op_win_CSS2Properties = models.TextField()
    op_win_origin = models.TextField()
    op_win_opener = models.TextField()
    op_win_history_length = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["op_frame_count", "op_win_window", "op_win_CSS2Properties", "op_win_origin", "op_win_opener", "op_win_history_length"
                                            ],
                                    name="win")
        ]


class ObjectProperties(models.Model):
    """The schema of the object properties."""
    op_el_height = models.TextField()
    op_el_width = models.TextField()
    op_el_naturalHeight = models.TextField()
    op_el_naturalWidth = models.TextField()
    op_el_videoWidth = models.TextField()
    op_el_videoHeight = models.TextField()
    op_el_duration = models.TextField()
    op_el_networkState = models.TextField()
    op_el_readyState = models.TextField()
    op_el_buffered = models.TextField()
    op_el_paused = models.TextField()
    op_el_seekable = models.TextField()
    op_el_sheet = models.TextField()
    op_el_media_error = models.TextField()
    op_el_contentDocument = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=[
                "op_el_height", "op_el_width",
                "op_el_naturalHeight", "op_el_naturalWidth", "op_el_videoHeight", "op_el_videoWidth",
                "op_el_duration", "op_el_networkState", "op_el_readyState", "op_el_buffered", "op_el_paused",
                "op_el_seekable", "op_el_sheet",  "op_el_media_error", "op_el_contentDocument"],
                name="op")
        ]


class GlobalProperties(models.Model):
    """The schema of global properties."""
    gp_window_onerror = models.TextField()
    gp_window_onblur = models.TextField()
    gp_window_postMessage = models.TextField()
    gp_window_getComputedStyle = models.TextField()
    gp_window_hasOwnProperty = models.TextField()
    gp_download_bar_height = models.TextField()
    gp_securitypolicyviolation = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["gp_window_onerror", "gp_window_onblur", "gp_window_postMessage", "gp_window_getComputedStyle",
                                            "gp_window_hasOwnProperty", "gp_download_bar_height", "gp_securitypolicyviolation"],
                                    name="gp")
        ]


class Observation(models.Model):
    """The schema of a observation."""
    browser = models.ForeignKey(Browser, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    global_properties = models.ForeignKey(
        GlobalProperties, on_delete=models.CASCADE, null=True)
    events = models.ForeignKey(Events, on_delete=models.CASCADE, null=True)
    object_properties = models.ForeignKey(
        ObjectProperties, on_delete=models.CASCADE, null=True)
    window_properties = models.ForeignKey(
        WindowProperties, on_delete=models.CASCADE, null=True)
    loading_time = models.IntegerField(null=True)
    timed_out = models.BooleanField(default=False)
    apg_url = models.TextField(null=True) 
    complete_time = models.IntegerField(null=True)
    retest = models.BooleanField(default=False)

class LeakResult(models.Model):
    """The schema of a leak result."""
    browser = models.ForeignKey(Browser, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    global_properties = models.ForeignKey(
        GlobalProperties, on_delete=models.CASCADE, null=True)
    events = models.ForeignKey(Events, on_delete=models.CASCADE, null=True)
    object_properties = models.ForeignKey(
        ObjectProperties, on_delete=models.CASCADE, null=True)
    window_properties = models.ForeignKey(
        WindowProperties, on_delete=models.CASCADE, null=True)
    loading_time = models.IntegerField(null=True)
    timed_out = models.BooleanField(default=False)
    apg_url = models.TextField(null=True) 
    complete_time = models.IntegerField(null=True)
    retest_num = models.IntegerField(default=False) # Run every test several times to make FPs less likely
    cookies = models.BooleanField(default=False)
    site = models.TextField()

class CookieSecFetch(models.Model):
    """The schema of the cookie/sec-fetch test."""
    browser = models.TextField()
    version = models.TextField()
    inc_method = models.TextField()
    org_site = models.TextField()
    rec_site = models.TextField()
    c_ns_f = models.TextField()
    c_ns_t = models.TextField()
    c_n_f = models.TextField()
    c_n_t = models.TextField()
    c_l_f = models.TextField()
    c_l_t = models.TextField()
    c_s_f = models.TextField()
    c_s_t = models.TextField()
    sec_fetch_dest = models.TextField()
    sec_fetch_mode = models.TextField()
    sec_fetch_site = models.TextField()
    sec_fetch_user = models.TextField()

class Result(models.Model):
    """The schema of the data we gather."""
    browser = models.CharField(max_length=20)
    version = models.CharField(max_length=50)
    apg_url = models.TextField()
    test_url = models.TextField()
    inc_method = models.TextField()
    global_properties = models.TextField(null=True)
    object_properties = models.TextField(null=True)
    event_set = models.TextField(null=True)
    event_list = models.TextField(null=True)
    timed_out = models.BooleanField(default=False)
    auth_failed = models.BooleanField(default=False)
    url_dict_version = models.TextField(default="Unknown")
    loading_time = models.IntegerField(null=True)
    headless = models.BooleanField(default=False)
    gp_window_onerror = models.TextField(null=True)
    gp_window_onblur = models.TextField(null=True)
    gp_window_postMessage = models.TextField(null=True)
    gp_window_getComputedStyle = models.TextField(null=True)
    gp_window_hasOwnProperty = models.TextField(null=True)
    gp_download_bar_height = models.TextField(null=True)
    gp_securitypolicyviolation = models.TextField(null=True)
    op_frame_count = models.TextField(null=True)
    op_win_window = models.TextField(null=True)
    op_win_CSS2Properties = models.TextField(null=True)
    op_win_origin = models.TextField(null=True)
    op_win_opener = models.TextField(null=True)
    op_el_height = models.TextField(null=True)
    op_el_width = models.TextField(null=True)
    op_el_naturalHeight = models.TextField(null=True)
    op_el_naturalWidth = models.TextField(null=True)
    op_el_videoWidth = models.TextField(null=True)
    op_el_videoHeight = models.TextField(null=True)
    op_el_duration = models.TextField(null=True)
    op_el_networkState = models.TextField(null=True)
    op_el_readyState = models.TextField(null=True)
    op_el_buffered = models.TextField(null=True)
    op_el_paused = models.TextField(null=True)
    op_el_seekable = models.TextField(null=True)
    op_el_sheet = models.TextField(null=True)
    op_el_media_error = models.TextField(null=True)
