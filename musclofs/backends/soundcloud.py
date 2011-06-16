# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Copyright (c) 2011 Andoni Morales Alstruey <ylatuya@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import urllib, urllib2
import webbrowser

import scapi

from musclofs.backend import APIBackendBase
from musclofs.errors import PathNotFound
from musclofs import fs



# the host to connect to. Normally, this
# would be api.soundcloud.com
API_HOST = "api.soundcloud.com"

# This needs to be the consumer ID you got from
# http://soundcloud.com/settings/applications/new
CONSUMER = "121b1b21907cac103a4abbfa1bc5a543"

# This needs to be the consumer secret password you got from
# http://soundcloud.com/settings/applications/new
CONSUMER_SECRET = "9a3a9773106b33f1eefad1bff5b7ba2e"


class SoundCloudFile(fs.MuscloFile):

    def __init__(self, track, backend):
        fs.MuscloFile.__init__(self, str(track.title), backend)
        self.track = track


class SoundCloudBackend(APIBackendBase):

    api = None

    def __init__(self):
        APIBackendBase.__init__(self, 'SoundCloud')

    def start(self):
        # first, we create an OAuthAuthenticator that only knows about consumer
        # credentials. This is done so that we can get an request-token as
        # first step.
        oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER,
                                                                      CONSUMER_SECRET,
                                                                      None,
                                                                      None)

        # The connector works with the authenticator to create and sign the requests. It
        # has some helper-methods that allow us to do the OAuth-dance.
        connector = scapi.ApiConnector(host=API_HOST, authenticator=oauth_authenticator)

        # First step is to get a request-token, and to let the user authorize that
        # via the browser.
        token, secret = connector.fetch_request_token()
        authorization_url = connector.get_request_token_authorization_url(token)
        webbrowser.open(authorization_url)
        oauth_verifier = raw_input("please enter verifier code as seen in the browser:")

        # Now we create a new authenticator with the temporary token & secret we got from
        # the request-token. This will give us the access-token
        oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                                      CONSUMER_SECRET,
                                                                      token, 
                                                                      secret)

        # we need a new connector with the new authenticator!
        connector = scapi.ApiConnector(API_HOST, authenticator=oauth_authenticator)
        token, secret = connector.fetch_access_token(oauth_verifier)


        # now we are finally ready to go - with all four parameters OAuth requires,
        # we can setup an authenticator that allows for actual API-calls.
        oauth_authenticator = scapi.authentication.OAuthAuthenticator(CONSUMER, 
                                                                      CONSUMER_SECRET,
                                                                      token, 
                                                                      secret)

        # we pass the connector to a Scope - a Scope is essentially a path in the REST-url-space.
        # Without any path-component, it's the root from which we can then query into the
        # resources.
        self.api = scapi.Scope(scapi.ApiConnector(host=API_HOST, authenticator=oauth_authenticator))
        self.populate()

    def populate(self):
        tracks = self.api.me().tracks('?limit=5')
        for track in tracks:
            logging.debug(str(track.title))
            self.add_file(SoundCloudFile(track, self))

    def delete(self, file):
        logging.debug("delete %s", file)
        try:
            self.api.me().tracks.remove(file.track)
        except Exception, e:
            logging.error("Error removing track: %s", e)
            raise

    def download(self, file, target_filename):
        logging.debug("download %s", file)
        if bool(file.track.downloadable):
            download_url = file.track.download_url
        else:
            download_url = file.track.waveform_url
        signed_url = file.track.oauth_sign_get_request(download_url)
        urllib.urlretrieve(signed_url, target_filename)

    def upload(self, fs_file, src_file):
        logging.debug("upload %s", src_file.name)
        try:
            track = self.api.Track.new(title=fs_file.track.title,
                        asset_data=src_file)
            fs_file.track = track
            self.add_file(fs_file)
        except Exception, e:
            logging.error("Could not upload file: %s" % str(e))
            raise
        logging.info("Track uploaded successfully")

    def new_file(self, path):
        try:
            track = TemporalTrack()
            track.title = path.rsplit('/', 1)[1:][0]
        except Exception, e:
            logging.error(str(e))
            return None
        return SoundCloudFile(track, self)


class TemporalTrack():
    title = ""
