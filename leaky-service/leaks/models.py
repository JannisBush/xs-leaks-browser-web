from django.db import models
import os

def to_dict(url_dict_obj):
    """Returns an URLDict object as a JSONable dict."""
    opts = url_dict_obj._meta
    data = {}
    for f in opts.concrete_fields:
        name = f.db_column if f.db_column is not None else f.name
        data[name] = f.value_from_object(url_dict_obj)
    data["url"] = f"{os.getenv('BASE_URL')}/leaks/{url_dict_obj.url_id}/noauth/"
    return data

# Dict to lookup the python identifiers of the different headers
column_look_up = {
    "X-Content-Type-Options": "xcto",
    "X-Frame-Options": "xfo",
    "Content-Type": "ct",
    "Content-Disposition": "cd",
    "Cross-Origin-Resource-Policy": "corp",
    "Cross-Origin-Opener-Policy": "coop",
    "Location": "loc",
}
class URLDict(models.Model):
    """Model for an entry in ther URLDict."""
    url_id = models.IntegerField(db_column="url_id")
    url_dict_version = models.TextField(db_column="url_dict_version")
    ecohd_status = models.IntegerField(db_column="Status-Code")
    body = models.TextField(default="empty", db_column="body")
    xcto = models.TextField(default="empty", db_column="X-Content-Type-Options")
    xfo = models.TextField(default="empty", db_column="X-Frame-Options")
    ct = models.TextField(default="empty", db_column="Content-Type")
    cd = models.TextField(default="empty", db_column="Content-Disposition")
    corp = models.TextField(default="empty", db_column="Cross-Origin-Resource-Policy")
    coop = models.TextField(default="empty", db_column="Cross-Origin-Opener-Policy")
    loc = models.TextField(default="empty", db_column="Location")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["url_id", "url_dict_version"],
                name="unique_url_for_version"
            )
        ]