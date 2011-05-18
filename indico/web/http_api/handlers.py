# -*- coding: utf-8 -*-
##
##
## This file is part of CDS Indico.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010 CERN.
##
## CDS Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS Indico; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""
HTTP API - Handlers
"""

# python stdlib imports
import hashlib
import hmac
import itertools
import re
import time
import urllib
from urlparse import parse_qs
from ZODB.POSException import ConflictError
import pytz

# indico imports
from indico.web.http_api import ExportInterface, LimitExceededException, Exporter
from indico.web.http_api.auth import APIKeyHolder
from indico.web.http_api.cache import RequestCache
from indico.web.http_api.responses import HTTPAPIResult, HTTPAPIError
from indico.web.http_api.util import remove_lists, get_query_parameter
from indico.web.http_api import API_MODE_KEY, API_MODE_ONLYKEY, API_MODE_SIGNED, API_MODE_ONLYKEY_SIGNED, API_MODE_ALL_SIGNED
from indico.web.wsgi import webinterface_handler_config as apache
from indico.util.metadata.serializer import Serializer

# indico legacy imports
from MaKaC.common import DBMgr
from MaKaC.common.fossilize import fossilizes, fossilize, Fossilizable
from MaKaC.accessControl import AccessWrapper
from MaKaC.common.info import HelperMaKaCInfo
from MaKaC.plugins.base import PluginsHolder

# Maximum number of records that will get exported for each detail level
MAX_RECORDS = {
    'events': 10000,
    'contributions': 500,
    'subcontributions': 500,
    'sessions': 100,
}

# Valid URLs for export handlers. the last group has to be the response type
EXPORT_URL_MAP = {
    r'/export/(event|categ)/(\w+(?:-\w+)*)\.(\w+)$': 'handler_event_categ'
}

# Compile url regexps
EXPORT_URL_MAP = dict((re.compile(pathRe), handlerFunc) for pathRe, handlerFunc in EXPORT_URL_MAP.iteritems())
# Remove the extension at the end or before the querystring
RE_REMOVE_EXTENSION = re.compile(r'\.(\w+)(?:$|(?=\?))')


def normalizeQuery(path, query, remove=('signature',)):
    """Normalize request path and query so it can be used for caching and signing

    Returns a string consisting of path and sorted query string.
    Dynamic arguments like signature and timestamp are removed from the query string.
    """
    qdata = remove_lists(parse_qs(query))
    if remove:
        for key in remove:
            qdata.pop(key, None)
    sortedQuery = sorted(qdata.items(), key=lambda x: x[0].lower())
    if sortedQuery:
        return '%s?%s' % (path, urllib.urlencode(sortedQuery))
    else:
        return path


def validateSignature(key, signature, timestamp, path, query):
    ttl = HelperMaKaCInfo.getMaKaCInfoInstance().getAPISignatureTTL()
    if not timestamp:
        raise HTTPAPIError('Signature invalid (no timestamp)', apache.HTTP_FORBIDDEN)
    elif abs(timestamp - int(time.time())) > ttl:
        raise HTTPAPIError('Signature invalid (bad timestamp)', apache.HTTP_FORBIDDEN)
    digest = hmac.new(key, normalizeQuery(path, query), hashlib.sha1).hexdigest()
    if signature != digest:
        raise HTTPAPIError('Signature invalid', apache.HTTP_FORBIDDEN)


def checkAK(apiKey, signature, timestamp, path, query):
    minfo = HelperMaKaCInfo.getMaKaCInfoInstance()
    apiMode = minfo.getAPIMode()
    if not apiKey:
        if apiMode in (API_MODE_ONLYKEY, API_MODE_ONLYKEY_SIGNED, API_MODE_ALL_SIGNED):
            raise HTTPAPIError('API key is missing', apache.HTTP_FORBIDDEN)
        return None, True
    akh = APIKeyHolder()
    if not akh.hasKey(apiKey):
        raise HTTPAPIError('Invalid API key', apache.HTTP_FORBIDDEN)
    ak = akh.getById(apiKey)
    if ak.isBlocked():
        raise HTTPAPIError('API key is blocked', apache.HTTP_FORBIDDEN)
    # Signature validation
    onlyPublic = False
    if signature:
        validateSignature(ak.getSignKey(), signature, timestamp, path, query)
    elif apiMode in (API_MODE_SIGNED, API_MODE_ALL_SIGNED):
        raise HTTPAPIError('Signature missing', apache.HTTP_FORBIDDEN)
    elif apiMode == API_MODE_ONLYKEY_SIGNED:
        onlyPublic = True
    return ak, onlyPublic


def buildAW(ak, req, onlyPublic=False):
    aw = AccessWrapper()
    if ak and not onlyPublic:
        # If we have an authenticated request, require HTTPS
        minfo = HelperMaKaCInfo.getMaKaCInfoInstance()
        if not req.is_https() and minfo.isAPIHTTPSRequired():
            raise HTTPAPIError('HTTPS is required', apache.HTTP_FORBIDDEN)
        aw.setUser(ak.getUser())
    return aw

def handler(req, **params):
    path, query = req.URLFields['PATH_INFO'], req.URLFields['QUERY_STRING']
    # Parse the actual query string
    qdata = parse_qs(query)

    dbi = DBMgr.getInstance()
    dbi.startRequest()

    cache = RequestCache(HelperMaKaCInfo.getMaKaCInfoInstance().getAPICacheTTL())

    apiKey = get_query_parameter(qdata, ['ak', 'apikey'], None)
    signature = get_query_parameter(qdata, ['signature'])
    timestamp = get_query_parameter(qdata, ['timestamp'], 0, integer=True)
    no_cache = get_query_parameter(qdata, ['nc', 'nocache'], 'no') == 'yes'
    pretty = get_query_parameter(qdata, ['p', 'pretty'], 'no') == 'yes'
    onlyPublic = get_query_parameter(qdata, ['op', 'onlypublic'], 'no') == 'yes'

    # Get our handler function and its argument and response type
    func, dformat = Exporter.parseRequest(path, qdata)
    if func is None or dformat is None:
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

    ak = error = result = None
    ts = int(time.time())
    try:
        # Validate the API key (and its signature)
        ak, enforceOnlyPublic = checkAK(apiKey, signature, timestamp, path, query)
        if enforceOnlyPublic:
            onlyPublic = True
        # Create an access wrapper for the API key's user
        aw = buildAW(ak, req, onlyPublic)
        # Get rid of API key in cache key if we did not impersonate a user
        if ak and aw.getUser() is None:
            cache_key = normalizeQuery(path, query, remove=('ak', 'apiKey', 'signature', 'timestamp'))
        else:
            cache_key = normalizeQuery(path, query, remove=('signature', 'timestamp'))

        obj = None
        add_to_cache = True
        cache_key = RE_REMOVE_EXTENSION.sub('', cache_key)
        if not no_cache:
            obj = cache.loadObject(cache_key)
            if obj is not None:
                result, complete = obj.getContent()
                ts = obj.getTS()
                add_to_cache = False
        if result is None:
            # Perform the actual exporting
            result, complete = func(aw)
        if result is not None and add_to_cache:
            cache.cacheObject(cache_key, (result, complete))
    except HTTPAPIError, e:
        error = e
        if e.getCode():
            req.status = e.getCode()

    if result is None and error is None:
        # TODO: usage page
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    else:
        if ak and error is None:
            # Commit only if there was an API key and no error
            for _retry in xrange(10):
                dbi.sync()
                ak.used(req.remote_ip, path, query, not onlyPublic)
                try:
                    dbi.endRequest(True)
                except ConflictError:
                    pass # retry
                else:
                    break
        else:
            # No need to commit stuff if we didn't use an API key
            # (nothing was written)
            dbi.endRequest(False)

        serializer = Serializer.create(dformat, pretty=pretty,
                                       **remove_lists(qdata))

        if error:
            resultFossil = fossilize(error)
        else:
            resultFossil = fossilize(HTTPAPIResult(result, path, query, ts, complete))
        del resultFossil['_fossil']

        req.headers_out['Content-Type'] = serializer.getMIMEType()
        return serializer(resultFossil)