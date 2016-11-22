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

from tests.dell import enable, configuring_vlan, \
    assert_running_config_contains_in_order, unconfigure_vlan, \
    assert_interface_configuration, ssh_protocol_factory,\
    telnet_protocol_factory
from tests.util.protocol_util import with_protocol


class DellConfigureVlanTest(unittest.TestCase):
    __test__ = False
    protocol_factory = None

    def setUp(self):
        self.protocol = self.protocol_factory()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_configuring_a_vlan(self, t):
        enable(t)

        configuring_vlan(t, 1234)

        assert_running_config_contains_in_order(t, [
            u"vlan database",
            u"vlan 1,1234",
            u"exit"
        ])

        unconfigure_vlan(t, 1234)

        assert_running_config_contains_in_order(t, [
            u"vlan database",
            u"vlan 1",
            u"exit"
        ])

    @with_protocol
    def test_unconfiguring_a_vlan_failing(self, t):
        enable(t)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"vlan database")
        t.readln(u"")
        t.read(u"my_switch(config-vlan)#")

        t.write(u"no vlan 3899")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"These VLANs do not exist:  3899.")
        t.readln(u"")

        t.read(u"my_switch(config-vlan)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_configuring_a_vlan_name(self, t):
        enable(t)

        configuring_vlan(t, 1234)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface vlan 1234")
        t.readln(u"")
        t.read(u"my_switch(config-if-vlan1234)#")
        t.write(u"name")
        t.readln(u"")
        t.readln(u"Command not found / Incomplete command. Use ? to list commands.")
        t.readln(u"")
        t.read(u"my_switch(config-if-vlan1234)#")
        t.write(u"name one two")
        t.readln(u"                                     ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-vlan1234)#")
        t.write(u"name this-name-is-too-long-buddy-buddy")
        t.readln(u"Name must be 32 characters or less.")
        t.readln(u"")
        t.read(u"my_switch(config-if-vlan1234)#")
        t.write(u"name this-name-is-too-long-buddy-budd")
        t.readln(u"")
        t.read(u"my_switch(config-if-vlan1234)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"vlan 1234", [
            u"interface vlan 1234",
            u"name \"this-name-is-too-long-buddy-budd\"",
            u"exit",
        ])

        unconfigure_vlan(t, 1234)


class DellConfigureVlanSshTest(DellConfigureVlanTest):
    __test__ = True
    protocol_factory = ssh_protocol_factory


class DellConfigureVlanTelnetTest(DellConfigureVlanTest):
    __test__ = True
    protocol_factory = telnet_protocol_factory
