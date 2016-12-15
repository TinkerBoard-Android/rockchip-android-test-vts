#!/usr/bin/env python3.4
#
# Copyright (C) 2016 The Android Open Source Project
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

import types
import threading
import re
import logging

from vts.runners.host import const
from vts.testcases.kernel.ltp.shell_environment import shell_commands


class ShellEnvironment(object):
    """Class for executing environment definition classes and do cleanup jobs.

    Attributes:
        shell: shell mirror object, shell to execute commands
        _cleanup_jobs: set of CheckSetupCleanup objects, a set used to store
                       clean up jobs if requested.
        _thread_lock: a threading.Lock object
    """

    def __init__(self, shell):
        self.shell = shell
        self._cleanup_jobs = []
        self._thread_lock = threading.Lock()

    def Cleanup(self):
        """Final cleanup jobs. Will run all the stored cleanup jobs"""
        return all([method(*args) for method, args in self._cleanup_jobs])

    def AddCleanupJob(self, method, *args):
        """Add a clean up job for final cleanup"""
        if (method, args) not in self._cleanup_jobs:
            self._cleanup_jobs.append((method, args))

    @property
    def shell(self):
        """returns an object that can execute a shell command"""
        return self._shell

    @shell.setter
    def shell(self, shell):
        self._shell = shell

    def ExecuteDefinitions(self, definitions):
        """Execute a given list of environment check definitions"""
        self._thread_lock.acquire()
        if not isinstance(definitions, types.ListType):
            definitions = [definitions]

        for definition in definitions:
            definition.context = self
            if not definition.Execute():
                self._thread_lock.release()
                return (False, definition.GetNote())

        self._thread_lock.release()
        return (True, "")

    def GetDevicePropCpuAbi(self):
        results = self.shell.Execute('{} | grep {}'.format(
            shell_commands.CMD_GETPROC, shell_commands.PROC_CPUABI))
        if (not results or results[const.EXIT_CODE][0] or
                not results[const.STDOUT][0]):
            logging.error("Cannot get cpu.abi info from device device."
                          "\n  Results: {}".format(results))
            return None
        else:
            return results[const.STDOUT][0]

    def IsDeviceArchArm64(self):
        """"Check whether the device's architecture is arm64"""
        result = self.GetDevicePropCpuAbi()
        if not result:
            return False
        else:
            return result.find("arm64") > 0

    def IsDeviceArchX86_64(self):
        """"Check whether the device's architecture is x86_64"""
        result = self.GetDevicePropCpuAbi()
        if not result:
            return False
        else:
            return result.find("x86_64") > 0

    def IsDeviceArchMips64(self):
        """"Check whether the device's architecture is mips64"""
        result = self.GetDevicePropCpuAbi()
        if not result:
            return False
        else:
            return result.find("mips64") > 0

    def IsDeviceArch64Bit(self):
        """Check whether device cpu is 64 bit."""
        return (self.IsDeviceArchArm64() or self.IsDeviceArchX86_64() or
                self.IsDeviceArchMips64())

    def GetDeviceNumberOfPresentCpu(self):
        """Get the number of available CPUs on target device"""
        results = self.shell.Execute('cat %s' %
                                     shell_commands.FILE_CPU_PRESENT)
        if (not results or results[const.EXIT_CODE][0] or
                not results[const.STDOUT][0]):
            logging.error("Cannot get number of working CPU info."
                          "\n  Command results: {}".format(results))
            return 1
        else:
            cpu_info = results[const.STDOUT][0].strip()
            m = re.match("[0-9]+-?[0-9]*", cpu_info)
            if m and m.span() == (0, len(cpu_info)):
                logging.info("spam" + str(m.span()))
                try:
                    return int(cpu_info.split('-')[-1]) + 1
                except Exception as e:
                    logging.error(e)

            logging.error("Cannot parse number of working CPU info."
                          "\n  CPU info: '{}'".format(cpu_info))
            return 1

    def CreateSedPattern(self, replace_from, replace_to):
        """Create a shell command to replace strings in given file list

        Args:
            replace_from: string, the string to search using sed
            replace_to: string, the replacement string for sed

        Returns:
            String, a sed pattern starting with 's' and ending with 'g',
            with a unique separator
        """
        separators = '/=+-:#\\'
        separator_avalibility = [c not in replace_from and c not in replace_to
                                 for c in separators]

        available_separator = [
            ch for ch, available in zip(separators, separator_avalibility)
            if available
        ]

        if not available_separator:
            logging.error('no pre-defined separator available for the given'
                          ' strings')
            return None

        separator = available_separator[0]
        return ("s{separator}{replace_from}{separator}"
                "{replace_to}{separator}g").format(
                    separator=separator,
                    replace_from=replace_from,
                    replace_to=replace_to)
