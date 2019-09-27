#!/usr/bin/env python
# -*- encoding: utf-8
"""
Usage: search_github.py <QUERY> --api_token=<TOKEN>
"""

import os
import webbrowser

import docopt

from common import slugify
import get_search_results
import render_search_results


if __name__ == "__main__":
    args = docopt.docopt(__doc__)

    query = args["<QUERY>"]
    api_token = args["--api_token"]

    search_result_path = get_search_results.main(query=query, api_token=api_token)

    html_output = render_search_results.main(
        search_result_path=search_result_path,
        api_token=api_token
    )

    out_path = f"results_{slugify(query)}.html"
    with open(out_path, "w") as outfile:
        outfile.write(html_output)

    print(out_path)

    webbrowser.open("file://" + os.path.abspath("results_requests-get.html"))
