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

from tests.dell import enable, assert_running_config_contains_in_order, \
    configuring_vlan, configuring_interface_vlan, unconfigure_vlan, \
    ssh_protocol_factory, telnet_protocol_factory, configuring_a_vlan_on_interface, configuring_interface
from tests.util.protocol_util import with_protocol


class DellEnabledTest(unittest.TestCase):
    __test__ = False
    protocol_factory = ssh_protocol_factory

    def setUp(self):
        self.protocol = self.protocol_factory()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_exit_returns_to_unprivileged_mode(self, t):
        enable(t)
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch>")

    @with_protocol
    def test_quit_disconnects(self, t):
        enable(t)
        t.write(u"quit")
        t.read_eof()

    @with_protocol
    def test_write_memory(self, t):
        enable(t)

        t.write(u"copy running-config startup-config")

        t.readln(u"")
        t.readln(u"This operation may take a few minutes.")
        t.readln(u"Management interfaces will not be available during this time.")
        t.readln(u"")
        t.read(u"Are you sure you want to save? (y/n) ")
        t.write_raw(u"y")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Configuration Saved!")
        t.read(u"my_switch#")

    @with_protocol
    def test_write_memory_abort(self, t):
        enable(t)

        t.write(u"copy running-config startup-config")

        t.readln(u"")
        t.readln(u"This operation may take a few minutes.")
        t.readln(u"Management interfaces will not be available during this time.")
        t.readln(u"")
        t.read(u"Are you sure you want to save? (y/n) ")
        t.write_raw(u"n")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Configuration Not Saved!")
        t.read(u"my_switch#")

    @with_protocol
    def test_write_memory_any_other_key_aborts(self, t):
        enable(t)

        t.write(u"copy running-config startup-config")

        t.readln(u"")
        t.readln(u"This operation may take a few minutes.")
        t.readln(u"Management interfaces will not be available during this time.")
        t.readln(u"")
        t.read(u"Are you sure you want to save? (y/n) ")
        t.write_raw(u"p")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Configuration Not Saved!")
        t.read(u"my_switch#")

    @with_protocol
    def test_invalid_command(self, t):
        enable(t)

        t.write(u"shizzle")
        t.readln(u"          ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")

    @with_protocol
    def test_entering_configure_mode(self, t):
        enable(t)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_show_running_config_on_empty_ethernet_port(self, t):
        enable(t)

        t.write(u"show running-config interface ethernet 1/g1")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_show_running_config_on_ethernet_port_that_does_not_exists(self, t):
        enable(t)

        t.write(u"show running-config interface ethernet 4/g8")
        t.readln(u"")
        t.read(u"ERROR: Invalid input!")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_show_running_config_displays_header(self, t):
        enable(t)
        assert_running_config_contains_in_order(t, [
            u'!Current Configuration:',
            u'!System Description "PowerConnect 6224P, 3.3.7.3, VxWorks 6.5"',
            u'!System Software Version 3.3.7.3',
            u'!Cut-through mode is configured as disabled',
            u'!',
            u'configure',
        ])

    @with_protocol
    def test_show_vlan(self, t):
        enable(t)

        configuring_vlan(t, 10)
        configuring_vlan(t, 11)
        configuring_vlan(t, 12)
        configuring_vlan(t, 13)
        configuring_vlan(t, 14)
        configuring_vlan(t, 15)
        configuring_vlan(t, 16)
        configuring_vlan(t, 17)
        configuring_interface_vlan(t, 17, do=u"name this-name-is-too-long-buddy-budd")
        configuring_vlan(t, 18)
        configuring_vlan(t, 19)
        configuring_vlan(t, 20)
        configuring_vlan(t, 21)
        configuring_vlan(t, 22)
        configuring_vlan(t, 23)
        configuring_vlan(t, 24)
        configuring_vlan(t, 25)
        configuring_vlan(t, 26)
        configuring_vlan(t, 27)
        configuring_vlan(t, 28)
        configuring_vlan(t, 29)
        configuring_vlan(t, 300)
        configuring_vlan(t, 4000)
        configuring_interface_vlan(t, 300, do=u"name shizzle")

        t.write(u"show vlan")
        t.readln(u"")
        t.readln(u"VLAN       Name                         Ports          Type      Authorization")
        t.readln(u"-----  ---------------                  -------------  -----     -------------")
        t.readln(u"1      Default                                         Default   Required     ")
        t.readln(u"10                                                     Static    Required     ")
        t.readln(u"11                                                     Static    Required     ")
        t.readln(u"12                                                     Static    Required     ")
        t.readln(u"13                                                     Static    Required     ")
        t.readln(u"14                                                     Static    Required     ")
        t.readln(u"15                                                     Static    Required     ")
        t.readln(u"16                                                     Static    Required     ")
        t.readln(u"17     this-name-is-too-long-buddy-budd                Static    Required     ")
        t.readln(u"18                                                     Static    Required     ")
        t.readln(u"19                                                     Static    Required     ")
        t.readln(u"20                                                     Static    Required     ")
        t.readln(u"21                                                     Static    Required     ")
        t.readln(u"22                                                     Static    Required     ")
        t.readln(u"23                                                     Static    Required     ")
        t.readln(u"24                                                     Static    Required     ")
        t.readln(u"25                                                     Static    Required     ")
        t.readln(u"26                                                     Static    Required     ")
        t.readln(u"")
        t.read(u"--More-- or (q)uit")
        t.write_raw(u"m")
        t.readln(u"\r                     ")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"VLAN       Name                         Ports          Type      Authorization")
        t.readln(u"-----  ---------------                  -------------  -----     -------------")
        t.readln(u"27                                                     Static    Required     ")
        t.readln(u"28                                                     Static    Required     ")
        t.readln(u"29                                                     Static    Required     ")
        t.readln(u"300    shizzle                                         Static    Required     ")
        t.readln(u"4000                                                   Static    Required     ")
        t.readln(u"")
        t.read(u"my_switch#")

        unconfigure_vlan(t, 10)
        unconfigure_vlan(t, 11)
        unconfigure_vlan(t, 12)
        unconfigure_vlan(t, 13)
        unconfigure_vlan(t, 14)
        unconfigure_vlan(t, 15)
        unconfigure_vlan(t, 16)
        unconfigure_vlan(t, 17)
        unconfigure_vlan(t, 18)
        unconfigure_vlan(t, 19)
        unconfigure_vlan(t, 20)
        unconfigure_vlan(t, 21)
        unconfigure_vlan(t, 22)
        unconfigure_vlan(t, 23)
        unconfigure_vlan(t, 24)
        unconfigure_vlan(t, 25)
        unconfigure_vlan(t, 26)
        unconfigure_vlan(t, 27)
        unconfigure_vlan(t, 28)
        unconfigure_vlan(t, 29)
        unconfigure_vlan(t, 300)
        unconfigure_vlan(t, 4000)

    @with_protocol
    def test_show_vlan_id(self, t):
        enable(t)

        configuring_vlan(t, 1000)

        t.write(u"show vlan id 500")
        t.readln(u"")
        t.readln(u"ERROR: This VLAN does not exist.")
        t.readln(u"")
        t.read(u"my_switch#")

        t.write(u"show vlan id 1000")
        t.readln(u"")
        t.readln(u"VLAN       Name                         Ports          Type      Authorization")
        t.readln(u"-----  ---------------                  -------------  -----     -------------")
        t.readln(u"1000                                                   Static    Required     ")
        t.readln(u"")
        t.read(u"my_switch#")

        t.write(u"show vlan id bleh")
        t.readln(u"                     ^")
        t.readln(u"Invalid input. Please specify an integer in the range 1 to 4093.")
        t.readln(u"")
        t.read(u"my_switch#")

        t.write(u"show vlan id")
        t.readln(u"")
        t.readln(u"Command not found / Incomplete command. Use ? to list commands.")
        t.readln(u"")
        t.read(u"my_switch#")

        unconfigure_vlan(t, 1000)

    @with_protocol
    def test_show_vlan_id_with_ports(self, t):
        enable(t)

        configuring_vlan(t, 1000)
        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")
        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport access vlan 1000")

        t.write(u"show vlan id 1000")
        t.readln(u"")
        t.readln(u"VLAN       Name                         Ports          Type      Authorization")
        t.readln(u"-----  ---------------                  -------------  -----     -------------")
        t.readln(u"1000                                    1/g1           Static    Required     ")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode trunk")
        t.write(u"show vlan id 1000")
        t.readln(u"")
        t.readln(u"VLAN       Name                         Ports          Type      Authorization")
        t.readln(u"-----  ---------------                  -------------  -----     -------------")
        t.readln(u"1000                                                   Static    Required     ")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan add 1000")
        configuring_interface(t, u"ethernet 1/g2", do=u"switchport mode trunk")
        configuring_a_vlan_on_interface(t, u"ethernet 1/g2", do=u"switchport trunk allowed vlan add 1000")
        t.write(u"show vlan id 1000")
        t.readln(u"")
        t.readln(u"VLAN       Name                         Ports          Type      Authorization")
        t.readln(u"-----  ---------------                  -------------  -----     -------------")
        t.readln(u"1000                                    1/g1-1/g2      Static    Required     ")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_interface(t, u"ethernet 1/xg1", do=u"switchport mode trunk")
        configuring_a_vlan_on_interface(t, u"ethernet 1/xg1", do=u"switchport trunk allowed vlan add 1000")
        t.write(u"show vlan id 1000")
        t.readln(u"")
        t.readln(u"VLAN       Name                         Ports          Type      Authorization")
        t.readln(u"-----  ---------------                  -------------  -----     -------------")
        t.readln(u"1000                                    1/g1-1/g2,     Static    Required     ")
        t.readln(u"                                        1/xg1                                 ")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")
        configuring_interface(t, u"ethernet 1/g2", do=u"switchport mode access")
        configuring_interface(t, u"ethernet 1/xg1", do=u"switchport mode access")

        unconfigure_vlan(t, 1000)

    @with_protocol
    def test_show_version(self, t):
        enable(t)

        t.write(u"show version")

        t.readln(u"")
        t.readln(u"Image Descriptions")
        t.readln(u"")
        t.readln(u" image1 : default image")
        t.readln(u" image2 :")
        t.readln(u"")
        t.readln(u"")
        t.readln(u" Images currently available on Flash")
        t.readln(u"")
        t.readln(u"--------------------------------------------------------------------")
        t.readln(u" unit      image1      image2     current-active        next-active")
        t.readln(u"--------------------------------------------------------------------")
        t.readln(u"")
        t.readln(u"    1     3.3.7.3     3.3.7.3             image1             image1")
        t.readln(u"    2     3.3.7.3    3.3.13.1             image1             image1")
        t.readln(u"")

        t.read(u"my_switch#")


class DellEnabledSshTest(DellEnabledTest):
    __test__ = True
    protocol_factory = ssh_protocol_factory


class DellEnabledTelnetTest(DellEnabledTest):
    __test__ = True
    protocol_factory = telnet_protocol_factory
