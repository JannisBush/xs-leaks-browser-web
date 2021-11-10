from celery import Celery

app = Celery('python_worker',
    broker='pyamqp://guest@localhost//',
)


if __name__ == '__main__':
    cookies = [ {'domain': 'example.org', 'name': 'sectionFilterApplied', 'value': 'true', 'path': '/', 'httpOnly': False, 'secure': False}, {'domain': 'example.com', 'secure': True, 'value': 's%3A93EUlGSOqODk1Dm6cd4twh1NcRy5Fi4v.8KZtWWt67yLRN%2FCpXEzExoXJlY0sOxBcOTIfdWVPg%2BY', 'expiry': 1625511081, 'path': '/', 'httpOnly': True, 'name': 'connect.sid'},  {'domain': 'example.com', 'secure': True, 'value': 'en-US', 'expiry': 1655837481, 'path': '/', 'httpOnly': False, 'name': 'locale'},  {'domain': 'example.com', 'name': 'sectionsSortStrategy', 'value': 'cat_new_to_old', 'path': '/', 'httpOnly': False, 'secure': False}, {'domain': 'example.com', 'name': 'overviewLayoutStrategy', 'value': '', 'path': '/', 'httpOnly': False, 'secure': False}, {'domain': 'example.com', 'name': '_csrf', 'value': 'Vi1fP7b2S0iCMyxwHtmz6m5A', 'path': '/', 'httpOnly': False, 'secure': False}, {'domain': 'example.com', 'name': 'notesSortStrategy', 'value': 'new_to_old', 'path': '/', 'httpOnly': False, 'secure': False}]
    # cookies = [{"domain": "172.17.0.1", "name": "sessionid", "value": "9qz9j20prywb1ekjvu39da85bq9duwc2", "path": "/", "sameSite": "None", "secure": True}]

    result = app.send_task("start_node.test_site", args=["example.org", cookies], kwargs={}, queue="node")

