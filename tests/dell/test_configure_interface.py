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

from tests.dell import enable, configuring_interface, \
    assert_interface_configuration, assert_running_config_contains_in_order, \
    get_running_config, configure, configuring_vlan, unconfigure_vlan, \
    configuring_a_vlan_on_interface, create_bond, remove_bond, \
    ssh_protocol_factory, telnet_protocol_factory, configuring_bond
from tests.util.protocol_util import with_protocol


class DellConfigureInterfaceTest(unittest.TestCase):
    __test__ = False
    protocol_factory = None

    def setUp(self):
        self.protocol = self.protocol_factory()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_show_run_vs_show_run_interface_same_output(self, t):
        enable(t)
        configuring_interface(t, u"ethernet 1/g1", do=u"shutdown")
        assert_interface_configuration(t, u"ethernet 1/g1", [
            u"shutdown"
        ])

        assert_running_config_contains_in_order(t, [
            u"interface ethernet 1/g1",
            u"shutdown",
            u"exit",
            u"!",
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"no shutdown")

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u""
        ])

        config = get_running_config(t)
        assert_that(config, is_not(has_item(u"interface ethernet 1/g1")))

    @with_protocol
    def test_shutting_down(self, t):
        enable(t)
        configuring_interface(t, u"ethernet 1/g1", do=u"shutdown")

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u"shutdown"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"no shutdown")

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u""
        ])

    @with_protocol
    def test_description(self, t):
        enable(t)
        configuring_interface(t, u"ethernet 1/g1", do=u'description "hello WORLD"')
        assert_interface_configuration(t, u"ethernet 1/g1", [
            u"description 'hello WORLD'"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"description 'We dont know yet'")
        assert_interface_configuration(t, u"ethernet 1/g1", [
            u"description 'We dont know yet'"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u'description YEEEAH')
        assert_interface_configuration(t, u"ethernet 1/g1", [
            u"description 'YEEEAH'"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u'no description')
        assert_interface_configuration(t, u"ethernet 1/g1", [
            u""
        ])

    @with_protocol
    def test_lldp_options_defaults_to_enabled(self, t):
        enable(t)
        configuring_interface(t, u"ethernet 1/g1", do=u'no lldp transmit')
        configuring_interface(t, u"ethernet 1/g1", do=u'no lldp receive')
        configuring_interface(t, u"ethernet 1/g1", do=u'no lldp med transmit-tlv capabilities')
        configuring_interface(t, u"ethernet 1/g1", do=u'no lldp med transmit-tlv network-policy')

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u'no lldp transmit',
            u'no lldp receive',
            u'no lldp med transmit-tlv capabilities',
            u'no lldp med transmit-tlv network-policy',
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u'lldp transmit')
        configuring_interface(t, u"ethernet 1/g1", do=u'lldp receive')
        configuring_interface(t, u"ethernet 1/g1", do=u'lldp med transmit-tlv capabilities')
        configuring_interface(t, u"ethernet 1/g1", do=u'lldp med transmit-tlv network-policy')

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u'',
        ])

    @with_protocol
    def test_spanning_tree(self, t):
        enable(t)
        configuring_interface(t, u"ethernet 1/g1", do=u'spanning-tree disable')
        configuring_interface(t, u"ethernet 1/g1", do=u'spanning-tree portfast')

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u'spanning-tree disable',
            u'spanning-tree portfast',
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u'no spanning-tree disable')
        configuring_interface(t, u"ethernet 1/g1", do=u'no spanning-tree portfast')

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u''
        ])



    @with_protocol
    def test_access_vlan_that_doesnt_exist_prints_a_warning_and_config_is_unchanged(self, t):
        enable(t)
        configure(t)

        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport access vlan 1200")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"VLAN ID not found.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u""
        ])

    @with_protocol
    def test_access_vlan(self, t):
        enable(t)

        configuring_vlan(t, 1264)

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"switchport access vlan 1264")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport access vlan 1264",
        ])

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"no switchport access vlan")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u""
        ])

        unconfigure_vlan(t, 1264)

    @with_protocol
    def test_no_switchport_mode_in_trunk_mode(self, t):
        enable(t)

        configuring_vlan(t, 1264)

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"switchport mode trunk")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"switchport trunk allowed vlan add 1264")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan add 1264",
        ])

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"no switchport mode")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u""
        ])

        unconfigure_vlan(t, 1264)

    @with_protocol
    def test_no_switchport_mode_in_access_mode(self, t):
        enable(t)

        configuring_vlan(t, 1264)

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"switchport access vlan 1264")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport access vlan 1264",
        ])

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"no switchport mode")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport access vlan 1264",
        ])

        unconfigure_vlan(t, 1264)

    @with_protocol
    def test_no_switchport_mode_in_general_mode(self, t):
        enable(t)

        configuring_vlan(t, 1264)

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"switchport mode general")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"switchport general pvid 1264")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan add 1264")

        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general pvid 1264",
            u"switchport general allowed vlan add 1264",
        ])

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"no switchport mode")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"",
        ])

        unconfigure_vlan(t, 1264)

    @with_protocol
    def test_switchport_mode(self, t):
        enable(t)

        configuring_vlan(t, 1264)
        configuring_vlan(t, 1265)

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u""
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u""
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport access vlan 1264")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport access vlan 1264"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport access vlan 1264"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode general")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport general pvid 1264")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general pvid 1264"
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport general allowed vlan add 1265")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general pvid 1264",
            u"switchport general allowed vlan add 1265",
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode trunk")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk"
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan add 1265")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan add 1265",
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u""
        ])

        unconfigure_vlan(t, 1265)
        unconfigure_vlan(t, 1264)

    @with_protocol
    def test_switchport_mode_failure(self, t):
        enable(t)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport mode shizzle")
        t.readln(u"                                         ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

    @with_protocol
    def test_switchport_general_pvid(self, t):
        enable(t)

        configuring_vlan(t, 1264)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general pvid 1264")
        t.readln(u"")
        t.readln(u"Port is not general port.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport mode general")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general pvid 1500")
        t.readln(u"Could not configure pvid.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general pvid 1264")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general pvid 1264"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"no switchport general pvid")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"",
        ])

        unconfigure_vlan(t, 1264)

    @with_protocol
    def test_switchport_add_trunk_trunk_vlans_special_cases(self, t):
        enable(t)

        configuring_vlan(t, 1201)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport trunk allowed vlan add 1200")
        t.readln(u"Interface not in Trunk Mode.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport mode trunk")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport trunk allowed vlan add 1200")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 1")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport trunk allowed vlan add 1200-1202")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 2")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.readln(u"VLAN      1202 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport trunk allowed vlan remove 1200")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 1")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport trunk allowed vlan remove 1200-1202")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 2")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.readln(u"VLAN      1202 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport trunk allowed vlan add 1202-1201")
        t.readln(u"VLAN range - separate non-consecutive IDs with ',' and no spaces.  Use '-' for range.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport trunk allowed vlan add 1202 1201")
        t.readln(u"                                                                 ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport mode access")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        unconfigure_vlan(t, 1201)

    @with_protocol
    def test_switchport_add_general_trunk_vlans_special_cases(self, t):
        enable(t)

        configuring_vlan(t, 1201)

        t.write(u"configure")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan add 1200")
        t.readln(u"Interface not in General Mode.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport mode general")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan add 1200")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 1")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan add 1200-1202")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 2")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.readln(u"VLAN      1202 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan remove 1200")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 1")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan remove 1200-1202")
        t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        t.readln(u"delays in applying the configuration.")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"          Failure Information")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLANs failed to be configured : 2")
        t.readln(u"---------------------------------------")
        t.readln(u"   VLAN             Error")
        t.readln(u"---------------------------------------")
        t.readln(u"VLAN      1200 ERROR: This VLAN does not exist.")
        t.readln(u"VLAN      1202 ERROR: This VLAN does not exist.")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan add 1202-1201")
        t.readln(u"VLAN range - separate non-consecutive IDs with ',' and no spaces.  Use '-' for range.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport general allowed vlan add 1202 1201")
        t.readln(u"                                                                 ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"switchport mode access")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        unconfigure_vlan(t, 1201)

    @with_protocol
    def test_switchport_add_remove_trunk_trunk_vlans(self, t):
        enable(t)

        configuring_vlan(t, 1200)
        configuring_vlan(t, 1201)
        configuring_vlan(t, 1202)
        configuring_vlan(t, 1203)
        configuring_vlan(t, 1205)

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode trunk")
        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan add 1200")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan add 1200",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan add 1200,1201")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan add 1200-1201",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan add 1201-1203,1205")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan add 1200-1203,1205",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan remove 1202")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan add 1200-1201,1203,1205",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan remove 1203,1205")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
            u"switchport trunk allowed vlan add 1200-1201",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport trunk allowed vlan remove 1200-1203")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode trunk",
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")

        unconfigure_vlan(t, 1200)
        unconfigure_vlan(t, 1201)
        unconfigure_vlan(t, 1202)
        unconfigure_vlan(t, 1203)
        unconfigure_vlan(t, 1205)

    @with_protocol
    def test_switchport_add_remove_general_trunk_vlans(self, t):
        enable(t)

        configuring_vlan(t, 1200)
        configuring_vlan(t, 1201)
        configuring_vlan(t, 1202)
        configuring_vlan(t, 1203)
        configuring_vlan(t, 1205)

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode general")
        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport general allowed vlan add 1200")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport general allowed vlan add 1200,1201")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1201",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport general allowed vlan add 1201-1203,1205")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1203,1205",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport general allowed vlan remove 1202")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1201,1203,1205",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport general allowed vlan remove 1203,1205")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
            u"switchport general allowed vlan add 1200-1201",
        ])

        configuring_a_vlan_on_interface(t, u"ethernet 1/g1", do=u"switchport general allowed vlan remove 1200-1203")
        assert_interface_configuration(t, u'ethernet 1/g1', [
            u"switchport mode general",
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"switchport mode access")

        unconfigure_vlan(t, 1200)
        unconfigure_vlan(t, 1201)
        unconfigure_vlan(t, 1202)
        unconfigure_vlan(t, 1203)
        unconfigure_vlan(t, 1205)

    @with_protocol
    def test_show_interfaces_status(self, t):
        enable(t)

        create_bond(t, 1)
        create_bond(t, 2)
        create_bond(t, 3)
        create_bond(t, 4)
        create_bond(t, 5)
        create_bond(t, 6)
        create_bond(t, 7)
        create_bond(t, 8)
        create_bond(t, 9)
        create_bond(t, 10)

        t.write(u"show interfaces status")
        t.readln(u"")
        t.readln(u"Port   Type                            Duplex  Speed    Neg  Link  Flow Control")
        t.readln(u"                                                             State Status")
        t.readln(u"-----  ------------------------------  ------  -------  ---- --------- ------------")
        t.readln(u"1/g1   Gigabit - Level                 Full    Unknown  Auto Down      Inactive")
        t.readln(u"1/g2   Gigabit - Level                 Full    Unknown  Auto Down      Inactive")
        t.readln(u"1/xg1  10G - Level                     Full    Unknown  Auto Down      Inactive")
        t.readln(u"2/g1   Gigabit - Level                 Full    Unknown  Auto Down      Inactive")
        t.readln(u"2/g2   Gigabit - Level                 Full    Unknown  Auto Down      Inactive")
        t.readln(u"2/xg1  10G - Level                     Full    Unknown  Auto Down      Inactive")
        t.readln(u"")
        t.readln(u"")
        t.readln(u"Ch   Type                            Link")
        t.readln(u"                                     State")
        t.readln(u"---  ------------------------------  -----")
        t.readln(u"ch1  Link Aggregate                  Down")
        t.readln(u"ch2  Link Aggregate                  Down")
        t.readln(u"ch3  Link Aggregate                  Down")
        t.readln(u"ch4  Link Aggregate                  Down")
        t.readln(u"ch5  Link Aggregate                  Down")
        t.readln(u"ch6  Link Aggregate                  Down")
        t.readln(u"ch7  Link Aggregate                  Down")
        t.readln(u"ch8  Link Aggregate                  Down")
        t.read(u"--More-- or (q)uit")
        t.write_raw(u"m")
        t.readln(u"")
        t.readln(u"ch9  Link Aggregate                  Down")
        t.readln(u"ch10 Link Aggregate                  Down")
        t.readln(u"")
        t.readln(u"Flow Control:Enabled")
        t.readln(u"")
        t.read(u"my_switch#")

        remove_bond(t, 1)
        remove_bond(t, 2)
        remove_bond(t, 3)
        remove_bond(t, 4)
        remove_bond(t, 5)
        remove_bond(t, 6)
        remove_bond(t, 7)
        remove_bond(t, 8)
        remove_bond(t, 9)
        remove_bond(t, 10)

    @with_protocol
    def test_mtu(self, t):
        enable(t)

        configure(t)
        t.write(u"interface ethernet 1/g1")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"mtu what")
        t.readln(u"                            ^")
        t.readln(u"Invalid input. Please specify an integer in the range 1518 to 9216.")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"mtu 1517")
        t.readln(u"                            ^")
        t.readln(u"Value is out of range. The valid range is 1518 to 9216.")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"mtu 9217")
        t.readln(u"                            ^")
        t.readln(u"Value is out of range. The valid range is 1518 to 9216.")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"mtu 5000 lol")
        t.readln(u"                                  ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")
        t.write(u"mtu 5000")
        t.readln(u"")
        t.read(u"my_switch(config-if-1/g1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u"mtu 5000"
        ])

        configuring_interface(t, u"ethernet 1/g1", do=u"no mtu")

        assert_interface_configuration(t, u"ethernet 1/g1", [
            u""
        ])

    @with_protocol
    def test_mtu_on_bond(self, t):
        enable(t)

        create_bond(t, 1)

        configure(t)
        t.write(u"interface port-channel 1")
        t.readln(u"")
        t.read(u"my_switch(config-if-ch1)#")
        t.write(u"mtu what")
        t.readln(u"                            ^")
        t.readln(u"Invalid input. Please specify an integer in the range 1518 to 9216.")
        t.read(u"my_switch(config-if-ch1)#")
        t.write(u"mtu 1517")
        t.readln(u"                            ^")
        t.readln(u"Value is out of range. The valid range is 1518 to 9216.")
        t.read(u"my_switch(config-if-ch1)#")
        t.write(u"mtu 9217")
        t.readln(u"                            ^")
        t.readln(u"Value is out of range. The valid range is 1518 to 9216.")
        t.read(u"my_switch(config-if-ch1)#")
        t.write(u"mtu 5000 lol")
        t.readln(u"                                  ^")
        t.readln(u"% Invalid input detected at '^' marker.")
        t.readln(u"")
        t.read(u"my_switch(config-if-ch1)#")
        t.write(u"mtu 5000")
        t.readln(u"")
        t.read(u"my_switch(config-if-ch1)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch(config)#")

        t.write(u"exit")
        t.readln(u"")
        t.read(u"my_switch#")

        assert_interface_configuration(t, u"port-channel 1", [
            u"mtu 5000"
        ])

        configuring_bond(t, u"port-channel 1", do=u"no mtu")

        assert_interface_configuration(t, u"port-channel 1", [
            u""
        ])

        remove_bond(t, 1)

class DellConfigureInterfaceSshTest(DellConfigureInterfaceTest):
    __test__ = True
    protocol_factory = ssh_protocol_factory


class DellConfigureInterfaceTelnetTest(DellConfigureInterfaceTest):
    __test__ = True
    protocol_factory = telnet_protocol_factory
