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

from functools import partial

import re
import textwrap
from fake_switches.command_processing.switch_tftp_parser import SwitchTftpParser
from fake_switches.command_processing.base_command_processor import BaseCommandProcessor
from fake_switches.cisco.command_processor.config import ConfigCommandProcessor
from fake_switches.switch_configuration import VlanPort, AggregatedPort
from fake_switches import group_sequences


class EnabledCommandProcessor(BaseCommandProcessor):

    def get_prompt(self):
        return self.switch_configuration.name + u"#"

    def do_enable(self, *args):
        pass

    def do_configure(self, *_):
        self.write_line(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        self.move_to(ConfigCommandProcessor)

    def do_show(self, *args):
        if u"running-config".startswith(args[0]):
            if len(args) < 2:
                self.show_run()
            elif u"vlan".startswith(args[1]):
                self.write_line(u"Building configuration...")
                self.write_line(u"")
                self.write_line(u"Current configuration:")
                for vlan in self.switch_configuration.vlans:
                    if vlan.number == int(args[2]):
                        self.write_line(u"\n".join([u"!"] + build_running_vlan(vlan)))
                self.write_line(u"end")
                self.write_line(u"")
            elif u"interface".startswith(args[1]):
                if_name = u"".join(args[2:])
                port = self.switch_configuration.get_port_by_partial_name(if_name)

                if port:
                    self.write_line(u"Building configuration...")
                    self.write_line(u"")

                    data = [u"!"] + build_running_interface(port) + [u"end", u""]

                    self.write_line(u"Current configuration : %i bytes" % (len(u"\n".join(data)) + 1))
                    [self.write_line(l) for l in data]
                else:
                    self.write_line(u"                               ^")
                    self.write_line(u"% Invalid input detected at '^' marker.")
                    self.write_line(u"")

        elif u"vlan".startswith(args[0]):
            self.write_line(u"")
            self.write_line(u"VLAN Name                             Status    Ports")
            self.write_line(u"---- -------------------------------- --------- -------------------------------")
            for vlan in sorted(self.switch_configuration.vlans, key=lambda v: v.number):
                ports = [port.get_subname(length=2) for port in self.switch_configuration.ports
                         if port.access_vlan == vlan.number or (vlan.number == 1 and port.access_vlan is None)]
                self.write_line(u"%-4s %-32s %s%s" % (
                    vlan.number,
                     vlan_name(vlan) if vlan_name(vlan) else u"VLAN%s" % vlan.number,
                    u"active",
                    (u"    " + u", ".join(ports)) if ports else u""
                ))
            if len(args) == 1:
                self.write_line(u"")
                self.write_line(u"VLAN Type  SAID       MTU   Parent RingNo BridgeNo Stp  BrdgMode Trans1 Trans2")
                self.write_line(u"---- ----- ---------- ----- ------ ------ -------- ---- -------- ------ ------")
                for vlan in sorted(self.switch_configuration.vlans, key=lambda v: v.number):
                    self.write_line(u"%-4s enet  10%04d     1500  -      -      -        -    -        0      0" % (vlan.number, vlan.number))
                self.write_line(u"")
                self.write_line(u"Remote SPAN VLANs")
                self.write_line(u"------------------------------------------------------------------------------")
                self.write_line(u"")
                self.write_line(u"")
                self.write_line(u"Primary Secondary Type              Ports")
                self.write_line(u"------- --------- ----------------- ------------------------------------------")
                self.write_line(u"")
        elif u"etherchannel".startswith(args[0]) and len(args) == 2 and u"summary".startswith(args[1]):
            ports = sorted(self.switch_configuration.ports, key=lambda x: x.name)
            port_channels = sorted(
                [p for p in ports if isinstance(p, AggregatedPort)],
                key=port_channel_number)
            self.write_line(u"Flags:  D - down        P - bundled in port-channel")
            self.write_line(u"        I - stand-alone s - suspended")
            self.write_line(u"        H - Hot-standby (LACP only)")
            self.write_line(u"        R - Layer3      S - Layer2")
            self.write_line(u"        U - in use      f - failed to allocate aggregator")
            self.write_line(u"")
            self.write_line(u"        M - not in use, minimum links not met")
            self.write_line(u"        u - unsuitable for bundling")
            self.write_line(u"        w - waiting to be aggregated")
            self.write_line(u"        d - default port")
            self.write_line(u"")
            self.write_line(u"")
            self.write_line(u"Number of channel-groups in use: {}".format(len(port_channels)))
            self.write_line(u"Number of aggregators:           {}".format(len(port_channels)))
            self.write_line(u"")
            self.write_line(u"Group  Port-channel  Protocol    Ports")
            self.write_line(u"------+-------------+-----------+-----------------------------------------------")
            for port_channel in port_channels:
                members = [short_name(p) for p in ports
                           if p.aggregation_membership == port_channel.name]
                self.write_line(
                    u"{: <6} {: <13} {: <11} {}".format(
                        port_channel_number(port_channel),
                        u"{}(S{})".format(short_name(port_channel), u"U" if members else u""),
                        u"  LACP",
                        u"  ".join(u"{}(P)".format(m) for m in members)))
            self.write_line(u"")
        elif u"ip".startswith(args[0]):
            if u"interface".startswith(args[1]):
                if_list = None
                if len(args) > 2:
                    interface = self.switch_configuration.get_port_by_partial_name(u"".join(args[2:]))
                    if interface:
                        if_list = [interface]
                    else:
                        self.write_line(u"                                 ^")
                        self.write_line(u"% Invalid input detected at '^' marker.")
                        self.write_line(u"")
                else:
                    if_list = sorted(self.switch_configuration.ports, key=lambda e: (u"a" if isinstance(e, VlanPort) else u"b") + e.name)
                if if_list:
                    for interface in if_list:
                        self.write_line(u"%s is down, line protocol is down" % interface.name)
                        if not isinstance(interface, VlanPort):
                            self.write_line(u"  Internet protocol processing disabled")
                        else:
                            if len(interface.ips) == 0:
                                self.write_line(u"  Internet protocol processing disabled")
                            else:
                                self.write_line(u"  Internet address is %s" % interface.ips[0])
                                for ip in interface.ips[1:]:
                                    self.write_line(u"  Secondary address %s" % ip)
                                self.write_line(u"  Outgoing access list is %s" % (interface.access_group_out if interface.access_group_out else u"not set"))
                                self.write_line(u"  Inbound  access list is %s" % (interface.access_group_in if interface.access_group_in else u"not set"))
                                if interface.vrf is not None:
                                    self.write_line(u"  VPN Routing/Forwarding \"%s\"" % interface.vrf.name)
            elif u"route".startswith(args[1]):
                if u"static".startswith(args[2]):
                    routes = self.switch_configuration.static_routes
                    for route in routes:
                        self.write_line(u"S        {0} [x/y] via {1}".format(route.destination, route.next_hop))
                self.write_line(u"")
        elif u"version".startswith(args[0]):
            self.show_version()

    def do_copy(self, source_url, destination_url):
        dest_protocol, dest_file = destination_url.split(u":")
        self.write(u"Destination filename [%s]? " % strip_leading_slash(dest_file))
        self.continue_to(partial(self.continue_validate_copy, source_url))

    def continue_validate_copy(self, source_url, _):
        self.write_line(u"Accessing %s..." % source_url)
        try:
            url, filename = re.match(u'tftp://([^/]*)/(.*)', source_url).group(1, 2)
            SwitchTftpParser(self.switch_configuration).parse(url, filename, ConfigCommandProcessor)
            self.write_line(u"Done (or some official message...)")
        except Exception as e:
            self.logger.warning(u"tftp parsing went wrong : %s" % str(e))
            self.write_line(u"Error opening %s (Timed out)" % source_url)

    def do_terminal(self, *args):
        pass

    def do_write(self, *args):
        self.write_line(u"Building configuration...")
        self.switch_configuration.commit()
        self.write_line(u"OK")

    def do_exit(self):
        self.is_done = True

    def show_run(self):

        all_data = [
            u"version 12.1",
            u"!",
            u"hostname %s" % self.switch_configuration.name,
            u"!",
            u"!",
        ]
        for vlan in self.switch_configuration.vlans:
            all_data = all_data + build_running_vlan(vlan) + [u"!"]
        for interface in sorted(self.switch_configuration.ports, key=lambda e: (u"b" if isinstance(e, VlanPort) else u"a") + e.name):
            all_data = all_data + build_running_interface(interface) + [u"!"]
        if self.switch_configuration.static_routes:
            for route in self.switch_configuration.static_routes:
                all_data.append(build_static_routes(route))
            all_data.append(u"!")

        all_data += [u"end", u""]

        self.write_line(u"Building configuration...")
        self.write_line(u"")

        self.write_line(u"Current configuration : %i bytes" % (len(u"\n".join(all_data)) + 1))
        [self.write_line(l) for l in all_data]

    def show_version(self):
        self.write_line(version_text(
            hostname=self.switch_configuration.name,
            vlan_port_count=len(self.switch_configuration.get_vlan_ports()),
            port_count=len(self.switch_configuration.get_physical_ports()),
        ))

def strip_leading_slash(dest_file):
    return dest_file[1:]


def build_static_routes(route):
    return u"ip route {0} {1} {2}".format(route.destination, route.mask, route.next_hop)

def build_running_vlan(vlan):
    data = [
        u"vlan %s" % vlan.number,
    ]
    if vlan.name:
        data.append(u" name %s" % vlan.name)
    return data


def build_running_interface(port):
    data = [
        u"interface %s" % port.name
    ]
    if port.description:
        data.append(u" description %s" % port.description)
    if port.access_vlan and port.access_vlan != 1:
        data.append(u" switchport access vlan %s" % port.access_vlan)
    if port.trunk_encapsulation_mode is not None:
        data.append(u" switchport trunk encapsulation %s" % port.trunk_encapsulation_mode)
    if port.trunk_native_vlan is not None:
        data.append(u" switchport trunk native vlan %s" % port.trunk_native_vlan)
    if port.trunk_vlans is not None and len(port.trunk_vlans) < 4096 :
        data.append(u" switchport trunk allowed vlan %s" % to_vlan_ranges(port.trunk_vlans))
    if port.mode:
        data.append(u" switchport mode %s" % port.mode)
    if port.shutdown:
        data.append(u" shutdown")
    if port.aggregation_membership:
        data.append(u" channel-group %s mode active" % last_number(port.aggregation_membership))
    if port.vrf:
        data.append(u" ip vrf forwarding %s" % port.vrf.name)
    if isinstance(port, VlanPort):
        if len(port.ips) > 0:
            for ip in port.ips[1:]:
                data.append(u" ip address %s %s secondary" % (ip.ip, ip.netmask))
            data.append(u" ip address %s %s" % (port.ips[0].ip, port.ips[0].netmask))
        else:
            data.append(u" no ip address")
        if port.access_group_in:
            data.append(u" ip access-group %s in" % port.access_group_in)
        if port.access_group_out:
            data.append(u" ip access-group %s out" % port.access_group_out)
        if port.ip_redirect is False:
            data.append(u" no ip redirects")
        for vrrp in port.vrrps:
            group = vrrp.group_id
            if vrrp.ip_addresses is not None:
                if len(vrrp.ip_addresses) == 0:
                    data.append(u" standby {group} ip".format(group=group))
                else:
                    for i, ip_address in enumerate(vrrp.ip_addresses):
                        data.append(u" standby {group} ip {ip_address}{secondary}".format(
                                group=group, ip_address=ip_address, secondary=u' secondary' if i > 0 else u''))
            if vrrp.timers_hello is not None and vrrp.timers_hold is not None:
                data.append(u" standby {group} timers {hello_time} {hold_time}".format(group=group, hello_time=vrrp.timers_hello, hold_time=vrrp.timers_hold))
            if vrrp.priority is not None:
                data.append(u" standby {group} priority {priority}".format(group=group, priority=vrrp.priority))
            if vrrp.preempt is not None:
                if vrrp.preempt_delay_minimum is not None:
                    data.append(u" standby {group} preempt delay minimum {delay}".format(group=group, delay=vrrp.preempt_delay_minimum))
                else:
                    data.append(u" standby {group} preempt".format(group=group))
            if vrrp.authentication is not None:
                data.append(u" standby {group} authentication {authentication}".format(group=group, authentication=vrrp.authentication))
            for track, decrement in sorted(vrrp.track.items()):
                data.append(u" standby {group} track {track} decrement {decrement}".format(group=group, track=track, decrement=decrement))
        for ip_address in port.ip_helpers:
            data.append(u" ip helper-address {}".format(ip_address))
    return data


def vlan_name(vlan):
    return vlan.name or (u"default" if vlan.number == 1 else None)


def to_vlan_ranges(vlans):
    if len(vlans) == 0:
        return u"none"

    ranges = group_sequences(vlans, are_in_sequence=lambda a, b: a + 1 == b)

    return u",".join([to_range_string(r) for r in ranges])


def to_range_string(array_range):
    if len(array_range) < 3:
        return u",".join([str(n) for n in array_range])
    else:
        return u"%s-%s" % (array_range[0], array_range[-1])


def port_channel_number(port):
    return last_number(port.name)


def last_number(text):
    return int(re.match(r'(.*?)(\d+$)', text).groups()[1])


def short_name(port):
    if_type, if_number = re.match(r'([^0-9]*)([0-9].*$)', port.name).groups()
    return if_type[:2] + if_number


def version_text(**kwargs):
    return textwrap.dedent(u"""
        Cisco IOS Software, C3750 Software (C3750-IPSERVICESK9-M), Version 12.2(58)SE2, RELEASE SOFTWARE (fc1)
        Technical Support: http://www.cisco.com/techsupport
        Copyright (c) 1986-2011 by Cisco Systems, Inc.
        Compiled Thu 21-Jul-11 01:53 by prod_rel_team

        ROM: Bootstrap program is C3750 boot loader
        BOOTLDR: C3750 Boot Loader (C3750-HBOOT-M) Version 12.2(44)SE5, RELEASE SOFTWARE (fc1)

        {hostname} uptime is 1 year, 18 weeks, 5 days, 1 hour, 11 minutes
        System returned to ROM by power-on
        System image file is "flash:c3750-ipservicesk9-mz.122-58.SE2.bin"


        This product contains cryptographic features and is subject to United
        States and local country laws governing import, export, transfer and
        use. Delivery of Cisco cryptographic products does not imply
        third-party authority to import, export, distribute or use encryption.
        Importers, exporters, distributors and users are responsible for
        compliance with U.S. and local country laws. By using this product you
        agree to comply with applicable laws and regulations. If you are unable
        to comply with U.S. and local laws, return this product immediately.

        A summary of U.S. laws governing Cisco cryptographic products may be found at:
        http://www.cisco.com/wwl/export/crypto/tool/stqrg.html

        If you require further assistance please contact us by sending email to
        export@cisco.com.

        cisco WS-C3750G-24TS-1U (PowerPC405) processor (revision H0) with 131072K bytes of memory.
        Processor board ID FOC1530X2F7
        Last reset from power-on
        {vlan_port_count} Virtual Ethernet interfaces
        {port_count} Gigabit Ethernet interfaces
        The password-recovery mechanism is enabled.

        512K bytes of flash-simulated non-volatile configuration memory.
        Base ethernet MAC Address       : 00:00:00:00:00:00
        Motherboard assembly number     : 73-10219-09
        Power supply part number        : 341-0098-02
        Motherboard serial number       : FOC153019Z6
        Power supply serial number      : ALD153000BB
        Model revision number           : H0
        Motherboard revision number     : A0
        Model number                    : WS-C3750G-24TS-S1U
        System serial number            : FOC1530X2F7
        Top Assembly Part Number        : 800-26859-03
        Top Assembly Revision Number    : C0
        Version ID                      : V05
        CLEI Code Number                : COMB600BRA
        Hardware Board Revision Number  : 0x09


        Switch Ports Model              SW Version            SW Image
        ------ ----- -----              ----------            ----------
        *    1 {port_count: <5} WS-C3750G-24TS-1U  12.2(58)SE2           C3750-IPSERVICESK9-M


        Configuration register is 0xF
        """.format(**kwargs))[1:]
