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

import pprint

from hamcrest import assert_that, is_

from tests.util.global_reactor import dell10g_privileged_password, dell10g_switch_ip, \
    dell10g_switch_ssh_port, dell10g_switch_telnet_port
from tests.util.protocol_util import SshTester, TelnetTester


def ssh_protocol_factory(*_):
    return SshTester(u"ssh", dell10g_switch_ip, dell10g_switch_ssh_port, u'root', u'root')


def telnet_protocol_factory(*_):
    return TelnetTester(u"ssh", dell10g_switch_ip, dell10g_switch_telnet_port, u'root', u'root')


def enable(t):
    t.write(u"enable")
    t.read(u"Password:")
    t.write_stars(dell10g_privileged_password)
    t.readln(u"")
    t.read(u"my_switch#")


def configuring(t, do):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")

    t.write(do)

    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def add_vlan(t, vlan_id):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"vlan {}".format(vlan_id))
    t.readln(u"")
    t.read(u"my_switch(config-vlan{})#".format(vlan_id))
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def configuring_vlan(t, vlan_id, do):
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")

    t.write(u"vlan {}".format(vlan_id))
    t.readln(u"")

    t.read(u"my_switch(config-vlan{})#".format(vlan_id))

    t.write(do)
    t.readln(u"")

    t.read(u"my_switch(config-vlan{})#".format(vlan_id))
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"exit")
    t.readln(u"")
    t.read(u"my_switch#")


def configuring_interface(t, interface, do):
    interface_short_name = interface.split(u' ')[1]
    t.write(u"configure")
    t.readln(u"")
    t.read(u"my_switch(config)#")
    t.write(u"interface {}".format(interface))
    t.readln(u"")
    t.read(u"my_switch(config-if-Te{})#".format(interface_short_name))

    t.write(do)

    t.readln(u"")
    t.read(u"my_switch(config-if-Te{})#".format(interface_short_name))
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
    t.read(u"my_switch(config-if-Po{})#".format(bond_id))
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
    t.write(u"show running-config interface {}".format(interface))
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
                    u"Item <%s> was expected to be found at line {} but found {} instead.\nWas looking for {} in {}".format(
                        line, expected_line_number, actual_content, pprint.pformat(lines), pprint.pformat(config)))
