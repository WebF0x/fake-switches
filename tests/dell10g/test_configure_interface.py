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
from hamcrest import assert_that, is_not, has_item

from tests.dell10g import enable, assert_interface_configuration, assert_running_config_contains_in_order, \
    get_running_config, configuring_interface, ssh_protocol_factory, telnet_protocol_factory, add_vlan, configuring, \
    remove_bond, create_bond
from tests.util.protocol_util import with_protocol


class Dell10GConfigureInterfaceSshTest(unittest.TestCase):
    protocol_factory = ssh_protocol_factory

    def setUp(self):
        self.protocol = self.protocol_factory()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_show_run_vs_show_run_interface_same_output(self, t):
        enable(t)
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"shutdown")
        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u"shutdown"
        ])

        assert_running_config_contains_in_order(t, [
            u"interface tengigabitethernet 0/0/1",
            u"shutdown",
            u"exit",
            u"!",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no shutdown")

        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u""
        ])

        config = get_running_config(t)
        assert_that(config, is_not(has_item(u"interface tengigabitethernet 0/0/1")))

    @with_protocol
    def test_shutting_down(self, t):
        enable(t)
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"shutdown")

        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u"shutdown"
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no shutdown")

        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u""
        ])

    @with_protocol
    def test_description(self, t):
        enable(t)
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'description "hello WORLD"')
        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u"description \"hello WORLD\""
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"description 'We dont know yet'")
        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u"description \"We dont know yet\""
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'description YEEEAH')
        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u"description \"YEEEAH\""
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no description')
        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u""
        ])

    @with_protocol
    def test_lldp_options_defaults_to_enabled(self, t):
        enable(t)
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no lldp transmit')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no lldp receive')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no lldp med')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no lldp med transmit-tlv capabilities')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no lldp med transmit-tlv network-policy')

        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u'no lldp transmit',
            u'no lldp receive',
            u'no lldp med',
            u'no lldp med transmit-tlv capabilities',
            u'no lldp med transmit-tlv network-policy',
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'lldp transmit')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'lldp receive')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'lldp med')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'lldp med transmit-tlv capabilities')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'lldp med transmit-tlv network-policy')

        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u'',
        ])

    @with_protocol
    def test_spanning_tree(self, t):
        enable(t)
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'spanning-tree disable')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'spanning-tree portfast')

        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u'spanning-tree disable',
            u'spanning-tree portfast',
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no spanning-tree disable')
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u'no spanning-tree portfast')

        assert_interface_configuration(t, u"tengigabitethernet 0/0/1", [
            u''
        ])

    @with_protocol
    def test_access_vlan_that_doesnt_exist_prints_a_warning_and_config_is_unchanged(self, t):
        enable(t)
        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport access vlan 1200")
        t.readln(u"")
        t.readln(u"VLAN ID not found.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u""
        ])

    @with_protocol
    def test_access_vlan(self, t):
        enable(t)

        add_vlan(t, 1264)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        
        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")
        t.write(u"switchport access vlan 1264")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport access vlan 1264",
        ])

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")
        t.write(u"no switchport access vlan")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u""
        ])

        configuring(t, do=u"no vlan 1264")

    @with_protocol
    def test_switchport_mode(self, t):
        enable(t)

        add_vlan(t, 1264)
        add_vlan(t, 1265)

        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u""
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode access")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u""
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport access vlan 1264")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport access vlan 1264"
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode access")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport access vlan 1264"
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode general")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport access vlan 1264"
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general pvid 1264")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport access vlan 1264",
            u"switchport general pvid 1264"
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no switchport access vlan")
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general allowed vlan add 1265")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport general pvid 1264",
            u"switchport general allowed vlan add 1265",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no switchport general pvid")
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no switchport general allowed vlan")
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode trunk")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk"
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode access")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u""
        ])

        configuring(t, do=u"no vlan 1265")
        configuring(t, do=u"no vlan 1264")

    @with_protocol
    def test_switchport_mode_failure(self, t):
        enable(t)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport mode shizzle")
        t.readln(u"                                         ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_switchport_general_pvid(self, t):
        enable(t)

        add_vlan(t, 1264)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport mode general")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general pvid 1500")
        t.readln(u"Could not configure pvid.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general pvid 1264")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport general pvid 1264"
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no switchport general pvid")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode access")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general pvid 1264")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport general pvid 1264",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no switchport general pvid")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"",
        ])

        configuring(t, do=u"no vlan 1264")

    @with_protocol
    def test_switchport_add_trunk_trunk_vlans_special_cases(self, t):
        enable(t)

        add_vlan(t, 1200)
        add_vlan(t, 1201)

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode trunk")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan add 1200")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan 1200")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1200",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan add 1201")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1200-1201",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan add 1202")
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan remove 1203")
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan remove 1200")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1201-1202",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no switchport trunk allowed vlan")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no switchport mode")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u""
        ])

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")
        t.write(u"switchport trunk allowed vlan add 1202 1201")
        t.readln(u"                                                                 ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring(t, do=u"no vlan 1200")
        configuring(t, do=u"no vlan 1201")

    #general stays the same
    @with_protocol
    def test_switchport_add_general_trunk_vlans_special_cases(self, t):
        enable(t)

        add_vlan(t, 1201)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport mode general")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general allowed vlan add 1200")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 1")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general allowed vlan add 1200-1202")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 2")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.readln(u"VLAN      1202 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general allowed vlan remove 1200")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 1")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general allowed vlan remove 1200-1202")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 2")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.readln(u"VLAN      1202 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general allowed vlan add 1202-1201")
        t.readln(u"VLAN range - separate non-consecutive IDs with ',' and no spaces.  Use '-' for range.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport general allowed vlan add 1202 1201")
        t.readln(u"                                                                 ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"switchport mode access")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring(t, do=u"no vlan 1201")

    @with_protocol
    def test_switchport_add_remove_trunk_trunk_vlans(self, t):
        enable(t)

        add_vlan(t, 1200)
        add_vlan(t, 1201)
        add_vlan(t, 1202)
        add_vlan(t, 1203)
        add_vlan(t, 1205)

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode trunk")
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan 1200")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1200",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan add 1200,1201")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1200-1201",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan add 1201-1203,1205")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1200-1203,1205",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan remove 1202")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1200-1201,1203,1205",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan remove 1203,1205")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan 1200-1201",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport trunk allowed vlan remove 1200-1203")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode trunk",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode access")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"",
        ])

        configuring(t, do=u"no vlan 1200")
        configuring(t, do=u"no vlan 1201")
        configuring(t, do=u"no vlan 1202")
        configuring(t, do=u"no vlan 1203")
        configuring(t, do=u"no vlan 1205")

    @with_protocol
    def test_switchport_add_remove_general_trunk_vlans(self, t):
        enable(t)

        add_vlan(t, 1200)
        add_vlan(t, 1201)
        add_vlan(t, 1202)
        add_vlan(t, 1203)
        add_vlan(t, 1205)

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode general")
        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general allowed vlan add 1200")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general allowed vlan add 1200,1201")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1201",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general allowed vlan add 1201-1203,1205")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1203,1205",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general allowed vlan remove 1202")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1201,1203,1205",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general allowed vlan remove 1203,1205")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1201",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport general allowed vlan remove 1200-1203")
        assert_interface_configuration(t, u'tengigabitethernet 0/0/1', [
            u"switchport mode general",
        ])

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"switchport mode access")

        configuring(t, do=u"no vlan 1200")
        configuring(t, do=u"no vlan 1201")
        configuring(t, do=u"no vlan 1202")
        configuring(t, do=u"no vlan 1203")
        configuring(t, do=u"no vlan 1205")

    @with_protocol
    def test_show_interfaces_status(self, t):
        enable(t)

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"description \"longer name than whats allowed\"")
        create_bond(t, 43)

        t.write(u"show interfaces status")
        t.readln(u"")
        t.readln(u"Port      Description               Vlan  Duplex Speed   Neg  Link   Flow Ctrl")
        t.readln(u"                                                              State  Status")
        t.readln(u"--------- ------------------------- ----- ------ ------- ---- ------ ---------")
        t.readln(u"Te0/0/1   longer name than whats al       Full   10000   Auto Up     Active")
        t.readln(u"Te0/0/2                                   Full   10000   Auto Up     Active")
        t.readln(u"Te1/0/1                                   Full   10000   Auto Up     Active")
        t.readln(u"Te1/0/2                                   Full   10000   Auto Up     Active")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Port    Description                    Vlan  Link")
        t.readln(u"Channel                                      State")
        t.readln(u"------- ------------------------------ ----- -------")
        t.readln(u"Po43                                   trnk  Up")
        t.readln(u"")
        t.read(u"my_switch#")

        configuring_interface(t, u"tengigabitethernet 0/0/1", do=u"no description")

        remove_bond(t, 43)

    @with_protocol
    def test_10g_does_not_support_mtu_command_on_interface(self, t):
        enable(t)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface tengigabitethernet 0/0/1")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"mtu 5000")
        t.readln(u"                                                     ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"no mtu")
        t.readln(u"                                                     ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-Te0/0/1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")



class Dell10GConfigureInterfaceTelnetTest(Dell10GConfigureInterfaceSshTest):
    protocol_factory = telnet_protocol_factory
