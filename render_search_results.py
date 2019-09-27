#!/usr/bin/env python
# -*- encoding: utf-8
"""
Given a search result from the GitHub API, render the results in a way that
minimises duplication.

Usage: render_search_results.py <SEARCH_RESULT_JSON> [--api_token=<TOKEN>]
"""

import base64
import hashlib
import json

import docopt
import hyperlink
from jinja2 import Environment, FileSystemLoader
import more_itertools
import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer_for_filename
import tqdm

from common import get_json_response_with_caching


def deduplicate_results(search_items, api_token=None):
    """
    Given a collection of search results from the GitHub API, work out which of
    them are actually unique, and which are duplicate files in multiple repos.

    :param api_token: API token to use in HTTP Basic Auth requests.  You don't
        have to provide this, but there are rate limits on looking up the contents
        of files if you don't use authorization on your requests.

    """
    unique_results = []

    # {$a => $b} is the blob with hash $a is equivalent to the blob with hash $b
    blob_aliases = {}

    for item in tqdm.tqdm(search_items):
        blob_id = hyperlink.URL.from_text(item["git_url"]).path[-1]

        parsed_data = {
            "repo_name": item["repository"]["full_name"],
            "name": item["name"],
            "path": item["path"],
            "blobs": set(blob_id),
            "text_matches": item["text_matches"],
            "html_url": item["html_url"],
            "duplicate_results": [],
        }

        # A Git "blob" is based on file contents.  If two blobs have the same hash,
        # then they describe files with the same contents.
        #
        # In that case, this is a duplicate result.
        try:
            match = next(
                uq for uq in unique_results if blob_id in uq["blobs"]
            )
        except StopIteration:
            pass
        else:
            del parsed_data["duplicate_results"]
            match["duplicate_results"].append(parsed_data)
            match["blobs"].add(blob_id)
            continue

        # This doesn't match anything we've seen so far, so go ahead and fetch
        # the contents of the file.
        blob_data = get_json_response_with_caching(
            item["git_url"], api_token=api_token
        )

        # Read the content of the file, and normalise the file contents to use
        # Unix-style line endings.  Sometimes we'll have files that differ only
        # in line endings, but for search purposes we should treat them as the same.
        content = base64.b64decode(blob_data["content"])

        unix_normalised_content = content.replace(b"\r\n", b"\n")
        parsed_data["content"] = unix_normalised_content

        # Now look for duplicates again: are there any files with a different blob
        # but matching content?
        try:
            match = next(
                uq
                for uq in unique_results
                if unix_normalised_content == uq["content"]
            )
        except StopIteration:
            pass
        else:
            del parsed_data["duplicate_results"]
            match["duplicate_results"].append(parsed_data)
            match["blobs"].add(blob_id)
            continue

        # Okay, we're sure this isn't a duplicate.  Add it to the list as a new
        # unique result.
        unique_results.append(parsed_data)

    return unique_results


def prepare_html_results(unique_results):
    for result in unique_results:

        # Start by rendering the file contents as HTML.  Throw away the opening
        # and closing tags; we'll add those back later.
        lexer = guess_lexer_for_filename(result["name"], result["content"])
        html_output = pygments.highlight(result["content"], lexer, HtmlFormatter())
        html_output = html_output.replace(
            '<div class="highlight"><pre>', '').replace("</pre></div>", "")

        # Now go through the lines, compare them to the "text_match" entries,
        # and work out which lines we actually want to show.
        lines_to_show = set()

        source_lines = result["content"].decode("utf8").splitlines()

        # TODO: There's some fudging with +1 and +2 below to get the correct
        # range of lines.  I erred on the side of showing more lines rather than
        # less, but I definitely don't quite understand what's going on here!

        for lineno, line in enumerate(source_lines, start=1):
            for match in result["text_matches"]:

                # Sometimes a fragment only contains the end of the first line
                # or the start of the last line.
                if len(match["fragment"].splitlines()) <= 2:
                    complete_fragment_lines = match["fragment"].splitlines()
                else:
                    complete_fragment_lines = match["fragment"].splitlines()[1:-1]

                if source_lines[lineno:lineno + len(complete_fragment_lines)] == complete_fragment_lines:
                    for i in range(lineno, lineno + len(complete_fragment_lines) + 1):
                        lines_to_show.add(i)

        # For each line that we're showing, add the corresponding HTML lines.
        #
        # Remember that Python lists are 0-indexed, but line numbers are 0-indexed,
        # so we add an empty line as line 0.
        html_lines = [""] + html_output.splitlines()

        html_snippets = []
        for group in more_itertools.consecutive_groups(sorted(lines_to_show)):
            linenos = list(group)
            html_snippets.append(
                zip(linenos, html_lines[linenos[0]:linenos[-1] + 2])
            )

        result["html_snippets"] = html_snippets

        yield result


def render_html_results(html_results, query):
    env = Environment(loader=FileSystemLoader("."))

    # Allow me to use `zip()` in the template.
    # See https://stackoverflow.com/q/5208252/1558022
    env.globals.update(zip=zip)

    template = env.get_template("results.html")

    return template.render(results=html_results, query=query)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)

    search_result_path = args["<SEARCH_RESULT_JSON>"]
    api_token = args["--api_token"]

    search_results = json.load(open(search_result_path))

    unique_results = deduplicate_results(
        search_results["search_response"]["items"],
        api_token=api_token
    )

    html_results = prepare_html_results(unique_results)

    html_output = render_html_results(
        html_results=html_results,
        query=search_results["query"]
    )

    print(html_output)
