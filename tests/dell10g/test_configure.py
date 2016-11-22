# Copyright 2015 Internap.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from flexmock import flexmock_teardown

from tests.dell10g import enable, ssh_protocol_factory, telnet_protocol_factory
from tests.util.protocol_util import with_protocol


class Dell10GConfigureTest(unittest.TestCase):
    __test__ = False
    protocol_factory = None

    def setUp(self):
        self.protocol = self.protocol_factory()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_entering_configure_unknown_interface_mode(self, t):
        enable(t)
        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"interface tengigabitethernet 1/0/99")
        t.readln(u"")
        t.readln(u"An invalid interface has been used for this function")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_entering_configure_unknown_vlan(self, t):
        enable(t)
        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"vlan 5000")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 1")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN 5000      ERROR: VLAN ID is out of range")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_entering_remove_unknown_vlan(self, t):
        enable(t)
        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"no vlan 3999")
        t.readln(u"")
        t.readln(u"These VLANs do not exist:  3999.")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")


class Dell10GConfigureSshTest(Dell10GConfigureTest):
    __test__ = True
    protocol_factory = ssh_protocol_factory 


class Dell10GConfigureTelnetTest(Dell10GConfigureTest):
    __test__ = True
    protocol_factory = telnet_protocol_factory
