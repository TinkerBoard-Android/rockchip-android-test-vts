#!/usr/bin/env python
#
# Copyright (C) 2018 The Android Open Source Project
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
"""VTS test to verify userspace fastboot implementation."""

import os
import subprocess

from vts.runners.host import asserts
from vts.runners.host import base_test
from vts.runners.host import test_runner
from vts.utils.python.android import api

PROPERTY_LOGICAL_PARTITIONS = "ro.boot.dynamic_partitions"


class VtsFastbootVerificationTest(base_test.BaseTestClass):
    """Verifies userspace fastboot implementation."""

    def setUpClass(self):
        """Initializes the DUT and places devices into fastboot mode.

        Attributes:
            gtest_bin_path: Path to the fuzzy_fastboot gtest binary
        """
        self.dut = self.android_devices[0]
        # precondition_api_level only skips test cases, issuing the
        # 'adb reboot fastboot' could cause undefined behavior in a
        # pre-Q device and hence we need to skip the setup for those
        # devices.
        if self.dut.getLaunchApiLevel() <= api.PLATFORM_API_LEVEL_P:
          return
        self.shell = self.dut.shell
        self.gtest_bin_path = os.path.join("host", "nativetest64", "fuzzy_fastboot",
                                           "fuzzy_fastboot")
        if self.dut.getProp(PROPERTY_LOGICAL_PARTITIONS) != "true":
            self.skipAllTests("Device does not support userspace fastboot")
        else:
            self.dut.cleanUp()
            self.dut.adb.reboot_fastboot()
            # The below command blocks until the device enters fastbootd mode to
            # ensure that the device is in fastbootd mode when setUpClass exits.
            # If this is not done, VTS self-diagnosis tries to recover the
            # device.
            self.dut.fastboot.getvar("is-userspace")

    def testFastbootdSlotOperations(self):
        """Runs fuzzy_fastboot gtest to verify slot operations in fastbootd implementation."""
        # Test slot operations and getvar partition-type
        fastboot_gtest_cmd_slot_operations = [
            "%s" % self.gtest_bin_path, "--gtest_filter=Conformance.Slots:Conformance.SetActive"
        ]
        # TODO(b/117181762): Add a serial number argument to fuzzy_fastboot.
        retcode = subprocess.call(fastboot_gtest_cmd_slot_operations)
        asserts.assertTrue(retcode == 0, "Incorrect slot operations")

    def testLogicalPartitionCommands(self):
        """Runs fuzzy_fastboot to verify getvar commands related to logical partitions."""
        fastboot_gtest_cmd_logical_partition_compliance = [
            "%s" % self.gtest_bin_path,
            "--gtest_filter=LogicalPartitionCompliance.GetVarIsLogical:LogicalPartitionCompliance.SuperPartition"
        ]
        retcode = subprocess.call(fastboot_gtest_cmd_logical_partition_compliance)
        asserts.assertTrue(retcode == 0, "Error in logical partition operations")

    def testFastbootReboot(self):
        """Runs fuzzy_fastboot to verify the commands to reboot into fastbootd and bootloader."""
        fastboot_gtest_cmd_reboot_test = [
            "%s" % self.gtest_bin_path,
            "--gtest_filter=LogicalPartitionCompliance.FastbootRebootTest"
        ]
        retcode = subprocess.call(fastboot_gtest_cmd_reboot_test)
        asserts.assertTrue(retcode == 0, "Error in fastbootd reboot test")

    def testLogicalPartitionFlashing(self):
        """Runs fuzzy_fastboot to verify the commands to reboot into fastbootd and bootloader."""
        fastboot_gtest_cmd_lp_flashing = [
            "%s" % self.gtest_bin_path, "--serial=%s" % self.dut.serial,
            "--gtest_filter=LogicalPartitionCompliance.CreateResizeDeleteLP"
        ]
        retcode = subprocess.call(fastboot_gtest_cmd_lp_flashing)
        asserts.assertTrue(retcode == 0, "Error in flashing logical partitions")

    def tearDownClass(self):
        """Reboot to Android."""
        if self.dut.isBootloaderMode:
            self.dut.reboot()
            self.dut.waitForBootCompletion()

if __name__ == "__main__":
    test_runner.main()
