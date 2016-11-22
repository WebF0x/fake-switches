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

from fake_switches.cisco.command_processor.config_interface import \
    ConfigInterfaceCommandProcessor


class DellConfigInterfaceCommandProcessor(ConfigInterfaceCommandProcessor):

    def __init__(self, switch_configuration, terminal_controller, logger,
                 piping_processor, port):
        super(DellConfigInterfaceCommandProcessor, self).__init__(
            switch_configuration, terminal_controller, logger, piping_processor,
            port)
        self.description_strip_chars = u"\"'"

    def get_prompt(self):
        if self.port.name.startswith(u"ethernet"):
            short_name = self.port.name.split(u' ')[1]
        elif self.port.name.startswith(u"port-channel"):
            short_name = u"ch{}".format(self.port.name.split(u' ')[1])
        else:
            short_name = self.port.name.replace(u' ', u'').lower()
        return self.switch_configuration.name + u"(config-if-%s)#" % short_name

    def do_description(self, *args):
        super(DellConfigInterfaceCommandProcessor, self).do_description(*args)
        self.write_line(u"")

    def do_no_description(self, *_):
        super(DellConfigInterfaceCommandProcessor, self).do_no_description(*_)
        self.write_line(u"")

    def do_no_shutdown(self, *_):
        super(DellConfigInterfaceCommandProcessor, self).do_no_shutdown(*_)
        self.write_line(u"")

    def do_shutdown(self, *_):
        super(DellConfigInterfaceCommandProcessor, self).do_shutdown(*_)
        self.write_line(u"")

    def do_spanning_tree(self, *args):
        if u"disable".startswith(args[0]):
            self.port.spanning_tree = False
        if u"portfast".startswith(args[0]):
            self.port.spanning_tree_portfast = True
        self.write_line(u"")

    def do_no_spanning_tree(self, *args):
        if u"disable".startswith(args[0]):
            self.port.spanning_tree = None
        if u"portfast".startswith(args[0]):
            self.port.spanning_tree_portfast = None
        self.write_line(u"")

    def do_lldp(self, *args):
        self.configure_lldp_port(args, target_value=True)
        self.write_line(u"")

    def do_no_lldp(self, *args):
        self.configure_lldp_port(args, target_value=False)
        self.write_line(u"")

    def configure_lldp_port(self, args, target_value):
        if u"transmit".startswith(args[0]):
            self.port.lldp_transmit = target_value
        elif u"receive".startswith(args[0]):
            self.port.lldp_receive = target_value
        elif u"med".startswith(args[0]) and u"transmit-tlv".startswith(args[1]):
            if u"capabilities".startswith(args[2]):
                self.port.lldp_med_transmit_capabilities = target_value
            elif u"network-policy".startswith(args[2]):
                self.port.lldp_med_transmit_network_policy = target_value

    def do_name(self, *args):
        if len(args) == 0:
            self.write_line(u"")
            self.write_line(u"Command not found / Incomplete command. Use ? to list commands.")
        elif len(args) > 1:
            self.write_line(u"                                     ^")
            self.write_line(u"% Invalid input detected at '^' marker.")
        elif len(args[0]) > 32:
            self.write_line(u"Name must be 32 characters or less.")
        else:
            vlan = self.switch_configuration.get_vlan(self.port.vlan_id)
            vlan.name = args[0]

        self.write_line(u"")

    def do_switchport(self, *args):
        if u"access".startswith(args[0]) and u"vlan".startswith(args[1]):
            self.set_access_vlan(int(args[2]))
        elif u"mode".startswith(args[0]):
            self.set_switchport_mode(args[1])
        elif (u"general".startswith(args[0]) or u"trunk".startswith(args[0])) and u"allowed".startswith(args[1]):
            if u"general".startswith(args[0]) and self.port.mode != u"general":
                self.write_line(u"Interface not in General Mode.")
            elif u"trunk".startswith(args[0]) and self.port.mode != u"trunk":
                self.write_line(u"Interface not in Trunk Mode.")
            elif u"vlan".startswith(args[2]):
                if len(args) > 5:
                    self.write_line(u"                                                                 ^")
                    self.write_line(u"% Invalid input detected at '^' marker.")
                else:
                    operation = args[3]
                    vlan_range = args[4]
                    self.update_trunk_vlans(operation, vlan_range)
                    return
        elif u"general".startswith(args[0]) and u"pvid".startswith(args[1]):
            self.set_trunk_native_vlan(int(args[2]))

        self.write_line(u"")

    def do_no_switchport(self, *args):
        if u"access".startswith(args[0]):
            if u"vlan".startswith(args[1]):
                self.print_vlan_warning()
                self.port.access_vlan = None
        elif u"general".startswith(args[0]):
            if u"pvid".startswith(args[1]):
                self.port.trunk_native_vlan = None
        elif u"mode".startswith(args[0]):
            self.port.trunk_vlans = None
            self.port.mode = None
            self.port.trunk_native_vlan = None
            self.port.trunk_vlans = None

        self.write_line(u"")

    def do_mtu(self, *args):
        if len(args) > 1:
            self.write_line(u"                                  ^")
            self.write_line(u"% Invalid input detected at '^' marker.")
            self.write_line(u"")
            return

        try:
            value = int(args[0])
        except ValueError:
            self.write_line(u"                            ^")
            self.write_line(u"Invalid input. Please specify an integer in the range 1518 to 9216.")
            return

        if not (1518 <= value <= 9216):
            self.write_line(u"                            ^")
            self.write_line(u"Value is out of range. The valid range is 1518 to 9216.")
            return

        self.port.mtu = value
        self.write_line(u"")

    def do_no_mtu(self, *args):
        self.port.mtu = None
        self.write_line(u"")

    def set_switchport_mode(self, mode):
        if mode not in (u"access", u"trunk", u"general"):
            self.write_line(u"                                         ^")
            self.write_line(u"% Invalid input detected at '^' marker.")
        else:
            if self.port.mode != mode:
                self.port.mode = mode
                self.port.access_vlan = None
                self.port.trunk_native_vlan = None
                self.port.trunk_vlans = None

    def set_access_vlan(self, vlan_id):
        self.print_vlan_warning()
        vlan = self.switch_configuration.get_vlan(int(vlan_id))
        if vlan:
            self.port.access_vlan = vlan.number
        else:
            self.write_line(u"")
            self.write_line(u"VLAN ID not found.")

    def set_trunk_native_vlan(self, native_vlan):
        if self.port.mode != u"general":
            self.write_line(u"")
            self.write_line(u"Port is not general port.")
        else:
            vlan = self.switch_configuration.get_vlan(native_vlan)
            if vlan is None:
                self.write_line(u"Could not configure pvid.")
            else:
                self.port.trunk_native_vlan = vlan.number

    def update_trunk_vlans(self, operation, vlan_range):
        try:
            vlans = parse_vlan_list(vlan_range)
        except ValueError:
            self.write_line(u"VLAN range - separate non-consecutive IDs with ',' and no spaces.  Use '-' for range.")
            self.write_line(u"")
            return

        self.print_vlan_warning()

        vlans_not_found = [v for v in vlans if self.switch_configuration.get_vlan(v) is None]
        if len(vlans_not_found) > 0:
            self.write_line(u"")
            self.write_line(u"          Failure Information")
            self.write_line(u"---------------------------------------")
            self.write_line(u"   VLANs failed to be configured : {}".format(len(vlans_not_found)))
            self.write_line(u"---------------------------------------")
            self.write_line(u"   VLAN             Error")
            self.write_line(u"---------------------------------------")
            for vlan in vlans_not_found:
                self.write_line(u"VLAN      {: >4} ERROR: This VLAN does not exist.".format(vlan))
            return

        if u"add".startswith(operation):
            if self.port.trunk_vlans is None:
                self.port.trunk_vlans = []
            self.port.trunk_vlans = list(set(self.port.trunk_vlans + vlans))
        if u"remove".startswith(operation):
            for v in vlans:
                if v in self.port.trunk_vlans:
                    self.port.trunk_vlans.remove(v)
            if len(self.port.trunk_vlans) == 0:
                self.port.trunk_vlans = None

        self.write_line(u"")

    def print_vlan_warning(self):
        self.write_line(u"Warning: The use of large numbers of VLANs or interfaces may cause significant")
        self.write_line(u"delays in applying the configuration.")
        self.write_line(u"")


def parse_vlan_list(param):
    ranges = param.split(u",")
    vlans = []
    for r in ranges:
        if u"-" in r:
            start, stop = r.split(u"-")
            if stop < start:
                raise ValueError
            vlans += [v for v in range(int(start), int(stop) + 1)]
        else:
            vlans.append(int(r))

    return vlans
