# -*- encoding: utf-8

import json
import os
import pathlib
import re

from unidecode import unidecode
import urllib3


def get_github_api_response(url, api_token=None, headers=None):
    """
    Make a request to the GitHub API, and return the body of the response.

    :param api_token: API token to use in HTTP Basic Auth requests.  You don't
        have to provide this, but some API endpoints require authorization,
        and others are rate-limited without authorization.  (Optional)
    :param headers: Any extra HTTP headers to add to the request.  (Optional)

    """
    if headers is None:
        headers = {}

    # Add the Authorization header
    if api_token is not None:
        headers.update(urllib3.util.make_headers(basic_auth=api_token))

    # The GitHub API rejects requests that don't have a User-Agent header.
    headers["User-Agent"] = f"Python script {__file__}, written by alexwlchan"

    http = urllib3.PoolManager()
    resp = http.request("GET", url, headers=headers)

    if resp.status != 200:
        raise RuntimeException(
            f"Non-200 HTTP status code from GitHub ({resp.status}): {resp.data}")

    return resp.data


def slugify(u):
    """Convert Unicode string into blog slug."""
    # From https://leancrew.com/all-this/2014/10/asciifying/

    u = re.sub(u'[–—/:;,.]', '-', u)  # replace separating punctuation
    a = unidecode(u).lower()          # best ASCII substitutions, lowercased
    a = re.sub(r'[^a-z0-9 -]', '', a) # delete any other characters
    a = a.replace(' ', '-')           # spaces to hyphens
    a = re.sub(r'-+', '-', a)         # condense repeated hyphens
    return a


def save_json_response(url, data):
    out_path = pathlib.Path("_cache") / slugify(str(url))
    out_path.parent.mkdir(exist_ok=True)

    parsed_data = json.loads(data)
    json_string = json.dumps(parsed_data, indent=2, sort_keys=True)

    out_path.write_text(json_string)

    return out_path

