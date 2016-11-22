# Copyright 2015-2016 Internap.
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
import mock

from tests.util.global_reactor import cisco_privileged_password
from tests.util.global_reactor import cisco_switch_ssh_port, cisco_switch_telnet_port, cisco_switch_ip
from tests.util.protocol_util import SshTester, TelnetTester, with_protocol


class TestCiscoSwitchProtocol(unittest.TestCase):
    __test__ = False

    def create_client(self):
        return SshTester(u"ssh", cisco_switch_ip, cisco_switch_ssh_port, u'root', u'root')

    def setUp(self):
        self.protocol = self.create_client()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_enable_command_requires_a_password(self, t):
        t.write(u"enable")
        t.read(u"Password: ")
        t.write_invisible(cisco_privileged_password)
        t.read(u"my_switch#")

    @with_protocol
    def test_wrong_password(self, t):
        t.write(u"enable")
        t.read(u"Password: ")
        t.write_invisible(u"hello_world")
        t.readln(u"% Access denied")
        t.readln(u"")
        t.read(u"my_switch>")

    @with_protocol
    def test_no_password_works_for_legacy_reasons(self, t):
        t.write(u"enable")
        t.read(u"Password: ")
        t.write_invisible(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_exiting_loses_the_connection(self, t):
        t.write(u"enable")
        t.read(u"Password: ")
        t.write_invisible(cisco_privileged_password)
        t.read(u"my_switch#")
        t.write(u"exit")
        t.read_eof()

    @with_protocol
    def test_no_such_command_return_to_prompt(self, t):
        enable(t)

        t.write(u"shizzle")
        t.readln(u"No such command : shizzle")
        t.read(u"my_switch#")

    @with_protocol
    @mock.patch(u"fake_switches.adapters.tftp_reader.read_tftp")
    def test_command_copy_failing(self, t, read_tftp):
        read_tftp.side_effect = Exception(u"Stuff")

        enable(t)

        t.write(u"copy tftp://1.2.3.4/my-file system:/running-config")
        t.read(u"Destination filename [running-config]? ")
        t.write(u"gneh")
        t.readln(u"Accessing tftp://1.2.3.4/my-file...")
        t.readln(u"Error opening tftp://1.2.3.4/my-file (Timed out)")
        t.read(u"my_switch#")

        read_tftp.assert_called_with(u"1.2.3.4", u"my-file")

    @with_protocol
    @mock.patch(u"fake_switches.adapters.tftp_reader.read_tftp")
    def test_command_copy_success(self, t, read_tftp):
        enable(t)

        t.write(u"copy tftp://1.2.3.4/my-file system:/running-config")
        t.read(u"Destination filename [running-config]? ")
        t.write_raw(u"\r")
        t.wait_for(u"\r\n")
        t.readln(u"Accessing tftp://1.2.3.4/my-file...")
        t.readln(u"Done (or some official message...)")
        t.read(u"my_switch#")

        read_tftp.assert_called_with(u"1.2.3.4", u"my-file")

    @with_protocol
    def test_command_show_run_int_vlan_empty(self, t):
        enable(t)

        t.write(u"terminal length 0")
        t.read(u"my_switch#")
        t.write(u"show run vlan 120")
        t.readln(u"Building configuration...")
        t.readln(u"")
        t.readln(u"Current configuration:")
        t.readln(u"end")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_command_add_vlan(self, t):
        enable(t)

        t.write(u"conf t")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"vlan 123")
        t.read(u"my_switch(config-vlan)#")
        t.write(u"name shizzle")
        t.read(u"my_switch(config-vlan)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")
        t.write(u"show run vlan 123")
        t.readln(u"Building configuration...")
        t.readln(u"")
        t.readln(u"Current configuration:")
        t.readln(u"!")
        t.readln(u"vlan 123")
        t.readln(u" name shizzle")
        t.readln(u"end")
        t.readln(u"")
        t.read(u"my_switch#")

        remove_vlan(t, u"123")

        t.write(u"show running-config vlan 123")
        t.readln(u"Building configuration...")
        t.readln(u"")
        t.readln(u"Current configuration:")
        t.readln(u"end")
        t.read(u"")

    @with_protocol
    def test_command_assign_access_vlan_to_port(self, t):
        enable(t)
        create_vlan(t, u"123")
        set_interface_on_vlan(t, u"FastEthernet0/1", u"123")

        assert_interface_configuration(t, u"Fa0/1", [
            u"interface FastEthernet0/1",
            u" switchport access vlan 123",
            u" switchport mode access",
            u"end"])

        configuring_interface(t, u"FastEthernet0/1", do=u"no switchport access vlan")

        assert_interface_configuration(t, u"Fa0/1", [
            u"interface FastEthernet0/1",
            u" switchport mode access",
            u"end"])

        configuring_interface(t, u"FastEthernet0/1", do=u"no switchport mode access")

        assert_interface_configuration(t, u"Fa0/1", [
            u"interface FastEthernet0/1",
            u"end"])

        remove_vlan(t, u"123")

    @with_protocol
    def test_show_vlan_brief(self, t):
        enable(t)
        create_vlan(t, u"123")
        create_vlan(t, u"3333", u"some-name")
        create_vlan(t, u"2222", u"your-name-is-way-too-long-for-this-pretty-printed-interface-man")

        set_interface_on_vlan(t, u"FastEthernet0/1", u"123")

        t.write(u"show vlan brief")
        t.readln(u"")
        t.readln(u"VLAN Name                             Status    Ports")
        t.readln(u"---- -------------------------------- --------- -------------------------------")
        t.readln(u"1    default                          active    Fa0/2, Fa0/3, Fa0/4")
        t.readln(u"123  VLAN123                          active    Fa0/1")
        t.readln(u"2222 your-name-is-way-too-long-for-th active")
        t.readln(u"3333 some-name                        active")
        t.read(u"my_switch#")

        revert_switchport_mode_access(t, u"FastEthernet0/1")
        remove_vlan(t, u"123")
        remove_vlan(t, u"2222")
        remove_vlan(t, u"3333")

    @with_protocol
    def test_show_vlan(self, t):
        enable(t)
        create_vlan(t, u"123")
        create_vlan(t, u"3333", u"some-name")
        create_vlan(t, u"2222", u"your-name-is-way-too-long-for-this-pretty-printed-interface-man")

        set_interface_on_vlan(t, u"FastEthernet0/1", u"123")

        t.write(u"show vlan")
        t.readln(u"")
        t.readln(u"VLAN Name                             Status    Ports")
        t.readln(u"---- -------------------------------- --------- -------------------------------")
        t.readln(u"1    default                          active    Fa0/2, Fa0/3, Fa0/4")
        t.readln(u"123  VLAN123                          active    Fa0/1")
        t.readln(u"2222 your-name-is-way-too-long-for-th active")
        t.readln(u"3333 some-name                        active")
        t.readln(u"")
        t.readln(u"VLAN Type  SAID       MTU   Parent RingNo BridgeNo Stp  BrdgMode Trans1 Trans2")
        t.readln(u"---- ----- ---------- ----- ------ ------ -------- ---- -------- ------ ------")
        t.readln(u"1    enet  100001     1500  -      -      -        -    -        0      0")
        t.readln(u"123  enet  100123     1500  -      -      -        -    -        0      0")
        t.readln(u"2222 enet  102222     1500  -      -      -        -    -        0      0")
        t.readln(u"3333 enet  103333     1500  -      -      -        -    -        0      0")
        t.readln(u"")
        t.readln(u"Remote SPAN VLANs")
        t.readln(u"------------------------------------------------------------------------------")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Primary Secondary Type              Ports")
        t.readln(u"------- --------- ----------------- ------------------------------------------")
        t.readln(u"")
        t.read(u"my_switch#")

        revert_switchport_mode_access(t, u"FastEthernet0/1")
        remove_vlan(t, u"123")
        remove_vlan(t, u"2222")
        remove_vlan(t, u"3333")

    @with_protocol
    def test_shutting_down(self, t):
        enable(t)

        configuring_interface(t, u"FastEthernet 0/3", do=u"shutdown")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" shutdown",
            u"end"])

        configuring_interface(t, u"FastEthernet 0/3", do=u"no shutdown")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u"end"])

    @with_protocol
    def test_configure_trunk_port(self, t):
        enable(t)

        configuring_interface(t, u"Fa0/3", do=u"switchport mode trunk")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport mode trunk",
            u"end"])

        # not really added because all vlan are in trunk by default on cisco
        configuring_interface(t, u"Fa0/3", do=u"switchport trunk allowed vlan add 123")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"switchport trunk allowed vlan none")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport trunk allowed vlan none",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"switchport trunk allowed vlan add 123")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport trunk allowed vlan 123",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"switchport trunk allowed vlan add 124,126-128")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport trunk allowed vlan 123,124,126-128",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"switchport trunk allowed vlan remove 123-124,127")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport trunk allowed vlan 126,128",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"switchport trunk allowed vlan all")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"switchport trunk allowed vlan 123-124,127")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport trunk allowed vlan 123,124,127",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"no switchport trunk allowed vlan")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" switchport mode trunk",
            u"end"])

        configuring_interface(t, u"Fa0/3", do=u"no switchport mode")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u"end"])

    @with_protocol
    def test_configure_native_vlan(self, t):
        enable(t)

        configuring_interface(t, u"FastEthernet0/2", do=u"switchport trunk native vlan 555")

        assert_interface_configuration(t, u"Fa0/2", [
            u"interface FastEthernet0/2",
            u" switchport trunk native vlan 555",
            u"end"])

        configuring_interface(t, u"FastEthernet0/2", do=u"no switchport trunk native vlan")

        assert_interface_configuration(t, u"Fa0/2", [
            u"interface FastEthernet0/2",
            u"end"])

    @with_protocol
    def test_setup_an_interface(self, t):
        enable(t)

        create_vlan(t, u"2999")
        create_interface_vlan(t, u"2999")
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"description hey ho")
        configuring_interface_vlan(t, u"2999", do=u"ip address 1.1.1.2 255.255.255.0")
        configuring_interface_vlan(t, u"2999", do=u"standby 1 ip 1.1.1.1")
        configuring_interface_vlan(t, u"2999", do=u'standby 1 timers 5 15')
        configuring_interface_vlan(t, u"2999", do=u'standby 1 priority 110')
        configuring_interface_vlan(t, u"2999", do=u'standby 1 preempt delay minimum 60')
        configuring_interface_vlan(t, u"2999", do=u'standby 1 authentication VLAN2999')
        configuring_interface_vlan(t, u"2999", do=u'standby 1 track 10 decrement 50')
        configuring_interface_vlan(t, u"2999", do=u'standby 1 track 20 decrement 50')

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" description hey ho",
            u" ip address 1.1.1.2 255.255.255.0",
            u" standby 1 ip 1.1.1.1",
            u" standby 1 timers 5 15",
            u" standby 1 priority 110",
            u" standby 1 preempt delay minimum 60",
            u" standby 1 authentication VLAN2999",
            u" standby 1 track 10 decrement 50",
            u" standby 1 track 20 decrement 50",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"ip address 2.2.2.2 255.255.255.0")
        configuring_interface_vlan(t, u"2999", do=u"standby 1 ip 2.2.2.1")
        configuring_interface_vlan(t, u"2999", do=u"standby 1 ip 2.2.2.3 secondary")
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 authentication")
        configuring_interface_vlan(t, u"2999", do=u"standby 1 preempt delay minimum 42")
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 priority")
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 timers")
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 track 10")

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" description hey ho",
            u" ip address 2.2.2.2 255.255.255.0",
            u" standby 1 ip 2.2.2.1",
            u" standby 1 ip 2.2.2.3 secondary",
            u" standby 1 preempt delay minimum 42",
            u" standby 1 track 20 decrement 50",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"no standby 1 ip 2.2.2.3")
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 preempt delay")
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 track 20")
        configuring_interface_vlan(t, u"2999", do=u"")
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" description hey ho",
            u" ip address 2.2.2.2 255.255.255.0",
            u" standby 1 ip 2.2.2.1",
            u" standby 1 preempt",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"no standby 1 ip 2.2.2.1")
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" description hey ho",
            u" ip address 2.2.2.2 255.255.255.0",
            u" standby 1 preempt",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"no standby 1")
        configuring_interface_vlan(t, u"2999", do=u"no description")
        configuring_interface_vlan(t, u"2999", do=u"")
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" ip address 2.2.2.2 255.255.255.0",
            u"end"])

        configuring(t, do=u"no interface vlan 2999")

        t.write(u"show run int vlan 2999")
        t.readln(u"\s*\^", regex=True)
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch#")

        remove_vlan(t, u"2999")

    @with_protocol
    def test_partial_standby_properties(self, t):
        enable(t)

        create_vlan(t, u"2999")
        create_interface_vlan(t, u"2999")
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u'standby 1 timers 5 15')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" standby 1 timers 5 15",
            u"end"])
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 timers")

        configuring_interface_vlan(t, u"2999", do=u'standby 1 priority 110')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" standby 1 priority 110",
            u"end"])
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 priority")

        configuring_interface_vlan(t, u"2999", do=u'standby 1 preempt delay minimum 60')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" standby 1 preempt delay minimum 60",
            u"end"])
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 preempt")

        configuring_interface_vlan(t, u"2999", do=u'standby 1 authentication VLAN2999')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" standby 1 authentication VLAN2999",
            u"end"])
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 authentication")

        configuring_interface_vlan(t, u"2999", do=u'standby 1 track 10 decrement 50')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" standby 1 track 10 decrement 50",
            u"end"])
        configuring_interface_vlan(t, u"2999", do=u"no standby 1 track 10")

        configuring(t, do=u"no interface vlan 2999")
        remove_vlan(t, u"2999")

    @with_protocol
    def test_partial_standby_ip_definition(self, t):
        enable(t)

        create_vlan(t, u"2999")
        create_interface_vlan(t, u"2999")

        configuring_interface_vlan(t, u"2999", do=u'standby 1 ip')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" standby 1 ip",
            u"end"])
        configuring_interface_vlan(t, u"2999", do=u'no standby 1 ip')

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface vlan 2999")
        t.read(u"my_switch(config-if)#")

        t.write(u"standby 1 ip 1..1.1")
        t.readln(u" ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if)#")

        t.write(u"standby 1 ip 1.1.1.1")
        t.readln(u"% Warning: address is not within a subnet on this interface")

        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"ip address 1.1.1.2 255.255.255.0")

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface vlan 2999")
        t.read(u"my_switch(config-if)#")

        t.write(u"standby 1 ip 2.1.1.1")
        t.readln(u"% Warning: address is not within a subnet on this interface")

        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        configuring_interface_vlan(t, u"2999", do=u'standby 1 ip 1.1.1.1')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" ip address 1.1.1.2 255.255.255.0",
            u" standby 1 ip 1.1.1.1",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u'standby 1 ip')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" ip address 1.1.1.2 255.255.255.0",
            u" standby 1 ip 1.1.1.1",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"no ip address 1.1.1.2 255.255.255.0")
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" standby 1 ip 1.1.1.1",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u'no standby 1 ip 1.1.1.1')
        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u"end"])

        configuring(t, do=u"no interface vlan 2999")
        remove_vlan(t, u"2999")

    @with_protocol
    def test_creating_a_port_channel(self, t):
        enable(t)

        create_port_channel_interface(t, u'1')
        configuring_port_channel(t, u'1', u'description HELLO')
        configuring_port_channel(t, u'1', u'switchport trunk encapsulation dot1q')
        configuring_port_channel(t, u'1', u'switchport trunk native vlan 998')
        configuring_port_channel(t, u'1', u'switchport trunk allowed vlan 6,4087-4089,4091,4093')
        configuring_port_channel(t, u'1', u'switchport mode trunk')

        assert_interface_configuration(t, u'Port-channel1', [
            u"interface Port-channel1",
            u" description HELLO",
            u" switchport trunk encapsulation dot1q",
            u" switchport trunk native vlan 998",
            u" switchport trunk allowed vlan 6,4087-4089,4091,4093",
            u" switchport mode trunk",
            u"end"
        ])

        t.write(u"show etherchannel summary")
        t.readln(u"Flags:  D - down        P - bundled in port-channel")
        t.readln(u"        I - stand-alone s - suspended")
        t.readln(u"        H - Hot-standby (LACP only)")
        t.readln(u"        R - Layer3      S - Layer2")
        t.readln(u"        U - in use      f - failed to allocate aggregator")
        t.readln(u"")
        t.readln(u"        M - not in use, minimum links not met")
        t.readln(u"        u - unsuitable for bundling")
        t.readln(u"        w - waiting to be aggregated")
        t.readln(u"        d - default port")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Number of channel-groups in use: 1")
        t.readln(u"Number of aggregators:           1")
        t.readln(u"")
        t.readln(u"Group  Port-channel  Protocol    Ports")
        t.readln(u"------+-------------+-----------+-----------------------------------------------")
        t.readln(u"1      Po1(S)          LACP      ")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring(t, do=u"no interface port-channel 1")

        t.write(u"show run int po1")
        t.readln(u"\s*\^", regex=True)
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_port_channel_is_automatically_created_when_adding_a_port_to_it(self, t):
        enable(t)

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface FastEthernet0/1")
        t.read(u"my_switch(config-if)#")
        t.write(u"channel-group 2 mode active")
        t.readln(u"Creating a port-channel interface Port-channel 2")
        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'fa0/1', [
            u"interface FastEthernet0/1",
            u" channel-group 2 mode active",
            u"end"
        ])

        assert_interface_configuration(t, u'po2', [
            u"interface Port-channel2",
            u"end"
        ])

        t.write(u"show etherchannel summary")
        t.readln(u"Flags:  D - down        P - bundled in port-channel")
        t.readln(u"        I - stand-alone s - suspended")
        t.readln(u"        H - Hot-standby (LACP only)")
        t.readln(u"        R - Layer3      S - Layer2")
        t.readln(u"        U - in use      f - failed to allocate aggregator")
        t.readln(u"")
        t.readln(u"        M - not in use, minimum links not met")
        t.readln(u"        u - unsuitable for bundling")
        t.readln(u"        w - waiting to be aggregated")
        t.readln(u"        d - default port")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Number of channel-groups in use: 1")
        t.readln(u"Number of aggregators:           1")
        t.readln(u"")
        t.readln(u"Group  Port-channel  Protocol    Ports")
        t.readln(u"------+-------------+-----------+-----------------------------------------------")
        t.readln(u"2      Po2(SU)         LACP      Fa0/1(P)")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring(t, do=u"no interface port-channel 2")

        configuring_interface(t, interface=u"fa0/1", do=u"no channel-group 2 mode on")

        assert_interface_configuration(t, u"fa0/1", [
            u"interface FastEthernet0/1",
            u"end"
        ])

    @with_protocol
    def test_port_channel_is_not_automatically_created_when_adding_a_port_to_it_if_its_already_created(self, t):
        enable(t)

        create_port_channel_interface(t, u'14')

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface FastEthernet0/1")
        t.read(u"my_switch(config-if)#")
        t.write(u"channel-group 14 mode active")
        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"fa0/1", [
            u"interface FastEthernet0/1",
            u" channel-group 14 mode active",
            u"end"
        ])

        configuring_interface(t, interface=u"fa0/1", do=u"no channel-group 14 mode on")

        assert_interface_configuration(t, u"fa0/1", [
            u"interface FastEthernet0/1",
            u"end"
        ])

        configuring(t, do=u"no interface port-channel 14")

    @with_protocol
    def test_setting_secondary_ips(self, t):
        enable(t)

        create_interface_vlan(t, u"2999")
        configuring_interface_vlan(t, u"2999", do=u"description hey ho")
        configuring_interface_vlan(t, u"2999", do=u"no ip redirects")
        configuring_interface_vlan(t, u"2999", do=u"ip address 1.1.1.1 255.255.255.0")
        configuring_interface_vlan(t, u"2999", do=u"ip address 2.2.2.1 255.255.255.0 secondary")
        configuring_interface_vlan(t, u"2999", do=u"ip address 4.4.4.1 255.255.255.0 secondary")
        configuring_interface_vlan(t, u"2999", do=u"ip address 3.3.3.1 255.255.255.0 secondary")

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" description hey ho",
            u" ip address 2.2.2.1 255.255.255.0 secondary",
            u" ip address 4.4.4.1 255.255.255.0 secondary",
            u" ip address 3.3.3.1 255.255.255.0 secondary",
            u" ip address 1.1.1.1 255.255.255.0",
            u" no ip redirects",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"no ip address")
        configuring_interface_vlan(t, u"2999", do=u"ip redirects")

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" description hey ho",
            u" no ip address",
            u"end"])

        configuring(t, do=u"no interface vlan 2999")

    @with_protocol
    def test_setting_access_group(self, t):
        enable(t)

        create_interface_vlan(t, u"2999")
        configuring_interface_vlan(t, u"2999", do=u"ip access-group SHNITZLE in")
        configuring_interface_vlan(t, u"2999", do=u"ip access-group WHIZZLE out")

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u" ip access-group SHNITZLE in",
            u" ip access-group WHIZZLE out",
            u"end"])

        configuring_interface_vlan(t, u"2999", do=u"no ip access-group in")
        configuring_interface_vlan(t, u"2999", do=u"no ip access-group WHIZZLE out")

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u"end"])

        configuring(t, do=u"no interface vlan 2999")

    @with_protocol
    def test_removing_ip_address(self, t):
        enable(t)

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface vlan2999")
        t.read(u"my_switch(config-if)#")
        t.write(u"ip address 1.1.1.1 255.255.255.0")
        t.read(u"my_switch(config-if)#")
        t.write(u"ip address 2.2.2.2 255.255.255.0 secondary")
        t.read(u"my_switch(config-if)#")
        t.write(u"no ip address 1.1.1.1 255.255.255.0")
        t.readln(u"Must delete secondary before deleting primary")
        t.read(u"my_switch(config-if)#")
        t.write(u"no ip address 2.2.2.2 255.255.255.0 secondary")
        t.read(u"my_switch(config-if)#")
        t.write(u"no ip address 1.1.1.1 255.255.255.0")
        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"Vlan2999", [
            u"interface Vlan2999",
            u" no ip address",
            u"end"])

        configuring(t, do=u"no interface vlan 2999")

    @with_protocol
    def test_show_ip_interfaces(self, t):
        enable(t)

        create_vlan(t, u"1000")
        create_interface_vlan(t, u"1000")
        create_vlan(t, u"2000")
        create_vlan(t, u"3000")
        create_interface_vlan(t, u"3000")
        configuring_interface_vlan(t, u"3000", do=u"ip address 1.1.1.1 255.255.255.0")

        create_interface_vlan(t, u"4000")
        configuring_interface_vlan(t, u"4000", do=u"ip vrf forwarding DEFAULT-LAN")
        configuring_interface_vlan(t, u"4000", do=u"ip address 2.2.2.2 255.255.255.0")
        configuring_interface_vlan(t, u"4000", do=u"ip address 4.2.2.2 255.255.255.0 secondary")
        configuring_interface_vlan(t, u"4000", do=u"ip address 3.2.2.2 255.255.255.0 secondary")
        configuring_interface_vlan(t, u"4000", do=u"ip address 3.2.2.2 255.255.255.128 secondary")
        configuring_interface_vlan(t, u"4000", do=u"ip access-group shizzle in")
        configuring_interface_vlan(t, u"4000", do=u"ip access-group whizzle out")

        t.write(u"show ip interface")
        t.readln(u"Vlan1000 is down, line protocol is down")
        t.readln(u"  Internet protocol processing disabled")
        t.readln(u"Vlan3000 is down, line protocol is down")
        t.readln(u"  Internet address is 1.1.1.1/24")
        t.readln(u"  Outgoing access list is not set")
        t.readln(u"  Inbound  access list is not set")
        t.readln(u"Vlan4000 is down, line protocol is down")
        t.readln(u"  Internet address is 2.2.2.2/24")
        t.readln(u"  Secondary address 4.2.2.2/24")
        t.readln(u"  Secondary address 3.2.2.2/25")
        t.readln(u"  Outgoing access list is whizzle")
        t.readln(u"  Inbound  access list is shizzle")
        t.readln(u"  VPN Routing/Forwarding \"DEFAULT-LAN\"")
        t.readln(u"FastEthernet0/1 is down, line protocol is down")
        t.readln(u"  Internet protocol processing disabled")
        t.readln(u"FastEthernet0/2 is down, line protocol is down")
        t.readln(u"  Internet protocol processing disabled")
        t.readln(u"FastEthernet0/3 is down, line protocol is down")
        t.readln(u"  Internet protocol processing disabled")
        t.readln(u"FastEthernet0/4 is down, line protocol is down")
        t.readln(u"  Internet protocol processing disabled")
        t.read(u"my_switch#")

        t.write(u"show ip interface vlan 4000")
        t.readln(u"Vlan4000 is down, line protocol is down")
        t.readln(u"  Internet address is 2.2.2.2/24")
        t.readln(u"  Secondary address 4.2.2.2/24")
        t.readln(u"  Secondary address 3.2.2.2/25")
        t.readln(u"  Outgoing access list is whizzle")
        t.readln(u"  Inbound  access list is shizzle")
        t.readln(u"  VPN Routing/Forwarding \"DEFAULT-LAN\"")
        t.read(u"my_switch#")

        t.write(u"show ip interface vlan1000")
        t.readln(u"Vlan1000 is down, line protocol is down")
        t.readln(u"  Internet protocol processing disabled")
        t.read(u"my_switch#")

        configuring(t, do=u"no interface vlan 1000")
        configuring(t, do=u"no interface vlan 3000")
        configuring(t, do=u"no interface vlan 4000")

        remove_vlan(t, u"1000")
        remove_vlan(t, u"2000")
        remove_vlan(t, u"3000")

    @with_protocol
    def test_assigning_a_secondary_ip_as_the_primary_removes_it_from_secondary_and_removes_the_primary(self, t):
        enable(t)

        create_interface_vlan(t, u"4000")
        configuring_interface_vlan(t, u"4000", do=u"ip address 2.2.2.2 255.255.255.0")
        configuring_interface_vlan(t, u"4000", do=u"ip address 4.2.2.2 255.255.255.0 secondary")
        configuring_interface_vlan(t, u"4000", do=u"ip address 3.2.2.2 255.255.255.0 secondary")
        configuring_interface_vlan(t, u"4000", do=u"ip address 3.2.2.2 255.255.255.128")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" ip address 4.2.2.2 255.255.255.0 secondary",
            u" ip address 3.2.2.2 255.255.255.128",
            u"end"])

        configuring(t, do=u"no interface vlan 4000")

    @with_protocol
    def test_overlapping_ips(self, t):
        enable(t)

        create_vlan(t, u"1000")
        create_interface_vlan(t, u"1000")
        create_vlan(t, u"2000")
        create_interface_vlan(t, u"2000")

        configuring_interface_vlan(t, u"1000", do=u"ip address 2.2.2.2 255.255.255.0")
        configuring_interface_vlan(t, u"1000", do=u"ip address 3.3.3.3 255.255.255.0 secondary")

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface vlan2000")
        t.read(u"my_switch(config-if)#")

        t.write(u"ip address 2.2.2.75 255.255.255.128")
        t.readln(u"% 2.2.2.0 overlaps with secondary address on Vlan1000")
        t.read(u"my_switch(config-if)#")

        t.write(u"ip address 3.3.3.4 255.255.255.128")
        t.readln(u"% 3.3.3.0 is assigned as a secondary address on Vlan1000")
        t.read(u"my_switch(config-if)#")

        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        configuring(t, do=u"no interface vlan 2000")
        remove_vlan(t, u"2000")
        configuring(t, do=u"no interface vlan 1000")
        remove_vlan(t, u"1000")

    @with_protocol
    def test_unknown_ip_interface(self, t):
        enable(t)

        t.write(u"show ip interface Vlan2345")
        t.readln(u"                                 ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_removing_ip_needs_to_compare_objects_better(self, t):
        enable(t)

        create_vlan(t, u"1000")
        create_interface_vlan(t, u"1000")

        configuring_interface_vlan(t, u"1000", do=u"ip address 1.1.1.1 255.255.255.0")
        configuring_interface_vlan(t, u"1000", do=u"ip address 1.1.1.2 255.255.255.0 secondary")
        configuring_interface_vlan(t, u"1000", do=u"ip address 1.1.1.3 255.255.255.0 secondary")

        configuring_interface_vlan(t, u"1000", do=u"no ip address 1.1.1.3 255.255.255.0 secondary")

        t.write(u"show ip interface vlan 1000")
        t.readln(u"Vlan1000 is down, line protocol is down")
        t.readln(u"  Internet address is 1.1.1.1/24")
        t.readln(u"  Secondary address 1.1.1.2/24")
        t.readln(u"  Outgoing access list is not set")
        t.readln(u"  Inbound  access list is not set")
        t.read(u"my_switch#")

        configuring(t, do=u"no interface vlan 1000")
        remove_vlan(t, u"1000")

    @with_protocol
    def test_extreme_vlan_range(self, t):
        enable(t)

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")

        t.write(u"vlan -1")
        t.readln(u"Command rejected: Bad VLAN list - character #1 ('-') delimits a VLAN number")
        t.readln(u" which is out of the range 1..4094.")
        t.read(u"my_switch(config)#")

        t.write(u"vlan 0")
        t.readln(u"Command rejected: Bad VLAN list - character #X (EOL) delimits a VLAN")
        t.readln(u"number which is out of the range 1..4094.")
        t.read(u"my_switch(config)#")

        t.write(u"vlan 1")
        t.read(u"my_switch(config-vlan)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")

        t.write(u"vlan 4094")
        t.read(u"my_switch(config-vlan)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"no vlan 4094")
        t.read(u"my_switch(config)#")

        t.write(u"vlan 4095")
        t.readln(u"Command rejected: Bad VLAN list - character #X (EOL) delimits a VLAN")
        t.readln(u"number which is out of the range 1..4094.")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.read(u"my_switch#")

    @with_protocol
    def test_full_running_config_and_pipe_begin_support(self, t):
        enable(t)

        create_vlan(t, u"1000", name=u"hello")
        create_interface_vlan(t, u"1000")
        configuring_interface(t, u"Fa0/2", do=u"switchport mode trunk")
        configuring_interface(t, u"Fa0/2", do=u"switchport trunk allowed vlan 125")

        t.write(u"show running | beg vlan")
        t.readln(u"vlan 1")
        t.readln(u"!")
        t.readln(u"vlan 1000")
        t.readln(u" name hello")
        t.readln(u"!")
        t.readln(u"interface FastEthernet0/1")
        t.readln(u"!")
        t.readln(u"interface FastEthernet0/2")
        t.readln(u" switchport trunk allowed vlan 125")
        t.readln(u" switchport mode trunk")
        t.readln(u"!")
        t.readln(u"interface FastEthernet0/3")
        t.readln(u"!")
        t.readln(u"interface FastEthernet0/4")
        t.readln(u"!")
        t.readln(u"interface Vlan1000")
        t.readln(u" no ip address")
        t.readln(u"!")
        t.readln(u"end")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_interface(t, u"Fa0/2", do=u"no switchport mode trunk")
        configuring_interface(t, u"Fa0/2", do=u"no switchport trunk allowed vlan")
        configuring(t, do=u"no interface vlan 1000")
        remove_vlan(t, u"1000")

    @with_protocol
    def test_pipe_inc_support(self, t):
        enable(t)

        create_vlan(t, u"1000", name=u"hello")

        t.write(u"show running | inc vlan")
        t.readln(u"vlan 1")
        t.readln(u"vlan 1000")
        t.read(u"my_switch#")

        remove_vlan(t, u"1000")

    @with_protocol
    def test_ip_vrf(self, t):
        enable(t)

        t.write(u"conf t")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"ip vrf SOME-LAN")
        t.read(u"my_switch(config-vrf)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"no ip vrf SOME-LAN")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

    @with_protocol
    def test_ip_vrf_forwarding(self, t):
        enable(t)

        t.write(u"conf t")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"ip vrf SOME-LAN")
        t.read(u"my_switch(config-vrf)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")

        t.write(u"interface Fa0/2")
        t.read(u"my_switch(config-if)#")
        t.write(u"ip vrf forwarding NOT-DEFAULT-LAN")
        t.readln(u"% VRF NOT-DEFAULT-LAN not configured.")
        t.read(u"my_switch(config-if)#")

        t.write(u"ip vrf forwarding SOME-LAN")
        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"Fa0/2", [
            u"interface FastEthernet0/2",
            u" ip vrf forwarding SOME-LAN",
            u"end"])

        t.write(u"conf t")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"no ip vrf SOME-LAN")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"Fa0/2", [
            u"interface FastEthernet0/2",
            u"end"])

    @with_protocol
    def test_ip_vrf_default_lan(self, t):
        enable(t)

        t.write(u"conf t")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")

        t.write(u"interface Fa0/2")
        t.read(u"my_switch(config-if)#")
        t.write(u"ip vrf forwarding DEFAULT-LAN")
        t.read(u"my_switch(config-if)#")

        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"Fa0/2", [
            u"interface FastEthernet0/2",
            u" ip vrf forwarding DEFAULT-LAN",
            u"end"])

        t.write(u"conf t")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface Fa0/2")
        t.read(u"my_switch(config-if)#")
        t.write(u"no ip vrf forwarding")
        t.read(u"my_switch(config-if)#")

        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"Fa0/2", [
            u"interface FastEthernet0/2",
            u"end"])

    @with_protocol
    def test_ip_setting_vrf_forwarding_wipes_ip_addresses(self, t):
        enable(t)

        create_vlan(t, u"4000")
        create_interface_vlan(t, u"4000")
        configuring_interface_vlan(t, u"4000", do=u"ip address 10.10.0.10 255.255.255.0")
        configuring_interface_vlan(t, u"4000", do=u"ip address 10.10.1.10 255.255.255.0 secondary")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" ip address 10.10.1.10 255.255.255.0 secondary",
            u" ip address 10.10.0.10 255.255.255.0",
            u"end"])

        configuring_interface_vlan(t, u"4000", do=u"ip vrf forwarding DEFAULT-LAN")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" ip vrf forwarding DEFAULT-LAN",
            u" no ip address",
            u"end"])

        configuring(t, do=u"no interface vlan 4000")
        remove_vlan(t, u"4000")

    @with_protocol
    def test_ip_helper(self, t):
        enable(t)

        create_interface_vlan(t, u"4000")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" no ip address",
            u"end"])

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface vlan 4000")
        t.read(u"my_switch(config-if)#")
        t.write(u"ip helper-address")
        t.readln(u"% Incomplete command.")
        t.readln(u"")
        t.read(u"my_switch(config-if)#")

        t.write(u"ip helper-address 10.10.0.1 EXTRA INFO")
        t.readln(u" ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        configuring_interface_vlan(t, u"4000", do=u"ip helper-address 10.10.10.1")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" no ip address",
            u" ip helper-address 10.10.10.1",
            u"end"])

        configuring_interface_vlan(t, u"4000", do=u"ip helper-address 10.10.10.1")
        configuring_interface_vlan(t, u"4000", do=u"ip helper-address 10.10.10.2")
        configuring_interface_vlan(t, u"4000", do=u"ip helper-address 10.10.10.3")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" no ip address",
            u" ip helper-address 10.10.10.1",
            u" ip helper-address 10.10.10.2",
            u" ip helper-address 10.10.10.3",
            u"end"])

        configuring_interface_vlan(t, u"4000", do=u"no ip helper-address 10.10.10.1")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" no ip address",
            u" ip helper-address 10.10.10.2",
            u" ip helper-address 10.10.10.3",
            u"end"])

        configuring_interface_vlan(t, u"4000", do=u"no ip helper-address 10.10.10.1")

        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"interface vlan 4000")
        t.read(u"my_switch(config-if)#")
        t.write(u"no ip helper-address 10.10.0.1 EXTRA INFO")
        t.readln(u" ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if)#")
        t.write(u"exit")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

        configuring_interface_vlan(t, u"4000", do=u"no ip helper-address")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface Vlan4000",
            u" no ip address",
            u"end"])

        configuring(t, do=u"no interface vlan 4000")

    @with_protocol
    def test_ip_route(self, t):
        enable(t)
        configuring(t, do=u"ip route 1.1.1.0 255.255.255.0 2.2.2.2")

        t.write(u"show ip route static | inc 2.2.2.2")
        t.readln(u"S        1.1.1.0 [x/y] via 2.2.2.2")
        t.read(u"my_switch#")

        t.write(u"show running | inc 2.2.2.2")
        t.readln(u"ip route 1.1.1.0 255.255.255.0 2.2.2.2")
        t.read(u"my_switch#")

        configuring(t, do=u"no ip route 1.1.1.0 255.255.255.0 2.2.2.2")

        t.write(u"show ip route static")
        t.readln(u"")
        t.read(u"my_switch#")
        t.write(u"exit")

    @with_protocol
    def test_write_memory(self, t):
        enable(t)

        t.write(u"write memory")
        t.readln(u"Building configuration...")
        t.readln(u"OK")
        t.read(u"my_switch#")

    @with_protocol
    def test_show_version(self, t):
        enable(t)

        t.write(u"show version")
        t.readln(u"Cisco IOS Software, C3750 Software (C3750-IPSERVICESK9-M), Version 12.2(58)SE2, RELEASE SOFTWARE (fc1)")
        t.readln(u"Technical Support: http://www.cisco.com/techsupport")
        t.readln(u"Copyright (c) 1986-2011 by Cisco Systems, Inc.")
        t.readln(u"Compiled Thu 21-Jul-11 01:53 by prod_rel_team")
        t.readln(u"")
        t.readln(u"ROM: Bootstrap program is C3750 boot loader")
        t.readln(u"BOOTLDR: C3750 Boot Loader (C3750-HBOOT-M) Version 12.2(44)SE5, RELEASE SOFTWARE (fc1)")
        t.readln(u"")
        t.readln(u"my_switch uptime is 1 year, 18 weeks, 5 days, 1 hour, 11 minutes")
        t.readln(u"System returned to ROM by power-on")
        t.readln(u"System image file is \"flash:c3750-ipservicesk9-mz.122-58.SE2.bin\"")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"This product contains cryptographic features and is subject to United")
        t.readln(u"States and local country laws governing import, export, transfer and")
        t.readln(u"use. Delivery of Cisco cryptographic products does not imply")
        t.readln(u"third-party authority to import, export, distribute or use encryption.")
        t.readln(u"Importers, exporters, distributors and users are responsible for")
        t.readln(u"compliance with U.S. and local country laws. By using this product you")
        t.readln(u"agree to comply with applicable laws and regulations. If you are unable")
        t.readln(u"to comply with U.S. and local laws, return this product immediately.")
        t.readln(u"")
        t.readln(u"A summary of U.S. laws governing Cisco cryptographic products may be found at:")
        t.readln(u"http://www.cisco.com/wwl/export/crypto/tool/stqrg.html")
        t.readln(u"")
        t.readln(u"If you require further assistance please contact us by sending email to")
        t.readln(u"export@cisco.com.")
        t.readln(u"")
        t.readln(u"cisco WS-C3750G-24TS-1U (PowerPC405) processor (revision H0) with 131072K bytes of memory.")
        t.readln(u"Processor board ID FOC1530X2F7")
        t.readln(u"Last reset from power-on")
        t.readln(u"0 Virtual Ethernet interfaces")
        t.readln(u"4 Gigabit Ethernet interfaces")
        t.readln(u"The password-recovery mechanism is enabled.")
        t.readln(u"")
        t.readln(u"512K bytes of flash-simulated non-volatile configuration memory.")
        t.readln(u"Base ethernet MAC Address       : 00:00:00:00:00:00")
        t.readln(u"Motherboard assembly number     : 73-10219-09")
        t.readln(u"Power supply part number        : 341-0098-02")
        t.readln(u"Motherboard serial number       : FOC153019Z6")
        t.readln(u"Power supply serial number      : ALD153000BB")
        t.readln(u"Model revision number           : H0")
        t.readln(u"Motherboard revision number     : A0")
        t.readln(u"Model number                    : WS-C3750G-24TS-S1U")
        t.readln(u"System serial number            : FOC1530X2F7")
        t.readln(u"Top Assembly Part Number        : 800-26859-03")
        t.readln(u"Top Assembly Revision Number    : C0")
        t.readln(u"Version ID                      : V05")
        t.readln(u"CLEI Code Number                : COMB600BRA")
        t.readln(u"Hardware Board Revision Number  : 0x09")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Switch Ports Model              SW Version            SW Image")
        t.readln(u"------ ----- -----              ----------            ----------")
        t.readln(u"*    1 4     WS-C3750G-24TS-1U  12.2(58)SE2           C3750-IPSERVICESK9-M")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Configuration register is 0xF")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_reset_port(self, t):
        enable(t)

        configuring_interface(t, u"FastEthernet0/3", do=u"description shizzle the whizzle and drizzle with lizzle")
        configuring_interface(t, u"FastEthernet0/3", do=u"shutdown")
        set_interface_on_vlan(t, u"FastEthernet0/3", u"123")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u" description shizzle the whizzle and drizzle with lizzle",
            u" switchport access vlan 123",
            u" switchport mode access",
            u" shutdown",
            u"end"])

        configuring(t, u"default interface FastEthernet0/3")

        assert_interface_configuration(t, u"FastEthernet0/3", [
            u"interface FastEthernet0/3",
            u"end"])

    @with_protocol
    def test_reset_port_invalid_interface_fails(self, t):
        enable(t)

        configuring_interface(t, u"FastEthernet0/3", do=u"description shizzle the whizzle and drizzle with lizzle")

        t.write(u"conf t")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")

        t.write(u"default interface WrongInterfaceName0/3")

        t.readln(u"\s*\^", regex=True)
        t.readln(u"% Invalid input detected at '^' marker (not such interface)")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        configuring(t, u"default interface FastEthernet0/3")


def enable(t):
    t.write(u"enable")
    t.read(u"Password: ")
    t.write_invisible(cisco_privileged_password)
    t.read(u"my_switch#")


def create_vlan(t, vlan, name=None):
    t.write(u"configure terminal")
    t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
    t.read(u"my_switch(config)#")
    t.write(u"vlan %s" % vlan)
    t.read(u"my_switch(config-vlan)#")
    if name:
        t.write(u"name %s" % name)
        t.read(u"my_switch(config-vlan)#")
    t.write(u"exit")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.read(u"my_switch#")


def create_interface_vlan(t, vlan):
    t.write(u"configure terminal")
    t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
    t.read(u"my_switch(config)#")
    t.write(u"interface vlan %s" % vlan)
    t.read(u"my_switch(config-if)#")
    t.write(u"exit")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.read(u"my_switch#")


def create_port_channel_interface(t, po_id):
    t.write(u"configure terminal")
    t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
    t.read(u"my_switch(config)#")
    t.write(u"interface port-channel %s" % po_id)
    t.read(u"my_switch(config-if)#")
    t.write(u"exit")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.read(u"my_switch#")


def remove_vlan(t, vlan):
    configuring(t, do=u"no vlan %s" % vlan)


def set_interface_on_vlan(t, interface, vlan):
    configuring_interface(t, interface, do=u"switchport mode access")
    configuring_interface(t, interface, do=u"switchport access vlan %s" % vlan)


def revert_switchport_mode_access(t, interface):
    configuring_interface(t, interface, do=u"no switchport access vlan")
    configuring_interface(t, interface, do=u"no switchport mode access")


def configuring(t, do):
    t.write(u"configure terminal")
    t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
    t.read(u"my_switch(config)#")

    t.write(do)

    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.read(u"my_switch#")


def configuring_interface(t, interface, do):
    t.write(u"configure terminal")
    t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
    t.read(u"my_switch(config)#")
    t.write(u"interface %s" % interface)
    t.read(u"my_switch(config-if)#")

    t.write(do)

    t.read(u"my_switch(config-if)#")
    t.write(u"exit")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.read(u"my_switch#")


def configuring_interface_vlan(t, interface, do):
    t.write(u"configure terminal")
    t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
    t.read(u"my_switch(config)#")
    t.write(u"interface vlan %s" % interface)
    t.read(u"my_switch(config-if)#")

    t.write(do)

    t.read(u"my_switch(config-if)#")
    t.write(u"exit")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.read(u"my_switch#")


def configuring_port_channel(t, number, do):
    t.write(u"configure terminal")
    t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
    t.read(u"my_switch(config)#")
    t.write(u"interface port-channel %s" % number)
    t.read(u"my_switch(config-if)#")

    t.write(do)

    t.read(u"my_switch(config-if)#")
    t.write(u"exit")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.read(u"my_switch#")


def assert_interface_configuration(t, interface, config):
    t.write(u"show running-config interface %s " % interface)
    t.readln(u"Building configuration...")
    t.readln(u"")
    t.readln(u"Current configuration : \d+ bytes", regex=True)
    t.readln(u"!")
    for line in config:
        t.readln(line)
    t.readln(u"")
    t.read(u"my_switch#")


class TestCiscoSwitchProtocolSSH(TestCiscoSwitchProtocol):
    __test__ = True

    def create_client(self):
        return SshTester(u"ssh", cisco_switch_ip, cisco_switch_ssh_port, u'root', u'root')


class TestCiscoSwitchProtocolTelnet(TestCiscoSwitchProtocol):
    __test__ = True

    def create_client(self):
        return TelnetTester(u"telnet", cisco_switch_ip, cisco_switch_telnet_port, u'root', u'root')
