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

from tests.dell10g import enable, assert_running_config_contains_in_order, \
    configuring_vlan, ssh_protocol_factory, telnet_protocol_factory, configuring, add_vlan, configuring_interface
from tests.util.protocol_util import with_protocol


class Dell10GEnabledTest(unittest.TestCase):
    __test__ = False
    protocol_factory = None

    def setUp(self):
        self.protocol = ssh_protocol_factory()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_terminal_length_0(self, t):
        enable(t)
        t.write(u"terminal length 0")
        t.readln(u"")
        t.read(u"my_switch#")

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
    def test_show_running_config_on_empty_ethernet_port(self, t):
        enable(t)

        t.write(u"show running-config interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_show_running_config_on_ethernet_port_that_does_not_exists(self, t):
        enable(t)

        t.write(u"show running-config interface tengigabitethernet 99/99/99")
        t.readln(u"")
        t.read(u"An invalid interface has been used for this function")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_show_running_config_displays_header(self, t):
        enable(t)
        assert_running_config_contains_in_order(t, [
            u'!Current Configuration:',
            u'!System Description "............."',
            u'!System Software Version 3.3.7.3',
            u'!Cut-through mode is configured as disabled',
            u'!',
            u'configure',
        ])

    @with_protocol
    def test_show_vlan(self, t):
        enable(t)

        add_vlan(t, 10)
        add_vlan(t, 11)
        add_vlan(t, 12)
        configuring_vlan(t, 17, do=u"name this-name-is-too-long-buddy-budd")
        add_vlan(t, 100)
        add_vlan(t, 1000)

        t.write(u"show vlan")
        t.readln(u"")
        t.readln(u"VLAN   Name                             Ports          Type")
        t.readln(u"-----  ---------------                  -------------  --------------")
        t.readln(u"1      default                                         Default")
        t.readln(u"10     VLAN10                                          Static")
        t.readln(u"11     VLAN11                                          Static")
        t.readln(u"12     VLAN12                                          Static")
        t.readln(u"17     this-name-is-too-long-buddy-budd                Static")
        t.readln(u"100    VLAN100                                         Static")
        t.readln(u"1000   VLAN1000                                        Static")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring(t, do=u"no vlan 10")
        configuring(t, do=u"no vlan 11")
        configuring(t, do=u"no vlan 12")
        configuring(t, do=u"no vlan 17")
        configuring(t, do=u"no vlan 100")
        configuring(t, do=u"no vlan 1000")


    @with_protocol
    def test_show_vlan_with_port(self, t):
        enable(t)

        add_vlan(t, 10)

        configuring_interface(t, u"tengigabitethernet 0/0/1", u"switchport mode trunk")
        configuring_interface(t, u"tengigabitethernet 0/0/1", u"switchport trunk allowed vlan 10")

        t.write(u"show vlan")
        t.readln(u"")
        t.readln(u"VLAN   Name                             Ports          Type")
        t.readln(u"-----  ---------------                  -------------  --------------")
        t.readln(u"1      default                                         Default")
        t.readln(u"10     VLAN10                           Te0/0/1        Static")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_interface(t, u"tengigabitethernet 0/0/1", u"switchport trunk allowed vlan remove 10")
        configuring_interface(t, u"tengigabitethernet 0/0/1", u"no switchport mode")
        configuring(t, do=u"no vlan 10")

    @with_protocol
    def test_show_vlan_with_ports(self, t):
        enable(t)

        add_vlan(t, 10)
        add_vlan(t, 11)

        configuring_interface(t, u"tengigabitethernet 0/0/1", u"switchport mode trunk")
        configuring_interface(t, u"tengigabitethernet 0/0/2", u"switchport mode trunk")
        configuring_interface(t, u"tengigabitethernet 1/0/2", u"switchport mode trunk")

        configuring_interface(t, u"tengigabitethernet 0/0/1", u"switchport trunk allowed vlan 10-11")
        configuring_interface(t, u"tengigabitethernet 0/0/2", u"switchport trunk allowed vlan 10")
        configuring_interface(t, u"tengigabitethernet 1/0/2", u"switchport trunk allowed vlan 11")

        t.write(u"show vlan")
        t.readln(u"")
        t.readln(u"VLAN   Name                             Ports          Type")
        t.readln(u"-----  ---------------                  -------------  --------------")
        t.readln(u"1      default                                         Default")
        t.readln(u"10     VLAN10                           Te0/0/1-2      Static")
        t.readln(u"11     VLAN11                           Te0/0/1,       Static")
        t.readln(u"                                        Te1/0/2        ")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_interface(t, u"tengigabitethernet 0/0/1", u"no switchport mode")
        configuring_interface(t, u"tengigabitethernet 0/0/2", u"no switchport mode")
        configuring_interface(t, u"tengigabitethernet 1/0/2", u"no switchport mode")

        configuring_interface(t, u"tengigabitethernet 0/0/1", u"switchport trunk allowed vlan remove 10,11")
        configuring_interface(t, u"tengigabitethernet 0/0/2", u"switchport trunk allowed vlan remove 10")
        configuring_interface(t, u"tengigabitethernet 1/0/2", u"switchport trunk allowed vlan remove 11")

        configuring(t, do=u"no vlan 10")
        configuring(t, do=u"no vlan 11")

    @with_protocol
    def test_show_vlan_id(self, t):
        enable(t)

        add_vlan(t, 1000)

        t.write(u"show vlan id 500")
        t.readln(u"")
        t.readln(u"ERROR: This VLAN does not exist.")
        t.readln(u"")
        t.read(u"my_switch#")

        t.write(u"show vlan id 1000")
        t.readln(u"")
        t.readln(u"VLAN   Name                             Ports          Type")
        t.readln(u"-----  ---------------                  -------------  --------------")
        t.readln(u"1000   VLAN1000                                        Static")
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

        configuring(t, do=u"no vlan 1000")


class Dell10GEnabledSshTest(Dell10GEnabledTest):
    __test__ = True
    protocol_factory = ssh_protocol_factory


class Dell10GEnabledTelnetTest(Dell10GEnabledTest):
    __test__ = True
    protocol_factory = telnet_protocol_factory
