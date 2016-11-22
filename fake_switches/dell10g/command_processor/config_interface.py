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

from fake_switches.dell.command_processor.config_interface import DellConfigInterfaceCommandProcessor, parse_vlan_list
from fake_switches.switch_configuration import AggregatedPort


class Dell10GConfigInterfaceCommandProcessor(DellConfigInterfaceCommandProcessor):

    def __init__(self, switch_configuration, terminal_controller, logger,
                 piping_processor, port):
        super(DellConfigInterfaceCommandProcessor, self).__init__(
            switch_configuration, terminal_controller, logger, piping_processor,
            port)
        self.description_strip_chars = u"\"'"

    def get_prompt(self):
        short_name = self.port.name.split(u' ')[1]
        return u"{}(config-if-{}{})#".format(
            self.switch_configuration.name,
            u"Po" if isinstance(self.port, AggregatedPort) else u"Te",
            short_name)

    def configure_lldp_port(self, args, target_value):
        if u"transmit".startswith(args[0]):
            self.port.lldp_transmit = target_value
        elif u"receive".startswith(args[0]):
            self.port.lldp_receive = target_value
        elif u"med".startswith(args[0]):
            if len(args) == 1:
                self.port.lldp_med = target_value
            elif u"transmit-tlv".startswith(args[1]):
                if u"capabilities".startswith(args[2]):
                    self.port.lldp_med_transmit_capabilities = target_value
                elif u"network-policy".startswith(args[2]):
                    self.port.lldp_med_transmit_network_policy = target_value


    def do_switchport(self, *args):
        if u"access".startswith(args[0]) and u"vlan".startswith(args[1]):
            self.set_access_vlan(int(args[2]))
        elif u"mode".startswith(args[0]):
            self.set_switchport_mode(args[1])
        elif (u"general".startswith(args[0]) or u"trunk".startswith(args[0])) and u"allowed".startswith(args[1]):
            if u"vlan".startswith(args[2]) and args[0] == u"general":
                if len(args) > 5:
                    self.write_line(u"                                                                 ^")
                    self.write_line(u"% Invalid input detected at '^' marker.")
                else:
                    operation = args[3]
                    vlan_range = args[4]
                    self.update_trunk_vlans(operation, vlan_range)
                    return
            elif u"vlan".startswith(args[2]) and args[0] == u"trunk":
                if len(args) > 5:
                    self.write_line(u"                                                                 ^")
                    self.write_line(u"% Invalid input detected at '^' marker.")
                else:
                    if args[0:4] == (u"trunk", u"allowed", u"vlan", u"add"):
                        if self.port.trunk_vlans is not None:
                            self.port.trunk_vlans = sorted(list(set(self.port.trunk_vlans + parse_vlan_list(args[4]))))
                    elif args[0:4] == (u"trunk", u"allowed", u"vlan", u"remove"):
                        if self.port.trunk_vlans is None:
                            self.port.trunk_vlans = list(range(1, 4097))
                        for v in parse_vlan_list(args[4]):
                            if v in self.port.trunk_vlans:
                                self.port.trunk_vlans.remove(v)
                        if len(self.port.trunk_vlans) == 0:
                            self.port.trunk_vlans = None
                    elif args[0:4] == (u"trunk", u"allowed", u"vlan", u"none"):
                        self.port.trunk_vlans = []
                    elif args[0:4] == (u"trunk", u"allowed", u"vlan", u"all"):
                        self.port.trunk_vlans = None
                    elif args[0:3] == (u"trunk", u"allowed", u"vlan"):
                        self.port.trunk_vlans = parse_vlan_list(args[3])
                    elif args[0:3] == (u"trunk", u"native", u"vlan"):
                        self.port.trunk_native_vlan = int(args[3])
        elif u"general".startswith(args[0]) and u"pvid".startswith(args[1]):
            self.set_trunk_native_vlan(int(args[2]))

        self.write_line(u"")

    def do_no_switchport(self, *args):
        if u"mode".startswith(args[0]):
            self.set_switchport_mode(u"access")
        elif u"access".startswith(args[0]):
            if u"vlan".startswith(args[1]):
                self.print_vlan_warning()
                self.port.access_vlan = None
        elif args[0] in (u"trunk", u"general") and args[1:3] == (u"allowed", u"vlan"):
            self.port.trunk_vlans = None
        elif u"general".startswith(args[0]):
            if u"pvid".startswith(args[1]):
                self.port.trunk_native_vlan = None

        self.write_line(u"")

    def do_mtu(self, *args):
        self.write_line(u"                                                     ^")
        self.write_line(u"% Invalid input detected at '^' marker.")
        self.write_line(u"")

    def do_no_mtu(self, *args):
        self.write_line(u"                                                     ^")
        self.write_line(u"% Invalid input detected at '^' marker.")
        self.write_line(u"")

    def set_switchport_mode(self, mode):
        if mode not in (u"access", u"trunk", u"general"):
            self.write_line(u"                                         ^")
            self.write_line(u"% Invalid input detected at '^' marker.")
        else:
            self.port.mode = mode

    def set_trunk_native_vlan(self, native_vlan):
        vlan = self.switch_configuration.get_vlan(native_vlan)
        if vlan is None:
            self.write_line(u"Could not configure pvid.")
        else:
            self.port.trunk_native_vlan = vlan.number

    def print_vlan_warning(self):
        pass
