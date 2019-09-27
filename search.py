#!/usr/bin/env python
# -*- encoding: utf-8

import urllib3

http = urllib3.PoolManager()

TOKEN = open("token.txt").read().strip()
headers = urllib3.util.make_headers(basic_auth=TOKEN)
headers["Accept"] = "application/vnd.github.v3.text-match+json"
headers["User-Agent"] = "search.py from alexwlchan"
resp = http.request('GET', "https://api.github.com/search/code?q=GetObjectRequest", headers=headers)
with open("resp.json", "wb") as f:
    f.write(resp.data)