#!/usr/bin/env python
#
# Copyright (C) 2017 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest
from vts.harnesses.host_controller.build import pab_client

try:
    from unittest import mock
except ImportError:
    import mock

from requests.models import Response


class PartnerAndroidBuildClientTest(unittest.TestCase):
    """Tests for Partner Android Build client."""

    def setUp(self):
        self.client = pab_client.PartnerAndroidBuildClient()
        self.client.XSRF_STORE = None

    def testUrlFormat(self):
        expected_url = (
            "https://partnerdash.google.com/build/gmsdownload/"
            "f_companion/label/clockwork.companion_20170906_211311_RC00/"
            "ClockworkCompanionGoogleWithGmsRelease_signed.apk?a=100621237")

        url = self.client.GetArtifactURL(
            100621237, 'f_companion', 'label',
            'clockwork.companion_20170906_211311_RC00',
            'ClockworkCompanionGoogleWithGmsRelease_signed.apk')
        self.assertEqual(url, expected_url)

    @mock.patch("pab_client.flow_from_clientsecrets")
    @mock.patch("pab_client.run_flow")
    @mock.patch("pab_client.Storage")
    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    def testAuthenticationNew(self, mock_creds, mock_storage, mock_rf,
                              mock_ffc):
        mock_creds.invalid = True
        self.client.Authenticate()
        mock_ffc.assert_called_once()
        mock_storage.assert_called_once()
        mock_rf.assert_called_once()

    @mock.patch("pab_client.flow_from_clientsecrets")
    @mock.patch("pab_client.run_flow")
    @mock.patch("pab_client.Storage")
    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    def testAuthenticationStale(self, mock_creds, mock_storage, mock_rf,
                                mock_ffc):
        mock_creds.invalid = False
        mock_creds.access_token_expired = True
        self.client.Authenticate()
        mock_ffc.assert_called_once()
        mock_storage.assert_called_once()
        mock_rf.assert_not_called()
        mock_creds.refresh.assert_called_once()

    @mock.patch("pab_client.flow_from_clientsecrets")
    @mock.patch("pab_client.run_flow")
    @mock.patch("pab_client.Storage")
    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    def testAuthenticationFresh(self, mock_creds, mock_storage, mock_rf,
                                mock_ffc):
        mock_creds.invalid = False
        mock_creds.access_token_expired = False
        self.client.Authenticate()
        mock_ffc.assert_called_once()
        mock_storage.assert_called_once()
        mock_rf.assert_not_called()
        mock_creds.refresh.assert_not_called()

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    @mock.patch('pab_client.open')
    def testGetArtifact(self, mock_open, mock_requests, mock_creds):
        artifact_url = (
            "https://partnerdash.google.com/build/gmsdownload/"
            "f_companion/label/clockwork.companion_20170906_211311_RC00/"
            "ClockworkCompanionGoogleWithGmsRelease_signed.apk?a=100621237")
        self.client.GetArtifact(
            artifact_url, 'ClockworkCompanionGoogleWithGmsRelease_signed.apk')
        mock_creds.apply.assert_called_with({})
        mock_requests.get.assert_called_with(
            artifact_url, headers={}, stream=True)
        mock_open.assert_called_with(
            'ClockworkCompanionGoogleWithGmsRelease_signed.apk', 'wb')

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetABArtifactURL(self, mock_requests, mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'{ "result" : {"1": "this_url"}}'
        mock_requests.post.return_value = response
        url = self.client.GetABArtifactURL(
            100621237, "4331445", "darwin_mac",
            "android-ndk-43345-darwin-x86_64.tar.bz2", "aosp-master-ndk", "",
            0)

        mock_requests.post.assert_called_with(
            'https://partner.android.com/build/u/0/_gwt/_rpc/buildsvc',
            data=
            ('{"xsrf": "disable", "params": "{\\"1\\": \\"4331445\\", \\"3\\": '
             '\\"android-ndk-43345-darwin-x86_64.tar.bz2\\", \\"2\\": '
             '\\"darwin_mac\\", \\"5\\": \\"\\", \\"4\\": '
             '\\"aosp-master-ndk\\", \\"6\\": 0}", '
             '"method": "downloadBuildArtifact"}'),
            headers={
                'Content-Type': 'application/json',
                'x-alkali-account': 100621237
            })
        self.assertEqual(url, "this_url")

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetABArtifactURLBackendError(self, mock_requests, mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'not JSON'
        mock_requests.post.return_value = response
        with self.assertRaises(ValueError) as cm:
            self.client.GetABArtifactURL(
                100621237, "4331445", "darwin_mac",
                "android-ndk-43345-darwin-x86_64.tar.bz2", "aosp-master-ndk",
                "", 0)
        expected = "Backend error -- check your account ID"
        self.assertEqual(str(cm.exception), expected)

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetABArtifactURLMissingResultError(self, mock_requests,
                                               mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'{"result": {}}'
        mock_requests.post.return_value = response
        with self.assertRaises(ValueError) as cm:
            self.client.GetABArtifactURL(
                100621237, "4331445", "darwin_mac",
                "android-ndk-43345-darwin-x86_64.tar.bz2", "aosp-master-ndk",
                "", 0)
        expected = "Resource not found"
        self.assertIn(expected, str(cm.exception))

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetABArtifactURLInvalidXSRFError(self, mock_requests, mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'{"error": {"code": -32000, "message":"Invalid"}}'
        mock_requests.post.return_value = response
        with self.assertRaises(ValueError) as cm:
            self.client.GetABArtifactURL(
                100621237, "4331445", "darwin_mac",
                "android-ndk-43345-darwin-x86_64.tar.bz2", "aosp-master-ndk",
                "", 0)
        self.assertIn('Bad XSRF token', str(cm.exception))

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetABArtifactURLInvalidXSRFError(self, mock_requests, mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'{"error": {"code": -32001, "message":"Expired"}}'
        mock_requests.post.return_value = response
        with self.assertRaises(ValueError) as cm:
            self.client.GetABArtifactURL(
                100621237, "4331445", "darwin_mac",
                "android-ndk-43345-darwin-x86_64.tar.bz2", "aosp-master-ndk",
                "", 0)
        self.assertIn('Expired XSRF token', str(cm.exception))

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetABArtifactURLUnknownError(self, mock_requests, mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'{"some_other_json": "foo"}'
        mock_requests.post.return_value = response
        with self.assertRaises(ValueError) as cm:
            self.client.GetABArtifactURL(
                100621237, "4331445", "darwin_mac",
                "android-ndk-43345-darwin-x86_64.tar.bz2", "aosp-master-ndk",
                "", 0)
        self.assertIn('Unknown response from server', str(cm.exception))

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetBuildListSuccess(self, mock_requests, mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'{"result": {"1": "foo"}}'
        mock_requests.post.return_value = response
        result = self.client.GetBuildList(100621237, "git_oc-treble-dev",
                                          "aosp_arm64_ab-userdebug")
        self.assertEqual(result, "foo")
        mock_requests.post.assert_called_with(
            'https://partner.android.com/build/u/0/_gwt/_rpc/buildsvc',
            data=
            ('{"xsrf": "disable", '
             '"params": "{\\"1\\": \\"git_oc-treble-dev\\", \\"3\\": \\"\\", '
             '\\"2\\": \\"aosp_arm64_ab-userdebug\\", '
             '\\"4\\": 10, \\"7\\": 1}", '
             '"method": "listBuild"}'),
            headers={
                'Content-Type': 'application/json',
                'x-alkali-account': 100621237
            })

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.requests')
    def testGetBuildListError(self, mock_requests, mock_creds):
        self.client._xsrf = 'disable'
        response = Response()
        response.status_code = 200
        response._content = b'{"result": {"3": "foo"}}'
        mock_requests.post.return_value = response
        with self.assertRaises(ValueError) as cm:
            self.client.GetBuildList(100621237, "git_oc-treble-dev",
                                     "aosp_arm64_ab-userdebug")
        self.assertIn('Build list not found', str(cm.exception))

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.PartnerAndroidBuildClient.GetBuildList')
    def testGetLatestBuildIdSuccess(self, mock_gbl, mock_creds):
        self.client._xsrf = 'disable'
        mock_gbl.return_value = [{'7': 5, '1': 'bad'}, {'7': 7, '1': 'good'}]
        result = self.client.GetLatestBuildId(100621237, "git_oc-treble-dev",
                                              "aosp_arm64_ab-userdebug")
        self.assertEqual(result, 'good')

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.PartnerAndroidBuildClient.GetBuildList')
    def testGetLatestBuildIdEmpty(self, mock_gbl, mock_creds):
        self.client._xsrf = 'disable'
        mock_gbl.return_value = []
        with self.assertRaises(ValueError) as cm:
            result = self.client.GetLatestBuildId(
                100621237, "git_oc-treble-dev", "aosp_arm64_ab-userdebug")
        self.assertIn("No builds found for", str(cm.exception))

    @mock.patch('pab_client.PartnerAndroidBuildClient._credentials')
    @mock.patch('pab_client.PartnerAndroidBuildClient.GetBuildList')
    def testGetLatestBuildIdAllBad(self, mock_gbl, mock_creds):
        self.client._xsrf = 'disable'
        mock_gbl.return_value = [{'7': 0}, {'7': 0}]
        with self.assertRaises(ValueError) as cm:
            result = self.client.GetLatestBuildId(
                100621237, "git_oc-treble-dev", "aosp_arm64_ab-userdebug")
        self.assertEqual(
            "No complete builds found: 2 failed or incomplete builds found",
            str(cm.exception))


if __name__ == "__main__":
    unittest.main()