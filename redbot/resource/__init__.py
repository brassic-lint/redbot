#!/usr/bin/env python

"""
The Resource Expert Droid.

RED will examine a HTTP resource for problems and other interesting
characteristics, making a list of these observation notes available
for presentation to the user. It does so by potentially making a number
of requests to probe the resource's behaviour.

See webui.py for the Web front-end.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from urlparse import urljoin

import redbot.speak as rs
from redbot.resource.fetch import RedFetcher, UA_STRING
from redbot.formatter import f_num
from redbot.resource import active_check


class HttpResource(RedFetcher):
    """
    Given a URI (optionally with method, request headers and body), as well
    as an optional status callback and list of body processors, examine the
    URI for issues and notable conditions, making any necessary additional
    requests.

    Note that this primary request negotiates for gzip content-encoding;
    see ConnegCheck.

    After processing the response-specific attributes of RedFetcher will be
    populated, as well as its notes; see that class for details.
    """
    def __init__(self, uri, method="GET", req_hdrs=None, req_body=None,
                status_cb=None, body_procs=None, descend=False):
        orig_req_hdrs = req_hdrs or []
        new_req_hdrs = orig_req_hdrs + [(u'Accept-Encoding', u'gzip')]
        RedFetcher.__init__(self, uri, method, new_req_hdrs, req_body,
                            status_cb, body_procs, name=method)
        self.descend = descend
        self.response.set_link_procs([self.process_link])
        self.subreqs = {} # sub-requests' RedState objects
        self.links = {}          # {type: set(link...)}
        self.link_count = 0
        self.linked = []    # list of linked HttpResources (if descend=True)
        self.orig_req_hdrs = orig_req_hdrs
        self.partial_support = None
        self.inm_support = None
        self.ims_support = None
        self.gzip_support = None
        self.gzip_savings = 0

    def done(self):
        """
        Response is available; perform further processing that's specific to
        the "main" response.
        """
        if self.response.complete:
            active_check.spawn_all(self)

    def process_link(self, base, link, tag, title):
        "Handle a link from content"
        self.link_count += 1
        if not self.links.has_key(tag):
            self.links[tag] = set()
        if self.descend and tag not in ['a'] and link not in self.links[tag]:
            linked = HttpResource(
                urljoin(base, link),
                req_hdrs=self.orig_req_hdrs,
                status_cb=self.status_cb,
            )
            self.linked.append((linked, tag))
            self.add_task(linked.run)
        self.links[tag].add(link)
        if not self.response.base_uri:
            self.response.base_uri = base


if __name__ == "__main__":
    import sys
    def status_p(msg):
        'print the status message'
        print msg
    RED = HttpResource(sys.argv[1], status_cb=status_p)
    RED.run()
    print RED.notes
