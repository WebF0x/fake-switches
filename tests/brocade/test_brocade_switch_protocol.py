import unittest

from flexmock import flexmock_teardown
from tests.util.global_reactor import brocade_switch_ip, \
    brocade_switch_ssh_port, brocade_privileged_password
import mock
from tests.util.protocol_util import SshTester, with_protocol


class TestBrocadeSwitchProtocol(unittest.TestCase):
    def setUp(self):
        self.protocol = SshTester(u"ssh", brocade_switch_ip, brocade_switch_ssh_port, u'root', u'root')

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_enable_command_requires_a_password(self, t):
        t.write(u"enable")
        t.read(u"Password:")
        t.write_invisible(brocade_privileged_password)
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_wrong_password(self, t):
        t.write(u"enable")
        t.read(u"Password:")
        t.write_invisible(u"hello_world")
        t.readln(u"Error - Incorrect username or password.")
        t.read(u"SSH@my_switch>")

    @with_protocol
    def test_no_password_works_for_legacy_reasons(self, t):
        t.write(u"enable")
        t.read(u"Password:")
        t.write_invisible(u"")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_exiting_loses_the_connection(self, t):
        t.write(u"enable")
        t.read(u"Password:")
        t.write_invisible(brocade_privileged_password)
        t.read(u"SSH@my_switch#")
        t.write(u"exit")
        t.read_eof()

    @with_protocol
    def test_no_such_command_return_to_prompt(self, t):
        enable(t)

        t.write(u"shizzle")
        t.readln(u"Invalid input -> shizzle")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch#")

    @with_protocol
    @mock.patch(u"fake_switches.adapters.tftp_reader.read_tftp")
    def test_command_copy_failing(self, t, read_tftp):
        read_tftp.side_effect = Exception(u"Stuff")

        enable(t)

        t.write(u"ncopy tftp 1.2.3.4 my-file running-config")
        t.readln(u"TFTP: Download to running-config failed - Session timed out")
        t.read(u"SSH@my_switch#")

        read_tftp.assert_called_with(u"1.2.3.4", u"my-file")

    @with_protocol
    @mock.patch(u"fake_switches.adapters.tftp_reader.read_tftp")
    def test_command_copy_success(self, t, read_tftp):
        enable(t)

        t.write(u"ncopy tftp 1.2.3.4 my-file running-config")
        t.readln(u"done")
        t.read(u"SSH@my_switch#")

        read_tftp.assert_called_with(u"1.2.3.4", u"my-file")

    @with_protocol
    def test_command_show_run_int_vlan_empty(self, t):
        enable(t)

        t.write(u"skip-page-display")
        t.read(u"SSH@my_switch#")
        t.write(u"show running-config vlan | begin vlan 1299")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_command_add_vlan(self, t):
        enable(t)

        t.write(u"conf t")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"vlan 123 name shizzle")
        t.read(u"SSH@my_switch(config-vlan-123)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")
        t.write(u"show running-config vlan | begin vlan 123")
        t.readln(u"vlan 123 name shizzle")
        t.readln(u"!")
        t.readln(u"!")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"no vlan 123")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")
        t.write(u"show running-config vlan | begin vlan 123")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_command_assign_access_vlan_to_port(self, t):
        enable(t)
        create_vlan(t, u"123")
        set_interface_untagged_on_vlan(t, u"ethernet 1/1", u"123")

        t.write(u"show interfaces ethernet 1/1 | inc Member of")
        t.readln(u"  Member of VLAN 123 (untagged), port is in untagged mode, port state is Disabled")
        t.read(u"SSH@my_switch#")

        unset_interface_untagged_on_vlan(t, u"ethernet 1/1", u"123")

        t.write(u"show interfaces ethe1/1 | inc VLAN 1")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.read(u"SSH@my_switch#")

        remove_vlan(t, u"123")

    @with_protocol
    def test_command_interface_tagged_with_native_default_vlan(self, t):
        enable(t)
        create_vlan(t, u"123")
        configuring_vlan(t, u"123", do=u"tagged ethernet 1/1")

        t.write(u"show interfaces ethe 1/1 | inc Member of")
        t.readln(u"  Member of VLAN 1 (untagged), 1 L2 VLANS (tagged), port is in dual mode (default vlan), port state is Disabled")
        t.read(u"SSH@my_switch#")

        configuring_vlan(t, u"123", do=u"no tagged ethernet 1/1")

        t.write(u"show interfaces ethe1/1 | inc VLAN 1")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.read(u"SSH@my_switch#")

        remove_vlan(t, u"123")

    @with_protocol
    def test_command_show_interface_invalid_interface_name(self, t):
        enable(t)

        t.write(u"show interface ethe 1/25")
        t.readln(u"Error - invalid interface 1/25")
        t.read(u"SSH@my_switch#")

        t.write(u"show interface ethe 1/64")
        t.readln(u"Error - invalid interface 1/64")
        t.read(u"SSH@my_switch#")

        t.write(u"show interface ethe 1/65")
        t.readln(u"Invalid input -> 1/65")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch#")

        t.write(u"show interface ethe 1/99")
        t.readln(u"Invalid input -> 1/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch#")

        t.write(u"show interface ethe 2/1")
        t.readln(u"Error - interface 2/1 is not an ETHERNET interface")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_command_no_interface_invalid_interface_name(self, t):
        enable(t)
        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"no interface ethe 1/25")
        t.readln(u"Error - invalid interface 1/25")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"no interface ethe 1/64")
        t.readln(u"Error - invalid interface 1/64")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"no interface ethe 1/65")
        t.readln(u"Invalid input -> 1/65")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"no interface ethe 1/99")
        t.readln(u"Invalid input -> 1/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"no interface ethe 2/1")
        t.readln(u"Error - interface 2/1 is not an ETHERNET interface")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_command_interface_invalid_interface_name(self, t):
        enable(t)
        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe 1/25")
        t.readln(u"Error - invalid interface 1/25")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe 1/64")
        t.readln(u"Error - invalid interface 1/64")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe 1/65")
        t.readln(u"Invalid input -> 1/65")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe 1/99")
        t.readln(u"Invalid input -> 1/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe nonexistent99")
        t.readln(u"Invalid input -> nonexistent  99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe 2/1")
        t.readln(u"Error - interface 2/1 is not an ETHERNET interface")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_remove_a_ports_from_a_vlan_should_print_an_error(self, t):
        enable(t)

        create_vlan(t, u"123")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"vlan 123")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"no untagged ethernet 1/1")
        t.readln(u"Error: ports ethe 1/1 are not untagged members of vlan 123")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"no tagged ethernet 1/1")
        t.readln(u"Error: ports ethe 1/1 are not tagged members of vlan 123")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_unknown_ports_when_tagging_prints_an_error(self, t):
        enable(t)

        create_vlan(t, u"123")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"vlan 123")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"untagged ethernet 1/99")
        t.readln(u"Invalid input -> 1/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"tagged ethernet 1/99")
        t.readln(u"Invalid input -> 1/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"no untagged ethernet 1/99")
        t.readln(u"Invalid input -> 1/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"no tagged ethernet 1/99")
        t.readln(u"Invalid input -> 1/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-123)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_command_interface_tagged_with_native_vlan(self, t):
        enable(t)
        create_vlan(t, u"123")
        create_vlan(t, u"124")
        create_vlan(t, u"456")

        configuring_vlan(t, u"123", do=u"tagged ethernet 1/1")
        configuring_vlan(t, u"124", do=u"tagged ethernet 1/1")
        configuring_vlan(t, u"456", do=u"untagged ethernet 1/1")

        t.write(u"show interfaces ethernet 1/1 | inc Member of")
        t.readln(u"  Member of VLAN 456 (untagged), 2 L2 VLANS (tagged), port is in dual mode, port state is Disabled")
        t.read(u"SSH@my_switch#")

        configuring_vlan(t, u"123", do=u"no tagged ethernet 1/1")
        configuring_vlan(t, u"124", do=u"no tagged ethernet 1/1")
        configuring_vlan(t, u"456", do=u"no untagged ethernet 1/1")

        t.write(u"show interfaces ethe1/1 | inc VLAN 1")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.read(u"SSH@my_switch#")

        remove_vlan(t, u"123")
        remove_vlan(t, u"124")
        remove_vlan(t, u"456")

    @with_protocol
    def test_command_interface_tagged_with_no_native_vlan(self, t):
        enable(t)
        create_vlan(t, u"123")

        configuring_vlan(t, u"123", do=u"tagged ethernet 1/1")
        configuring_vlan(t, u"1", do=u"no untagged ethernet 1/1")

        t.write(u"show interfaces ethernet 1/1 | inc Member of")
        t.readln(u"  Member of 1 L2 VLAN(S) (tagged), port is in tagged mode, port state is Disabled")
        t.read(u"SSH@my_switch#")

        configuring_vlan(t, u"123", do=u"no tagged ethernet 1/1")
        # untagged vlan 1 returns by default magically

        t.write(u"show interfaces ethe1/1 | inc VLAN 1")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.read(u"SSH@my_switch#")

        remove_vlan(t, u"123")

    @with_protocol
    def test_show_interfaces(self, t):
        enable(t)

        configuring_interface(t, u"1/2", do=u"port-name hello")
        configuring_interface(t, u"1/3", do=u"enable")
        create_interface_vlan(t, u"1000")
        configuring_interface_vlan(t, u"1000", do=u"port-name Salut")
        create_interface_vlan(t, u"2000")
        configuring_interface_vlan(t, u"2000", do=u"ip address 1.1.1.1/24")

        t.write(u"show interfaces")
        t.readln(u"GigabitEthernet1/1 is disabled, line protocol is down")
        t.readln(u"  Hardware is GigabitEthernet, address is 0000.0000.0000 (bia 0000.0000.0000)")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.readln(u"  No port name")
        t.readln(u"GigabitEthernet1/2 is disabled, line protocol is down")
        t.readln(u"  Hardware is GigabitEthernet, address is 0000.0000.0000 (bia 0000.0000.0000)")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.readln(u"  Port name is hello")
        t.readln(u"GigabitEthernet1/3 is down, line protocol is down")
        t.readln(u"  Hardware is GigabitEthernet, address is 0000.0000.0000 (bia 0000.0000.0000)")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.readln(u"  No port name")
        t.readln(u"GigabitEthernet1/4 is disabled, line protocol is down")
        t.readln(u"  Hardware is GigabitEthernet, address is 0000.0000.0000 (bia 0000.0000.0000)")
        t.readln(u"  Member of VLAN 1 (untagged), port is in untagged mode, port state is Disabled")
        t.readln(u"  No port name")
        t.readln(u"Ve1000 is down, line protocol is down")
        t.readln(u"  Hardware is Virtual Ethernet, address is 0000.0000.0000 (bia 0000.0000.0000)")
        t.readln(u"  Port name is Salut")
        t.readln(u"  Vlan id: 1000")
        t.readln(u"  Internet address is 0.0.0.0/0, IP MTU 1500 bytes, encapsulation ethernet")
        t.readln(u"Ve2000 is down, line protocol is down")
        t.readln(u"  Hardware is Virtual Ethernet, address is 0000.0000.0000 (bia 0000.0000.0000)")
        t.readln(u"  No port name")
        t.readln(u"  Vlan id: 2000")
        t.readln(u"  Internet address is 1.1.1.1/24, IP MTU 1500 bytes, encapsulation ethernet")
        t.read(u"SSH@my_switch#")

        configuring_interface(t, u"1/2", do=u"no port-name hello")
        configuring_interface(t, u"1/3", do=u"disable")

        configuring(t, do=u"no interface ve 1000")
        configuring(t, do=u"no vlan 1000")

        configuring(t, do=u"no interface ve 2000")
        configuring(t, do=u"no vlan 2000")

        remove_vlan(t, u"123")

    @with_protocol
    def test_show_vlan_brief(self, t):
        enable(t)
        create_vlan(t, u"123")
        create_vlan(t, u"3333", u"some-name")
        create_vlan(t, u"2222", u"your-name-is-at-the-maxi-length")  # 31 on brocade

        set_interface_untagged_on_vlan(t, u"ethe1/1", u"123")

        t.write(u"show vlan brief")
        t.readln(u"")
        t.readln(u"VLAN     Name       Encap ESI                              Ve    Pri Ports")
        t.readln(u"----     ----       ----- ---                              ----- --- -----")
        t.readln(
            u"1        DEFAULT-VL                                        -     -   Untagged Ports : ethe 1/2 to 1/4")
        t.readln(u"123      [None]                                            -     -   Untagged Ports : ethe 1/1")
        t.readln(u"2222     your-name-                                        -     -")
        t.readln(u"3333     some-name                                         -     -")
        t.read(u"SSH@my_switch#")

        remove_interface_from_vlan(t, u"ethe1/1", u"123")
        remove_vlan(t, u"123")
        remove_vlan(t, u"1234")
        remove_vlan(t, u"5555")

    @with_protocol
    def test_show_running_config_vlan(self, t):
        enable(t)
        create_vlan(t, u"123")
        create_vlan(t, u"999")
        create_vlan(t, u"888")

        configuring_vlan(t, u"123", do=u"untagged ethernet 1/2")
        configuring_vlan(t, u"888", do=u"tagged ethernet 1/2")
        configuring_vlan(t, u"888", do=u"router-interface ve 1888")
        configuring_vlan(t, u"999", do=u"tagged ethe1/2")
        configuring_vlan(t, u"999", do=u"untagged ethe1/1")

        t.write(u"show running-config vlan")
        t.readln(u"spanning-tree")
        t.readln(u"!")
        t.readln(u"!")
        t.readln(u"vlan 1 name DEFAULT-VLAN")
        t.readln(u" no untagged ethe 1/3 to 1/4")
        t.readln(u"!")
        t.readln(u"vlan 123")
        t.readln(u" untagged ethe 1/2")
        t.readln(u"!")
        t.readln(u"vlan 888")
        t.readln(u" tagged ethe 1/2")
        t.readln(u" router-interface ve 1888")
        t.readln(u"!")
        t.readln(u"vlan 999")
        t.readln(u" untagged ethe 1/1")
        t.readln(u" tagged ethe 1/2")
        t.readln(u"!")
        t.readln(u"!")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no interface ve 1888")
        configuring(t, do=u"no vlan 123")
        configuring(t, do=u"no vlan 888")
        configuring(t, do=u"no vlan 999")

    @with_protocol
    def test_shutting_down(self, t):
        enable(t)

        t.write(u"show run interface ethernet 1/3")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ethe1/3")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"enable")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        t.write(u"show run interface ethernet 1/3")
        t.readln(u"interface ethernet 1/3")
        t.readln(u" enable")
        t.readln(u"!")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ethe1/3")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"disable")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        t.write(u"show run interface ethernet 1/3")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_setup_an_interface(self, t):
        enable(t)

        t.write(u"show run int ve 2999")
        t.readln(u"Error - ve 2999 was not configured")
        t.read(u"SSH@my_switch#")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 2999")
        t.readln(u"Error - invalid virtual ethernet interface number.")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"vlan 2999")
        t.read(u"SSH@my_switch(config-vlan-2999)#")
        t.write(u"router interface ve 2999")
        t.readln(u"Invalid input -> interface ve 2999")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-2999)#")
        t.write(u"rout patate 2999")
        t.readln(u"Invalid input -> patate 2999")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-2999)#")
        t.write(u"router-interface ve 2999")
        t.read(u"SSH@my_switch(config-vlan-2999)#")
        t.write(u"router-interface ve 3000")
        t.readln(u"Error: VLAN: 2999  already has router-interface 2999")
        t.read(u"SSH@my_switch(config-vlan-2999)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        t.write(u"show running-config vlan | begin vlan 2999")
        t.readln(u"vlan 2999")
        t.readln(u" router-interface ve 2999")
        t.readln(u"!")
        t.readln(u"!")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ve 2999", [
            u"interface ve 2999",
            u"!"
        ])

        configuring_interface_vlan(t, u"2999", do=u"port-name hey ho")
        configuring_interface_vlan(t, u"2999", do=u"ip address 2.2.2.2/24")
        configuring_interface_vlan(t, u"2999", do=u"ip address 1.1.1.1/24")

        assert_interface_configuration(t, u"ve 2999", [
            u"interface ve 2999",
            u" port-name hey ho",
            u" ip address 1.1.1.1/24",
            u" ip address 2.2.2.2/24",
            u"!"])

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 2999")
        t.read(u"SSH@my_switch(config-vif-2999)#")
        t.write(u"ip address 1.1.1.1/24")
        t.readln(u"IP/Port: Errno(6) Duplicate ip address")
        t.read(u"SSH@my_switch(config-vif-2999)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no interface ve 2999")
        assert_interface_configuration(t, u"ve 2999", [
            u"interface ve 2999",
            u"!"
        ])

        configuring_vlan(t, u"2999", do=u"no router-interface 2999")
        t.write(u"show run int ve 2999")
        t.readln(u"Error - ve 2999 was not configured")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no vlan 2999")

    @with_protocol
    def test_setting_access_group(self, t):
        enable(t)

        create_interface_vlan(t, u"2999")
        configuring_access_group_interface_vlan(t, u"2999", do=u"ip access-group SHNITZLE in")
        configuring_access_group_interface_vlan(t, u"2999", do=u"ip access-group WHIZZLE out")

        assert_interface_configuration(t, u"ve 2999", [
            u"interface ve 2999",
            u" ip access-group SHNITZLE in",
            u" ip access-group WHIZZLE out",
            u"!"])

        configuring_interface_vlan(t, u"2999", do=u"no ip access-group WHIZZLE out")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 2999")
        t.read(u"SSH@my_switch(config-vif-2999)#")
        t.write(u"no ip access-group wat in")
        t.readln(u"Error: Wrong Access List Name wat")
        t.read(u"SSH@my_switch(config-vif-2999)#")
        t.write(u"no ip access-group out")
        t.readln(u"Error: Wrong Access List Name out")
        t.read(u"SSH@my_switch(config-vif-2999)#")
        t.write(u"no ip access-group gneh out")
        t.readln(u"Error: Wrong Access List Name gneh")
        t.read(u"SSH@my_switch(config-vif-2999)#")
        t.write(u"no ip access-group SHNITZLE in")
        t.read(u"SSH@my_switch(config-vif-2999)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ve 2999", [
            u"interface ve 2999",
            u"!"])

        configuring(t, do=u"no interface ve 2999")
        configuring(t, do=u"no vlan 2999")

    @with_protocol
    def test_removing_ip_address(self, t):
        enable(t)

        create_interface_vlan(t, u"2999")
        configuring_interface_vlan(t, u"2999", do=u"ip address 2.2.2.2/24")

        assert_interface_configuration(t, u"ve 2999", [
            u"interface ve 2999",
            u" ip address 2.2.2.2/24",
            u"!"])

        configuring_interface_vlan(t, u"2999", do=u"no ip address 2.2.2.2/24")

        assert_interface_configuration(t, u"ve 2999", [
            u"interface ve 2999",
            u"!"])

        configuring(t, do=u"no interface ve 2999")
        configuring(t, do=u"no vlan 2999")

    @with_protocol
    def test_static_routes(self, t):
        enable(t)
        configuring(t, do=u"ip route 100.100.100.100 255.255.255.0 2.2.2.2")
        configuring(t, do=u"ip route 1.1.2.0 255.255.255.0 2.2.2.3")
        t.write(u"show ip route static")
        t.readln(u"        Destination        Gateway        Port          Cost          Type Uptime src-vrf")
        t.readln(u"1       100.100.100.100/24 2.2.2.2")
        t.readln(u"2       1.1.2.0/24         2.2.2.3")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no ip route 100.100.100.100 255.255.255.0 2.2.2.2")

        t.write(u"show ip route static")
        t.readln(u"        Destination        Gateway        Port          Cost          Type Uptime src-vrf")
        t.readln(u"1       1.1.2.0/24         2.2.2.3")

    @with_protocol
    def test_show_all_interfaces_in_running(self, t):
        enable(t)

        create_interface_vlan(t, u"2998")

        create_interface_vlan(t, u"2999")
        configuring_interface_vlan(t, u"2999", do=u"ip address 2.2.2.2/24")
        configuring_access_group_interface_vlan(t, u"2999", do=u"ip access-group SHNITZLE in")
        configuring_access_group_interface_vlan(t, u"2999", do=u"ip access-group WHIZZLE out")

        create_interface_vlan(t, u"3000")
        configuring_interface_vlan(t, u"3000", do=u"port-name howdy")

        configuring_interface(t, u"1/1", do=u"port-name one one")
        configuring_interface(t, u"1/3", do=u"port-name one three")
        configuring_interface(t, u"1/3", do=u"enable")
        configuring_interface(t, u"1/4", do=u"enable")

        t.write(u"show running-config interface")
        t.readln(u"interface ethernet 1/1")
        t.readln(u" port-name one one")
        t.readln(u"!")
        t.readln(u"interface ethernet 1/3")
        t.readln(u" port-name one three")
        t.readln(u" enable")
        t.readln(u"!")
        t.readln(u"interface ethernet 1/4")
        t.readln(u" enable")
        t.readln(u"!")
        t.readln(u"interface ve 2998")
        t.readln(u"!")
        t.readln(u"interface ve 2999")
        t.readln(u" ip address 2.2.2.2/24")
        t.readln(u" ip access-group SHNITZLE in")
        t.readln(u" ip access-group WHIZZLE out")
        t.readln(u"!")
        t.readln(u"interface ve 3000")
        t.readln(u" port-name howdy")
        t.readln(u"!")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no interface ve 2998")
        configuring(t, do=u"no vlan 2998")
        configuring(t, do=u"no interface ve 2999")
        configuring(t, do=u"no vlan 2999")
        configuring(t, do=u"no interface ve 3000")
        configuring(t, do=u"no vlan 3000")

        configuring_interface(t, u"1/1", do=u"no port-name")
        configuring_interface(t, u"1/3", do=u"no port-name")
        configuring_interface(t, u"1/3", do=u"disable")
        
        configuring(t, do=u"no interface ethernet 1/4")

        t.write(u"show running-config interface")
        t.readln(u"")
        t.read(u"SSH@my_switch#")


    @with_protocol
    def test_configuring_no_interface_does_not_remove_interfaces_from_vlans(self, t):
        enable(t)

        create_vlan(t, u"3000")
        configuring_vlan(t, u"3000", do=u"untagged ethernet 1/1")
        configuring_vlan(t, u"3000", do=u"tagged ethernet 1/2")

        create_vlan(t, u"3001")
        configuring_vlan(t, u"3001", do=u"untagged ethernet 1/3")

        configuring(t, do=u"no interface ethernet 1/1")
        configuring(t, do=u"no interface ethernet 1/2")

        t.write(u"show running-config vlan | begin vlan 3000")
        t.readln(u"vlan 3000")
        t.readln(u" untagged ethe 1/1")
        t.readln(u" tagged ethe 1/2")
        t.readln(u"!")
        t.readln(u"vlan 3001")
        t.readln(u" untagged ethe 1/3")
        t.readln(u"!")

        t.readln(u"!")
        t.readln(u"")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no vlan 3000")
        configuring(t, do=u"no vlan 3001")


    @with_protocol
    def test_overlapping_and_secondary_ips(self, t):
        enable(t)

        create_interface_vlan(t, u"1000")
        create_interface_vlan(t, u"2000")

        configuring_interface_vlan(t, u"1000", do=u"ip address 2.2.2.2/24")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 2000")
        t.read(u"SSH@my_switch(config-vif-2000)#")

        t.write(u"ip address 2.2.2.75/25")
        t.readln(u"IP/Port: Errno(11) ip subnet overlap with another interface")

        t.read(u"SSH@my_switch(config-vif-2000)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ve 1000")
        t.read(u"SSH@my_switch(config-vif-1000)#")

        t.write(u"ip address 2.2.2.4/24")
        t.readln(u"IP/Port: Errno(15) Can only assign one primary ip address per subnet")
        t.read(u"SSH@my_switch(config-vif-1000)#")

        t.write(u"ip address 2.2.2.5/25 secondary")
        t.read(u"SSH@my_switch(config-vif-1000)#")
        t.write(u"ip address 2.2.2.87/30 secondary")
        t.read(u"SSH@my_switch(config-vif-1000)#")
        t.write(u"ip address 2.2.2.72/29 secondary")
        t.read(u"SSH@my_switch(config-vif-1000)#")

        t.write(u"no ip address 2.2.2.2/24")
        t.readln(u"IP/Port: Errno(18) Delete secondary address before deleting primary address")
        t.read(u"SSH@my_switch(config-vif-1000)#")

        t.write(u"no ip address 2.2.2.5/25")
        t.read(u"SSH@my_switch(config-vif-1000)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ve 1000", [
            u"interface ve 1000",
            u" ip address 2.2.2.2/24",
            u" ip address 2.2.2.72/29 secondary",
            u" ip address 2.2.2.87/30 secondary",
            u"!"])

        configuring(t, do=u"no interface ve 2000")
        configuring(t, do=u"no vlan 2000")
        configuring(t, do=u"no interface ve 1000")
        configuring(t, do=u"no vlan 1000")

    @with_protocol
    def test_multiple_secondary_are_listed_at_the_end(self, t):
        enable(t)

        create_interface_vlan(t, u"1000")

        configuring_interface_vlan(t, u"1000", do=u"ip address 2.2.2.2/24")
        configuring_interface_vlan(t, u"1000", do=u"ip address 2.2.2.3/24 secondary")

        configuring_interface_vlan(t, u"1000", do=u"ip address 1.2.2.2/24")
        configuring_interface_vlan(t, u"1000", do=u"ip address 1.2.2.3/24 secondary")

        assert_interface_configuration(t, u"ve 1000", [
            u"interface ve 1000",
            u" ip address 1.2.2.2/24",
            u" ip address 2.2.2.2/24",
            u" ip address 1.2.2.3/24 secondary",
            u" ip address 2.2.2.3/24 secondary",
            u"!"])

        configuring(t, do=u"no interface ve 1000")
        configuring(t, do=u"no vlan 1000")

    @with_protocol
    def test_ip_vrf(self, t):
        enable(t)

        t.write(u"conf t")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"ip vrf SOME-LAN")
        t.read(u"SSH@my_switch(config-vrf-SOME-LAN)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"no ip vrf SOME-LAN")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_ip_vrf_forwarding(self, t):
        enable(t)

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"ip vrf SOME-LAN")
        t.read(u"SSH@my_switch(config-vrf-SOME-LAN)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe 1/3")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"vrf forwarding NOT-DEFAULT-LAN")
        t.readln(u"Error - VRF(NOT-DEFAULT-LAN) does not exist or Route-Distinguisher not specified or Address Family not configured")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")

        t.write(u"vrf forwarding SOME-LAN")
        t.readln(u"Warning: All IPv4 and IPv6 addresses (including link-local) on this interface have been removed")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ethernet 1/3", [
            u"interface ethernet 1/3",
            u" vrf forwarding SOME-LAN",
            u"!"])

        t.write(u"conf t")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"no ip vrf SOME-LAN")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ethernet 1/3", [])

    @with_protocol
    def test_ip_vrf_default_lan(self, t):
        enable(t)

        t.write(u"conf t")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethe 1/3")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"vrf forwarding DEFAULT-LAN")
        t.readln(u"Warning: All IPv4 and IPv6 addresses (including link-local) on this interface have been removed")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ethernet 1/3", [
            u"interface ethernet 1/3",
            u" vrf forwarding DEFAULT-LAN",
            u"!"])

        t.write(u"conf t")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ethe 1/3")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")
        t.write(u"no vrf forwarding DEFAULT-LAN")
        t.readln(u"Warning: All IPv4 and IPv6 addresses (including link-local) on this interface have been removed")
        t.read(u"SSH@my_switch(config-if-e1000-1/3)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ethernet 1/3", [])

    @with_protocol
    def test_ip_setting_vrf_forwarding_wipes_ip_addresses(self, t):
        enable(t)

        create_vlan(t, u"4000")
        create_interface_vlan(t, u"4000")
        configuring_interface_vlan(t, u"4000", do=u"ip address 10.10.0.10/24")
        configuring_interface_vlan(t, u"4000", do=u"ip address 10.10.1.10/24")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface ve 4000",
            u" ip address 10.10.0.10/24",
            u" ip address 10.10.1.10/24",
            u"!"])

        t.write(u"conf t")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 4000")
        t.read(u"SSH@my_switch(config-vif-4000)#")
        t.write(u"vrf forwarding DEFAULT-LAN")
        t.readln(u"Warning: All IPv4 and IPv6 addresses (including link-local) on this interface have been removed")
        t.read(u"SSH@my_switch(config-vif-4000)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface ve 4000",
            u" vrf forwarding DEFAULT-LAN",
            u"!"])

        configuring_interface_vlan(t, u"4000", do=u"ip address 10.10.0.10/24")
        configuring_interface_vlan(t, u"4000", do=u"ip address 10.10.1.10/24")

        t.write(u"conf t")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 4000")
        t.read(u"SSH@my_switch(config-vif-4000)#")
        t.write(u"no vrf forwarding")
        t.readln(u"Incomplete command.")
        t.read(u"SSH@my_switch(config-vif-4000)#")
        t.write(u"no vrf forwarding DEFAULT-LAN")
        t.readln(u"Warning: All IPv4 and IPv6 addresses (including link-local) on this interface have been removed")
        t.read(u"SSH@my_switch(config-vif-4000)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"Vlan4000", [
            u"interface ve 4000",
            u"!"])

        configuring(t, do=u"no interface ve 4000")
        configuring(t, do=u"no vlan 4000")

    @with_protocol
    def test_extreme_vlan_ranges(self, t):
        enable(t)

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"vlan -1")
        t.readln(u"Invalid input -> -1")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"vlan 0")
        t.readln(u"Error: vlan ID value 0 not allowed.")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"vlan 1")
        t.read(u"SSH@my_switch(config-vlan-1)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"vlan 4090")
        t.read(u"SSH@my_switch(config-vlan-4090)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"no vlan 4090")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"vlan 4091")
        t.readln(u"Error: vlan id 4091 is outside of allowed max of 4090")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_show_vlan_ethernet_shows_all_vlans_on_an_interface(self, t):
        enable(t)

        t.write(u"show vlan ethe1/78")
        t.readln(u"Invalid input -> ethe1/78")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch#")

        t.write(u"show vlan ethe 1/78")
        t.readln(u"Invalid input -> 1/78")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch#")

        t.write(u"show vlan ethe 1/2")
        t.readln(u"VLAN: 1  Untagged")
        t.read(u"SSH@my_switch#")

        create_vlan(t, u"1001")
        create_vlan(t, u"1002")
        create_vlan(t, u"1003")
        create_vlan(t, u"1004")
        create_vlan(t, u"1005")

        configuring_vlan(t, u"1002", do=u"tagged ethe1/2")

        t.write(u"show vlan ethe 1/2")
        t.readln(u"VLAN: 1002  Tagged")
        t.read(u"SSH@my_switch#")

        configuring_vlan(t, u"1003", do=u"untagged ethe1/2")

        configuring_vlan(t, u"1001", do=u"tagged ethe1/2")
        configuring_vlan(t, u"1002", do=u"tagged ethe1/2")
        configuring_vlan(t, u"1004", do=u"tagged ethe1/2")

        configuring_vlan(t, u"1005", do=u"tagged ethe1/3")

        t.write(u"show vlan ethe 1/2")
        t.readln(u"VLAN: 1001  Tagged")
        t.readln(u"VLAN: 1002  Tagged")
        t.readln(u"VLAN: 1003  Untagged")
        t.readln(u"VLAN: 1004  Tagged")
        t.read(u"SSH@my_switch#")

        configuring_vlan(t, u"1001", do=u"no tagged ethe1/2")
        configuring_vlan(t, u"1002", do=u"no tagged ethe1/2")
        configuring_vlan(t, u"1004", do=u"no tagged ethe1/2")

        configuring_vlan(t, u"1005", do=u"no tagged ethe1/3")

        t.write(u"show vlan ethe 1/2")
        t.readln(u"VLAN: 1003  Untagged")
        t.read(u"SSH@my_switch#")

        configuring_vlan(t, u"1003", do=u"no untagged ethe1/2")

        t.write(u"show vlan ethe 1/2")
        t.readln(u"VLAN: 1  Untagged")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no vlan 1001")
        configuring(t, do=u"no vlan 1002")
        configuring(t, do=u"no vlan 1003")
        configuring(t, do=u"no vlan 1004")
        configuring(t, do=u"no vlan 1005")

    @with_protocol
    def test_unknown_interface_shows_an_error(self, t):
        enable(t)

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"interface ethernet 909/99")
        t.readln(u"Invalid input -> 909/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_tagging_or_untagging_an_unknown_interface_shows_an_error(self, t):
        enable(t)

        create_vlan(t, u"1000")

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"vlan 1000")
        t.read(u"SSH@my_switch(config-vlan-1000)#")

        t.write(u"tagged ethernet 999/99")
        t.readln(u"Invalid input -> 999/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-1000)#")

        t.write(u"untagged ethernet 999/99")
        t.readln(u"Invalid input -> 999/99")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vlan-1000)#")

        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        configuring(t, do=u"no vlan 1000")

    @with_protocol
    def test_write_memory(self, t):
        enable(t)

        t.write(u"write memory")
        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_vrrp(self, t):
        enable(t)
        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"vlan 2995 name HELLO_VLAN")
        t.read(u"SSH@my_switch(config-vlan-2995)#")
        t.write(u"tagged ethernet 1/1")
        t.read(u"SSH@my_switch(config-vlan-2995)#")
        t.write(u"router-interface ve 2995 ")
        t.read(u"SSH@my_switch(config-vlan-2995)#")
        t.write(u"interface ve 2995")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"ip address 10.0.0.2/29")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"ip vrrp-extended vrid 1")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"backup priority 160 track-priority 13")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"ip-address 10.0.0.1")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"ip-address 10.0.0.3")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"ip-address 10.0.0.4")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"hello-interval 5")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"dead-interval 15")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"advertise backup")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"track-port ethernet 2/4")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"backup priority 110 track-priority 50")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-1)#")
        t.write(u"activate")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"ip vrrp-extended vrid 2")
        t.read(u"SSH@my_switch(config-vif-2995-vrid-2)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"ip vrrp-extended auth-type simple-text-auth ABCD")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u" ip address 10.0.0.2/29",
            u" ip vrrp-extended auth-type simple-text-auth ********",
            u" ip vrrp-extended vrid 1",
            u"  backup priority 110 track-priority 50",
            u"  ip-address 10.0.0.1",
            u"  ip-address 10.0.0.3",
            u"  ip-address 10.0.0.4",
            u"  advertise backup",
            u"  dead-interval 15",
            u"  hello-interval 5",
            u"  track-port ethernet 2/4",
            u"  activate",
            u" ip vrrp-extended vrid 2",
            u"  exit",
            u"!"])

        configuring_interface_vlan_vrrp(t, 2995, 1, u"no advertise backup")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no ip-address 10.0.0.1")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no ip-address 10.0.0.3")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no ip-address 10.0.0.4")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no activate")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no dead-interval 15")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no hello-interval 5")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no track-port ethernet 2/4")
        configuring_interface_vlan_vrrp(t, 2995, 1, u"no backup")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u" ip address 10.0.0.2/29",
            u" ip vrrp-extended auth-type simple-text-auth ********",
            u" ip vrrp-extended vrid 1",
            u"  exit",
            u" ip vrrp-extended vrid 2",
            u"  exit",
            u"!"])

        configuring_interface_vlan(t, 2995, u"no ip vrrp-extended vrid 1")
        configuring_interface_vlan(t, 2995, u"no ip vrrp-extended vrid 2")
        configuring_interface_vlan(t, 2995, u"no ip address 10.0.0.2/29")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u" ip vrrp-extended auth-type simple-text-auth ********",
            u"!"])

        configuring_interface_vlan(t, 2995, u"no ip vrrp-extended auth-type simple-text-auth ABC")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u"!"])

        configuring(t, do=u"no interface ve 2995")
        remove_vlan(t, u"2995")

    @with_protocol
    def test_ip_helper(self, t):
        enable(t)

        create_vlan(t, u"2995")
        create_interface_vlan(t, u"2995")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u"!"])

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 2995")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"ip helper-address")
        t.readln(u"Incomplete command.")
        t.read(u"SSH@my_switch(config-vif-2995)#")

        t.write(u"ip helper-address 10.10.0.1 EXTRA INFO")
        t.readln(u"Invalid input -> EXTRA INFO")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        configuring_interface_vlan(t, vlan=u"2995", do=u"ip helper-address 10.10.0.1")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u" ip helper-address 10.10.0.1",
            u"!"])

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 2995")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"ip helper-address 10.10.0.1")
        t.readln(u"UDP: Errno(7) Duplicate helper address")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        configuring_interface_vlan(t, vlan=u"2995", do=u"ip helper-address 10.10.0.2")
        configuring_interface_vlan(t, vlan=u"2995", do=u"ip helper-address 10.10.0.3")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u" ip helper-address 10.10.0.1",
            u" ip helper-address 10.10.0.2",
            u" ip helper-address 10.10.0.3",
            u"!"])

        configuring_interface_vlan(t, vlan=u"2995", do=u"no ip helper-address 10.10.0.1")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u" ip helper-address 10.10.0.2",
            u" ip helper-address 10.10.0.3",
            u"!"])

        t.write(u"configure terminal")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"interface ve 2995")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"no ip helper-address")
        t.readln(u"Incomplete command.")
        t.read(u"SSH@my_switch(config-vif-2995)#")

        t.write(u"no ip helper-address 10.10.0.1")
        t.readln(u"UDP: Errno(10) Helper address not configured")
        t.read(u"SSH@my_switch(config-vif-2995)#")

        t.write(u"no ip helper-address 10.10.0.2 EXTRA INFO")
        t.readln(u"Invalid input -> EXTRA INFO")
        t.readln(u"Type ? for a list")
        t.read(u"SSH@my_switch(config-vif-2995)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch(config)#")
        t.write(u"exit")
        t.read(u"SSH@my_switch#")

        configuring_interface_vlan(t, vlan=u"2995", do=u"no ip helper-address 10.10.0.2")
        configuring_interface_vlan(t, vlan=u"2995", do=u"no ip helper-address 10.10.0.3")

        assert_interface_configuration(t, u"ve 2995", [
            u"interface ve 2995",
            u"!"])

        configuring(t, do=u"no interface ve 2995")
        remove_vlan(t, u"2995")

    @with_protocol
    def test_show_vlan(self, t):
        enable(t)

        t.write(u"show vlan 1600")
        t.readln(u"Error: vlan 1600 is not configured")
        t.read(u"SSH@my_switch#")

        create_vlan(t, u"1600")

        t.write(u"show vlan 1600")
        t.readln(u"")
        t.readln(u"PORT-VLAN 1600, Name [None], Priority Level -, Priority Force 0, Creation Type STATIC")
        t.readln(u"Topo HW idx    : 81    Topo SW idx: 257    Topo next vlan: 0")
        t.readln(u"L2 protocols   : STP")
        t.readln(u"Associated Virtual Interface Id: NONE")
        t.readln(u"----------------------------------------------------------")
        t.readln(u"No ports associated with VLAN")
        t.readln(u"Arp Inspection: 0")
        t.readln(u"DHCP Snooping: 0")
        t.readln(u"IPv4 Multicast Snooping: Disabled")
        t.readln(u"IPv6 Multicast Snooping: Disabled")
        t.readln(u"")
        t.readln(u"No Virtual Interfaces configured for this vlan")
        t.read(u"SSH@my_switch#")

        create_vlan(t, u"1600", name=u"Shizzle")
        configuring_vlan(t, u"1600", do=u"router-interface ve 999")

        t.write(u"show vlan 1600")
        t.readln(u"")
        t.readln(u"PORT-VLAN 1600, Name Shizzle, Priority Level -, Priority Force 0, Creation Type STATIC")
        t.readln(u"Topo HW idx    : 81    Topo SW idx: 257    Topo next vlan: 0")
        t.readln(u"L2 protocols   : STP")
        t.readln(u"Associated Virtual Interface Id: 999")
        t.readln(u"----------------------------------------------------------")
        t.readln(u"No ports associated with VLAN")
        t.readln(u"Arp Inspection: 0")
        t.readln(u"DHCP Snooping: 0")
        t.readln(u"IPv4 Multicast Snooping: Disabled")
        t.readln(u"IPv6 Multicast Snooping: Disabled")
        t.readln(u"")
        t.readln(u"Ve999 is down, line protocol is down")
        t.readln(u"  Type is Vlan (Vlan Id: 1600)")
        t.readln(u"  Hardware is Virtual Ethernet, address is 748e.f8a7.1b01 (bia 748e.f8a7.1b01)")
        t.readln(u"  No port name")
        t.readln(u"  Vlan id: 1600")
        t.readln(u"  Internet address is 0.0.0.0/0, IP MTU 1500 bytes, encapsulation ethernet")
        t.readln(u"  Configured BW 0 kbps")
        t.read(u"SSH@my_switch#")

        configuring_vlan(t, u"1600", do=u"no router-interface 999")
        remove_vlan(t, u"1600")

    @with_protocol
    def test_show_vlan_has_tagged_untagged_ports(self, t):
        enable(t)
        create_vlan(t, u"1600")
        set_interface_untagged_on_vlan(t, u"ethernet 1/2", u"1600")

        t.write(u"show vlan 1600")
        t.readln(u"")
        t.readln(u"PORT-VLAN 1600, Name [None], Priority Level -, Priority Force 0, Creation Type STATIC")
        t.readln(u"Topo HW idx    : 81    Topo SW idx: 257    Topo next vlan: 0")
        t.readln(u"L2 protocols   : STP")
        t.readln(u"Untagged Ports : ethe 1/2")
        t.readln(u"Associated Virtual Interface Id: NONE")
        t.readln(u"----------------------------------------------------------")
        t.readln(u"Port  Type      Tag-Mode  Protocol  State")
        t.readln(u"1/2   PHYSICAL  UNTAGGED  STP       DISABLED")
        t.readln(u"Arp Inspection: 0")
        t.readln(u"DHCP Snooping: 0")
        t.readln(u"IPv4 Multicast Snooping: Disabled")
        t.readln(u"IPv6 Multicast Snooping: Disabled")
        t.readln(u"")
        t.readln(u"No Virtual Interfaces configured for this vlan")
        t.read(u"SSH@my_switch#")

        set_interface_tagged_on_vlan(t, u"ethernet 1/4", u"1600")

        t.write(u"show vlan 1600")
        t.readln(u"")
        t.readln(u"PORT-VLAN 1600, Name [None], Priority Level -, Priority Force 0, Creation Type STATIC")
        t.readln(u"Topo HW idx    : 81    Topo SW idx: 257    Topo next vlan: 0")
        t.readln(u"L2 protocols   : STP")
        t.readln(u"Statically tagged Ports    : ethe 1/4")
        t.readln(u"Untagged Ports : ethe 1/2")
        t.readln(u"Associated Virtual Interface Id: NONE")
        t.readln(u"----------------------------------------------------------")
        t.readln(u"Port  Type      Tag-Mode  Protocol  State")
        t.readln(u"1/2   PHYSICAL  UNTAGGED  STP       DISABLED")
        t.readln(u"1/4   PHYSICAL  TAGGED    STP       DISABLED")
        t.readln(u"Arp Inspection: 0")
        t.readln(u"DHCP Snooping: 0")
        t.readln(u"IPv4 Multicast Snooping: Disabled")
        t.readln(u"IPv6 Multicast Snooping: Disabled")
        t.readln(u"")
        t.readln(u"No Virtual Interfaces configured for this vlan")
        t.read(u"SSH@my_switch#")

        set_interface_tagged_on_vlan(t, u"ethernet 1/3", u"1600")

        t.write(u"show vlan 1600")
        t.readln(u"")
        t.readln(u"PORT-VLAN 1600, Name [None], Priority Level -, Priority Force 0, Creation Type STATIC")
        t.readln(u"Topo HW idx    : 81    Topo SW idx: 257    Topo next vlan: 0")
        t.readln(u"L2 protocols   : STP")
        t.readln(u"Statically tagged Ports    : ethe 1/3 to 1/4")
        t.readln(u"Untagged Ports : ethe 1/2")
        t.readln(u"Associated Virtual Interface Id: NONE")
        t.readln(u"----------------------------------------------------------")
        t.readln(u"Port  Type      Tag-Mode  Protocol  State")
        t.readln(u"1/2   PHYSICAL  UNTAGGED  STP       DISABLED")
        t.readln(u"1/3   PHYSICAL  TAGGED    STP       DISABLED")
        t.readln(u"1/4   PHYSICAL  TAGGED    STP       DISABLED")
        t.readln(u"Arp Inspection: 0")
        t.readln(u"DHCP Snooping: 0")
        t.readln(u"IPv4 Multicast Snooping: Disabled")
        t.readln(u"IPv6 Multicast Snooping: Disabled")
        t.readln(u"")
        t.readln(u"No Virtual Interfaces configured for this vlan")
        t.read(u"SSH@my_switch#")

        unset_interface_untagged_on_vlan(t, u"ethernet 1/2", u"1600")
        unset_interface_tagged_on_vlan(t, u"ethernet 1/3", u"1600")
        unset_interface_tagged_on_vlan(t, u"ethernet 1/4", u"1600")
        remove_vlan(t, u"1600")

    @with_protocol
    def test_show_version(self, t):
        enable(t)

        t.write(u"show version")

        t.readln(u"System: NetIron CER (Serial #: 1P2539K036,  Part #: 40-1000617-02)")
        t.readln(u"License: RT_SCALE, ADV_SVCS_PREM (LID: XXXXXXXXXX)")
        t.readln(u"Boot     : Version 5.8.0T185 Copyright (c) 1996-2014 Brocade Communications Systems, Inc.")
        t.readln(u"Compiled on May 18 2015 at 13:03:00 labeled as ceb05800")
        t.readln(u" (463847 bytes) from boot flash")
        t.readln(u"Monitor  : Version 5.8.0T185 Copyright (c) 1996-2014 Brocade Communications Systems, Inc.")
        t.readln(u"Compiled on May 18 2015 at 13:03:00 labeled as ceb05800")
        t.readln(u" (463847 bytes) from code flash")
        t.readln(u"IronWare : Version 5.8.0bT183 Copyright (c) 1996-2014 Brocade Communications Systems, Inc.")
        t.readln(u"Compiled on May 21 2015 at 09:20:22 labeled as ce05800b")
        t.readln(u" (17563175 bytes) from Primary")
        t.readln(u"CPLD Version: 0x00000010")
        t.readln(u"Micro-Controller Version: 0x0000000d")
        t.readln(u"Extended route scalability")
        t.readln(u"PBIF Version: 0x0162")
        t.readln(u"800 MHz Power PC processor 8544 (version 8021/0023) 400 MHz bus")
        t.readln(u"512 KB Boot Flash (MX29LV040C), 64 MB Code Flash (MT28F256J3)")
        t.readln(u"2048 MB DRAM")
        t.readln(u"System uptime is 109 days 4 hours 39 minutes 4 seconds")

        t.read(u"SSH@my_switch#")

    @with_protocol
    def test_ip_redirect(self, t):
        enable(t)

        create_interface_vlan(t, u"1201")
        configuring_interface_vlan(t, u"1201", do=u"no ip redirect")

        assert_interface_configuration(t, u"ve 1201", [
            u"interface ve 1201",
            u" no ip redirect",
            u"!"
        ])

        configuring_interface_vlan(t, u"1201", do=u"ip redirect")

        assert_interface_configuration(t, u"ve 1201", [
            u"interface ve 1201",
            u"!"
        ])

        remove_vlan(t, u"1201")

def enable(t):
    t.write(u"enable")
    t.read(u"Password:")
    t.write_invisible(brocade_privileged_password)
    t.read(u"SSH@my_switch#")


def create_vlan(t, vlan, name=None):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    if name:
        t.write(u"vlan {} name {}".format(vlan, name))
        t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    else:
        t.write(u"vlan {}".format(vlan))
        t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def remove_vlan(t, vlan):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"no vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def set_interface_untagged_on_vlan(t, interface, vlan):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"untagged {}".format(interface))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def unset_interface_untagged_on_vlan(t, interface, vlan):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"no untagged {}".format(interface))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def set_interface_tagged_on_vlan(t, interface, vlan):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"tagged {}".format(interface))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def unset_interface_tagged_on_vlan(t, interface, vlan):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"no tagged {}".format(interface))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def remove_interface_from_vlan(t, interface, vlan):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"no untagged {}".format(interface))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def assert_interface_configuration(t, interface, config):
    t.write(u"show running-config interface {} ".format(interface))
    for line in config:
        t.readln(line)
    t.readln(u"")
    t.read(u"SSH@my_switch#")


def configuring_interface(t, interface, do):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"interface ethe {}".format(interface))
    t.read(u"SSH@my_switch(config-if-e1000-{})#".format(interface))

    t.write(do)

    t.read(u"SSH@my_switch(config-if-e1000-{})#".format(interface))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def configuring_interface_vlan(t, vlan, do):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"interface ve {}".format(vlan))
    t.read(u"SSH@my_switch(config-vif-{})#".format(vlan))

    t.write(do)

    t.read(u"SSH@my_switch(config-vif-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def configuring_access_group_interface_vlan(t, vlan, do):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"interface ve {}".format(vlan))
    t.read(u"SSH@my_switch(config-vif-{})#".format(vlan))

    t.write(do)

    t.readln(u"Warning: An undefined or zero length ACL has been applied. "
             u"Filtering will not occur for the specified interface VE {} (outbound).".format(vlan))
    t.read(u"SSH@my_switch(config-vif-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def configuring_interface_vlan_vrrp(t, vlan, group, do):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"interface ve {}".format(vlan))
    t.read(u"SSH@my_switch(config-vif-{})#".format(vlan))
    t.write(u"ip vrrp vrid {}".format(group))
    t.read(u"SSH@my_switch(config-vif-{}-vrid-{})#".format(vlan, group))

    t.write(do)

    t.read(u"SSH@my_switch(config-vif-{}-vrid-{})#".format(vlan, group))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config-vif-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def configuring_vlan(t, vlan, do):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))

    t.write(do)

    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def configuring(t, do):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")

    t.write(do)

    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")


def create_interface_vlan(t, vlan):
    t.write(u"configure terminal")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"vlan {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"router-interface ve {}".format(vlan))
    t.read(u"SSH@my_switch(config-vlan-{})#".format(vlan))
    t.write(u"exit")
    t.read(u"SSH@my_switch(config)#")
    t.write(u"exit")
    t.read(u"SSH@my_switch#")
