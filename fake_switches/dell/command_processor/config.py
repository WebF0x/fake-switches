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

from fake_switches.cisco.command_processor.config import \
    ConfigCommandProcessor
from fake_switches.dell.command_processor.config_interface import \
    DellConfigInterfaceCommandProcessor
from fake_switches.dell.command_processor.config_vlan import \
    DellConfigureVlanCommandProcessor


class DellConfigCommandProcessor(ConfigCommandProcessor):
    config_interface_processor = DellConfigInterfaceCommandProcessor
    interface_separator = u' '

    def get_prompt(self):
        return u"\n" + self.switch_configuration.name + u"(config)#"

    def do_vlan(self, *args):
        if u"database".startswith(args[0]):
            self.move_to(DellConfigureVlanCommandProcessor)

    def do_interface(self, *args):
        if u'vlan'.startswith(args[0]):
            vlan_id = int(args[1])
            vlan = self.switch_configuration.get_vlan(vlan_id)
            if vlan is None:
                self.write_line(u"VLAN ID not found.")
                return
        self.write_line(u"")
        super(DellConfigCommandProcessor, self).do_interface(*args)

    def do_backdoor(self, *args):
        if u'remove'.startswith(args[0]) and u'port-channel'.startswith(args[1]):
            self.switch_configuration.remove_port(
                self.switch_configuration.get_port_by_partial_name(u" ".join(args[1:3])))

    def do_exit(self):
        self.write_line(u"")
        self.is_done = True

    def make_vlan_port(self, vlan_id, interface_name):
        return self.switch_configuration.new(u"VlanPort", vlan_id, interface_name)

    def make_aggregated_port(self, interface_name):
        return self.switch_configuration.new(u"AggregatedPort", interface_name)
