#!/usr/bin/env python
# -*- encoding: utf-8

import base64
import hashlib
import json

import hyperlink
from jinja2 import Environment, FileSystemLoader
import pygments
import urllib3


from itertools import islice

def window(seq, n=2):
    "Returns a sliding window (of width n) over data from the iterable"
    "   s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   "
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result



def sha256(s):
    h = hashlib.sha256()
    h.update(s)
    return h.hexdigest()

http = urllib3.PoolManager()

env = Environment(loader=FileSystemLoader("."))
template = env.get_template("results.html")

data = json.load(open("resp.json"))

unique_results = []

# print(len(data["items"]))

import tqdm

def _get(url):
    TOKEN = open("token.txt").read().strip()
    headers = urllib3.util.make_headers(basic_auth=TOKEN)
    headers["User-Agent"] = f"{__file__} from alexwlchan"

    cached = json.load(open("cached_urls.json"))
    try:
        return cached[url].encode("utf8")
    except KeyError:
        resp = http.request("GET", url, headers=headers)
        cached[url] = resp.data.decode("utf8")
        with open("cached_urls.json", "w") as outfile:
            outfile.write(json.dumps(cached, indent=2, sort_keys=True))

        return resp.data


for item in tqdm.tqdm(data["items"]):
    result = {
        "repo_name": item["repository"]["full_name"],
        "path": item["path"],
        "blob": hyperlink.URL.from_text(item["git_url"]).path[-1],
        "text_matches": item["text_matches"],
        "duplicate_results": [],
        "git_url": item["git_url"],
        "html_url": item["html_url"],
    }

    from pygments.formatters import HtmlFormatter

    resp = _get(item["git_url"])
    content = json.loads(resp)["content"]
    normalised_content = base64.b64decode(content).replace(b"\r\n", b"\n")
    # print(d)
    normalised_hash = sha256(normalised_content)

    from pygments.lexers import guess_lexer_for_filename
    result["hash"] = normalised_hash
    result["lexer"] = guess_lexer_for_filename(item["name"], normalised_content)
    import sys
    # print((result["lexer"], item["name"]), file=sys.stderr)
    result["html_code"] = pygments.highlight(normalised_content, guess_lexer_for_filename(item["name"], normalised_content), HtmlFormatter())

    lines = result["html_code"].splitlines()

    # matching_lines = set()
    # for match in result["text_matches"]:
    #     for line in match["fragment"].splitlines():
    #         if line.strip():
    #             matching_lines.add(line)
    #
    # print(matching_lines)
    # assert 0

    lines_to_show = []

    original_lines = normalised_content.decode("utf8").splitlines()
    html_lines = result["html_code"].replace('<div class="highlight"><pre>', '').replace("</pre></div>", "").splitlines()

    # print(html_lines)

    for lineno, line in enumerate(html_lines, start=1):
        for match in result["text_matches"]:
            if len(match["fragment"].splitlines()) <= 2:
                fragment_lines = match["fragment"].splitlines()
            else:
                fragment_lines = match["fragment"].splitlines()[1:-1]
            # print(original_lines[lineno:lineno + len(fragment_lines)])
            # print(fragment_lines)
            # assert 0
            if original_lines[lineno:lineno + len(fragment_lines)] == fragment_lines:
                lines_to_show.append(
                    (html_lines[lineno-1:lineno + len(fragment_lines) + 1], (lineno, lineno + len(fragment_lines)))
                )


    has_changes = True
    while has_changes:
        has_changes = False

        for code_slice in window(lines_to_show, 2):
            (lines1, range1), (lines2, range2) = code_slice
            if range1[-1] + 1 == range2[0]:
                idx = lines_to_show.index((lines1, range1))
                lines_to_show[idx] = (
                    lines1 + lines2[1:],
                    (range1[0], range2[1])
                )

                lines_to_show.pop(idx + 1)
                has_changes = True
                break

    result["lines_to_show"] = ["\n".join(c[0]) for c in lines_to_show]

    # print(result["lines_to_show"])
    #
    # assert 0

    try:
        matching = next(
            r
            for r in unique_results
            if r["hash"] == result["hash"]
        )
    except StopIteration:
        unique_results.append(result)
    else:
        del result["duplicate_results"]
        matching["duplicate_results"].append(result)

# print(len(unique_results))
print(template.render(unique_results=unique_results, query="GetObjectRequest"))