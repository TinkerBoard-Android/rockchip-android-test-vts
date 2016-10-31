#!/usr/bin/env python
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

from setuptools import setup
from setuptools import find_packages
import sys

install_requires = [
    'future',
    'futures',
    'concurrent',
]

if sys.version_info < (3,):
    install_requires.append('enum34')

setup(
    name='vts',
    version='0.1',
    description='Android Vendor Test Suite',
    license='Apache2.0',
    packages=find_packages(),
    include_package_data=False,
    install_requires=install_requires,
    url="http://www.android.com/"
)
