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

from hamcrest import assert_that, is_
import pprint

from tests.util.global_reactor import dell_privileged_password, dell_switch_ip, \
    dell_switch_ssh_port, dell_switch_telnet_port
from tests.util.protocol_util import SshTester, TelnetTester


def ssh_protocol_factory(*_):
    return SshTester(u"ssh", dell_switch_ip, dell_switch_ssh_port, u'root', u'root')


def telnet_protocol_factory(*_):
    return TelnetTester(u"ssh", dell_switch_ip, dell_switch_telnet_port, u'root', u'root')


def enable(t):
    t.write(u"enable")
    t.read(u"Password:")
    t.write_stars(dell_privileged_password)
    t.readln(u"")
    t.read(u"my_switch#")


def configure(t):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")


def configuring_interface(t, interface, do):
    interface_short_name = interface.split(u' ')[1]
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"interface %s" % interface)
    t.readln(u"")
    t.read(u"my_switch(config-if-%s)#" % interface_short_name)

    t.write(do)

    t.readln(u"")
    t.read(u"my_switch(config-if-%s)#" % interface_short_name)
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def configuring_bond(t, bond, do):
    bond_number = bond.split(u' ')[1]
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"interface %s" % bond)
    t.readln(u"")
    t.read(u"my_switch(config-if-ch%s)#" % bond_number)

    t.write(do)

    t.readln(u"")
    t.read(u"my_switch(config-if-ch%s)#" % bond_number)
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def configuring_a_vlan_on_interface(t, interface, do):
    interface_short_name = interface.split(u' ')[1]
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"interface %s" % interface)
    t.readln(u"")
    t.read(u"my_switch(config-if-%s)#" % interface_short_name)

    t.write(do)

    t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
    t.readln(u"delays in applying the configuration.")
    t.readln(u"")
    t.readln(u"")
    t.read(u"my_switch(config-if-%s)#" % interface_short_name)
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def configuring_interface_vlan(t, vlan, do):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"interface vlan {}".format(vlan))
    t.readln(u"")
    t.read(u"my_switch(config-if-vlan{})#".format(vlan))

    t.write(do)

    t.readln(u"")
    t.read(u"my_switch(config-if-vlan{})#".format(vlan))
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def configuring_vlan(t, vlan_id):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")

    t.write(u"vlan database")
    t.readln(u"")
    t.read(u"my_switch(config-vlan)#")

    t.write(u"vlan %s" % vlan_id)
    t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
    t.readln(u"delays in applying the configuration.")
    t.readln(u"")

    t.readln(u"")
    t.read(u"my_switch(config-vlan)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def unconfigure_vlan(t, vlan_id):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")

    t.write(u"vlan database")
    t.readln(u"")
    t.read(u"my_switch(config-vlan)#")

    t.write(u"no vlan %s" % vlan_id)
    t.readln(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
    t.readln(u"delays in applying the configuration.")
    t.readln(u"")
    t.readln(u"If any of the VLANs being deleted are for access ports, the ports will be")
    t.readln(u"unusable until it is assigned a VLAN that exists.")
    t.readln(u"")

    t.read(u"my_switch(config-vlan)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def create_bond(t, bond_id):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"interface port-channel {}".format(bond_id))
    t.readln(u"")
    t.read(u"my_switch(config-if-ch{})#".format(bond_id))
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def remove_bond(t, bond_id):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"no interface port-channel {}".format(bond_id))
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def assert_interface_configuration(t, interface, config):
    t.write(u"show running-config interface %s " % interface)
    for line in config:
        t.readln(line)
    t.readln(u"")
    t.read(u"my_switch#")


def assert_running_config_contains_in_order(t, lines):
    config = get_running_config(t)

    assert_lines_order(config, lines)


def get_running_config(t):
    t.write(u"show running-config")
    config = t.read_lines_until(u'my_switch#')
    return config


def assert_lines_order(config, lines):
    begin = config.index(lines[0])

    for (i, line) in enumerate(lines):
        expected_content = line
        expected_line_number = i + begin
        actual_content = config[expected_line_number]

        assert_that(actual_content, is_(expected_content),
                    u"Item <%s> was expected to be found at line %s but found %s instead.\nWas looking for %s in %s" % (
                        line, expected_line_number, actual_content, pprint.pformat(lines), pprint.pformat(config)))
