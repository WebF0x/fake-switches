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

from netaddr import IPNetwork
from netaddr.ip import IPAddress

from fake_switches.switch_configuration import VlanPort
from fake_switches.command_processing.base_command_processor import BaseCommandProcessor


class ConfigInterfaceCommandProcessor(BaseCommandProcessor):

    def __init__(self, switch_configuration, terminal_controller, logger, piping_processor, port):
        BaseCommandProcessor.__init__(self, switch_configuration, terminal_controller, logger, piping_processor)
        self.description_strip_chars = u"\""
        self.port = port

    def get_prompt(self):
        return self.switch_configuration.name + u"(config-if)#"

    def do_switchport(self, *args):
        if args[0:1] == (u"mode",):
            self.port.mode = args[1]
        elif args[0:2] == (u"access", u"vlan"):
            self.port.access_vlan = int(args[2])
        elif args[0:2] == (u"trunk", u"encapsulation"):
            self.port.trunk_encapsulation_mode = args[2]
        elif args[0:4] == (u"trunk", u"allowed", u"vlan", u"add"):
            if self.port.trunk_vlans is not None: #for cisco, no list = all vlans
                self.port.trunk_vlans += parse_vlan_list(args[4])
        elif args[0:4] == (u"trunk", u"allowed", u"vlan", u"remove"):
            if self.port.trunk_vlans is None:
                self.port.trunk_vlans = list(range(1, 4097))
            for v in parse_vlan_list(args[4]):
                if v in self.port.trunk_vlans:
                    self.port.trunk_vlans.remove(v)
        elif args[0:4] == (u"trunk", u"allowed", u"vlan", u"none"):
            self.port.trunk_vlans = []
        elif args[0:4] == (u"trunk", u"allowed", u"vlan", u"all"):
            self.port.trunk_vlans = None
        elif args[0:3] == (u"trunk", u"allowed", u"vlan"):
            self.port.trunk_vlans = parse_vlan_list(args[3])
        elif args[0:3] == (u"trunk", u"native", u"vlan"):
            self.port.trunk_native_vlan = int(args[3])

    def do_no_switchport(self, *args):
        if args[0:2] == (u"access", u"vlan"):
            self.port.access_vlan = None
        elif args[0:1] == (u"mode",):
            self.port.mode = None
        elif args[0:3] == (u"trunk", u"allowed", u"vlan"):
            self.port.trunk_vlans = None
        elif args[0:3] == (u"trunk", u"native", u"vlan"):
            self.port.trunk_native_vlan = None

    def do_channel_group(self, *args):
        port_channel_id = args[0]
        port_channel_name = u"Port-channel%s" % port_channel_id

        if not self.port_channel_exists(port_channel_name):
            self.write_line(u"Creating a port-channel interface Port-channel %s" % port_channel_id)
            self.create_port_channel(port_channel_name)
        self.port.aggregation_membership = port_channel_name

    def do_no_channel_group(self, *_):
        self.port.aggregation_membership = None

    def do_description(self, *args):
        self.port.description = u" ".join(args).strip(self.description_strip_chars)

    def do_no_description(self, *_):
        self.port.description = None

    def do_shutdown(self, *_):
        self.port.shutdown = True

    def do_no_shutdown(self, *_):
        self.port.shutdown = False

    def do_ip(self, *args):

        if u"address".startswith(args[0]):
            new_ip = IPNetwork(u"%s/%s" % (args[1], args[2]))
            ip_owner, existing_ip = self.switch_configuration.get_port_and_ip_by_ip(new_ip.ip)
            if not ip_owner or ip_owner == self.port:
                if len(args) == 4 and u"secondary".startswith(args[3]):
                    self.port.add_ip(new_ip)
                else:
                    if len(self.port.ips) == 0:
                        self.port.add_ip(new_ip)
                    else:
                        if ip_owner == self.port:
                            self.port.remove_ip(new_ip)
                        self.port.ips[0] = new_ip
            else:
                if ip_owner.ips.index(existing_ip) == 0:
                    self.write_line(u"%% %s overlaps with secondary address on %s" % (existing_ip.network, ip_owner.name))
                else:
                    self.write_line(u"%% %s is assigned as a secondary address on %s" % (existing_ip.network, ip_owner.name))

        if u"access-group".startswith(args[0]):
            if u"in".startswith(args[2]):
                self.port.access_group_in = args[1]
            if u"out".startswith(args[2]):
                self.port.access_group_out = args[1]

        if u"vrf".startswith(args[0]):
            if u"forwarding".startswith(args[1]):
                if isinstance(self.port, VlanPort):
                    for ip in self.port.ips[:]:
                        self.port.remove_ip(ip)
                vrf = self.switch_configuration.get_vrf(args[2])
                if vrf:
                    self.port.vrf = vrf
                else:
                    self.write_line(u"%% VRF %s not configured." % args[2])
        if u"redirects".startswith(args[0]):
            self.port.ip_redirect = True

        if u"helper-address".startswith(args[0]):
            if len(args) == 1:
                self.write_line(u"% Incomplete command.")
                self.write_line(u"")
            elif len(args) > 2:
                self.write_line(u" ^")
                self.write_line(u"% Invalid input detected at '^' marker.")
                self.write_line(u"")
            else:
                ip_address = IPAddress(args[1])
                if ip_address not in self.port.ip_helpers:
                    self.port.ip_helpers.append(ip_address)

    def do_no_ip(self, *args):
        if u"address".startswith(args[0]):
            if len(args) == 1:
                self.port.ips = []
            else:
                ip = IPNetwork(u"%s/%s" % (args[1], args[2]))
                is_secondary = u"secondary".startswith(args[3]) if len(args) == 4 else False
                if is_secondary:
                    self.port.remove_ip(ip)
                else:
                    if len(self.port.ips) == 1:
                        self.port.remove_ip(ip)
                    else:
                        self.write_line(u"Must delete secondary before deleting primary")
        if u"access-group".startswith(args[0]):
            direction = args[-1]
            if u"in".startswith(direction):
                self.port.access_group_in = None
            elif u"out".startswith(direction):
                self.port.access_group_out = None
        if u"vrf".startswith(args[0]):
            if u"forwarding".startswith(args[1]):
                self.port.vrf = None
        if u"redirects".startswith(args[0]):
            self.port.ip_redirect = False

        if u"helper-address".startswith(args[0]):
            if len(args) > 2:
                self.write_line(u" ^")
                self.write_line(u"% Invalid input detected at '^' marker.")
                self.write_line(u"")
            else:
                if len(args) == 1:
                    self.port.ip_helpers = []
                else:
                    ip_address = IPAddress(args[1])
                    if ip_address in self.port.ip_helpers:
                        self.port.ip_helpers.remove(ip_address)

    def do_standby(self, group, command, *args):
        vrrp = self.port.get_vrrp_group(group)
        if vrrp is None:
            vrrp = self.switch_configuration.new(u"VRRP", group)
            self.port.vrrps.append(vrrp)

        if u"ip".startswith(command):
            if len(args) == 0:
                vrrp.ip_addresses = vrrp.ip_addresses or []
            else:
                ip = _parse_ip(args[0])
                if ip is not None:
                    in_networks = any(ip in net for net in self.port.ips)
                    if in_networks:
                        vrrp.ip_addresses = vrrp.ip_addresses or []
                        if len(args) > 1 and u"secondary".startswith(args[1]):
                            vrrp.ip_addresses.append(ip)
                        else:
                            vrrp.ip_addresses = [ip] + vrrp.ip_addresses[1:]
                    else:
                        self.write_line(u"% Warning: address is not within a subnet on this interface")

                else:
                    self.write_line(u" ^")
                    self.write_line(u"% Invalid input detected at '^' marker.")
                    self.write_line(u"")

        if u"timers".startswith(command):
            vrrp.timers_hello = args[0]
            vrrp.timers_hold = args[1]

        if u"priority".startswith(command):
            vrrp.priority = args[0]

        if u"authentication".startswith(command):
            vrrp.authentication = args[0]

        if u"track".startswith(command) and u"decrement".startswith(args[1]):
            vrrp.track.update({args[0]: args[2]})

        if u"preempt".startswith(command):
            vrrp.preempt = True
            if len(args) > 0 and u" ".join(args[0:2]) == u"delay minimum":
                vrrp.preempt_delay_minimum = args[2]

    def do_no_standby(self, group, *cmd_args):
        vrrp = self.port.get_vrrp_group(group)

        if vrrp is None:
            return

        if len(cmd_args) == 0:
            self.port.vrrps.remove(vrrp)

        else:
            command = cmd_args[0]
            args = cmd_args[1:]

            if u"ip".startswith(command):
                if len(args) == 0:
                    vrrp.ip_addresses = None
                else:
                    vrrp.ip_addresses.remove(IPAddress(args[0]))
                    if len(vrrp.ip_addresses) == 0:
                        vrrp.ip_addresses = None

            if u"authentication".startswith(command):
                vrrp.authentication = None

            if u"priority".startswith(command):
                vrrp.priority = None

            if u"timers".startswith(command):
                vrrp.timers_hello = None
                vrrp.timers_hold = None

            if u"track".startswith(command) and args[0] in vrrp.track:
                del vrrp.track[args[0]]

            if u"preempt".startswith(command):
                if len(args) > 0 and u"delay".startswith(args[0]):
                    vrrp.preempt_delay_minimum = None
                else:
                    vrrp.preempt_delay_minimum = None
                    vrrp.preempt = None

    def do_exit(self):
        self.is_done = True

    def port_channel_exists(self, name):
        return self.switch_configuration.get_port_by_partial_name(name) is not None

    def create_port_channel(self, name):
        port = self.switch_configuration.new(u"AggregatedPort", name)
        self.port.switch_configuration.add_port(port)


def parse_vlan_list(param):
    ranges = param.split(u",")
    vlans = []
    for r in ranges:
        if u"-" in r:
            start, stop = r.split(u"-")
            vlans += [v for v in range(int(start), int(stop) + 1)]
        else:
            vlans.append(int(r))

    return vlans


def _parse_ip(ip):
    try:
        return IPAddress(ip)
    except:
        return None
