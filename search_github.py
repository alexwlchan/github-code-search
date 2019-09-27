#!/usr/bin/env python
# -*- encoding: utf-8
"""
Search the GitHub API, and cache the results.  Prints a path to the saved JSON file.

Usage: search_github.py <SEARCH_TERM> [--api_token=<TOKEN>]
"""

import json

import docopt
import hyperlink

from common import get_github_api_response, save_json_response


if __name__ == '__main__':
    args = docopt.docopt(__doc__)

    # https://developer.github.com/v3/search/#search-code
    api_url = hyperlink.URL.from_text("https://api.github.com/search/code")
    query_url = api_url.set("q", args["<SEARCH_TERM>"])

    resp = get_github_api_response(
        url=str(query_url),
        api_token=args["--api_token"],

        # This header means we get text-match data in the response, so we can
        # see which part of the code fragment matched this query.
        headers={"Accept": "application/vnd.github.v3.text-match+json"}
    )

    out_data = {
        "query": args["<SEARCH_TERM>"],
        "search_response": json.loads(resp)
    }

    out_path = save_json_response(url=query_url, data=out_data)

    print(out_path)
