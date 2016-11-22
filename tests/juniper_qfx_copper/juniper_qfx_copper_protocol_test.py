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


from tests.juniper import BaseJuniper, vlan
from lxml import etree

from fake_switches.netconf import dict_2_etree, XML_TEXT, XML_ATTRIBUTES
from hamcrest import assert_that, has_length, equal_to, has_items, is_, is_not, contains_string
from ncclient import manager
from ncclient.operations import RPCError
from tests import contains_regex
from tests.juniper.assertion_tools import has_xpath
from tests.netconf.netconf_protocol_test import xml_equals_to

from tests.util.global_reactor import juniper_qfx_copper_switch_ip, \
    juniper_qfx_copper_switch_netconf_port


class JuniperQfxCopperProtocolTest(BaseJuniper):

    def create_client(self):
        return manager.connect(
            host=juniper_qfx_copper_switch_ip,
            port=juniper_qfx_copper_switch_netconf_port,
            username=u"root",
            password=u"root",
            hostkey_verify=False,
            device_params={u'name': u'junos'}
        )

    def test_capabilities(self):
        assert_that(self.nc.server_capabilities, has_items(
                u"urn:ietf:params:xml:ns:netconf:base:1.0",
                u"urn:ietf:params:xml:ns:netconf:capability:candidate:1.0",
                u"urn:ietf:params:xml:ns:netconf:capability:confirmed-commit:1.0",
                u"urn:ietf:params:xml:ns:netconf:capability:validate:1.0",
                u"urn:ietf:params:xml:ns:netconf:capability:url:1.0?protocol=http,ftp,file",
                u"http://xml.juniper.net/netconf/junos/1.0",
                u"http://xml.juniper.net/dmi/system/1.0",
        ))

    def test_get_running_config(self):
        result = self.nc.get_config(source=u"running")

        conf = result._NCElement__result.xml
        assert_that(conf, contains_regex(
                u'<configuration xmlns="http://xml.juniper.net/xnm/1.1/xnm" junos:commit-localtime="[^"]*" junos:commit-seconds="[^"]*" junos:commit-user="[^"]*"'))

        assert_that(result.xpath(u"data/configuration/*"), has_length(0))

    def test_only_configured_interfaces_are_returned(self):
        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"description": u"I see what you did there!"}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running")

        assert_that(result.xpath(u"data/configuration/interfaces/*"), has_length(1))

        self.cleanup(reset_interface(u"ge-0/0/3"))

    def test_lock_edit_candidate_add_vlan_and_commit(self):
        with self.nc.locked(target=u'candidate'):
            result = self.nc.edit_config(target=u'candidate', config=dict_2_etree({
                u"config": {
                    u"configuration": {
                        u"vlans": {
                            u"vlan": {
                                u"name": u"VLAN2999",
                            }
                        }
                    }
                }}))
            assert_that(result.xpath(u"//rpc-reply/ok"), has_length(1))

            result = self.nc.commit()
            assert_that(result.xpath(u"//rpc-reply/ok"), has_length(1))

        result = self.nc.get_config(source=u"running")

        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(1))

        self.edit({
            u"vlans": {
                u"vlan": {
                    XML_ATTRIBUTES: {u"operation": u"delete"},
                    u"name": u"VLAN2999"
                }
            }
        })

        self.nc.commit()

        result = self.nc.get_config(source=u"running")
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_locking_fails_if_changes_are_being_made(self):
        nc2 = self.create_client()

        try:
            self.nc.edit_config(target=u'candidate', config=dict_2_etree({
                u"config": {
                    u"configuration": {
                        u"vlans": {
                            u"vlan": [
                                {u"name": u"VLAN2999"},
                                {u"description": u"WHAAT"}
                            ]
                        }
                    }
                }}))

            with self.assertRaises(RPCError):
                with nc2.locked(target=u'candidate'):
                    self.fail(u'Should not be able to lock an edited configuration')

        finally:
            self.nc.discard_changes()
            nc2.close_session()

    def test_double_locking_with_two_sessions(self):
        nc2 = self.create_client()

        try:
            with self.nc.locked(target=u'candidate'):
                with self.assertRaises(RPCError):
                    with nc2.locked(target=u'candidate'):
                        self.fail(u"The second lock should not have worked.")

        finally:
            nc2.close_session()

    def test_bad_configuration_element(self):
        with self.assertRaises(RPCError):
            self.nc.edit_config(target=u'candidate', config=dict_2_etree({
                u"config": {
                    u"configuration": {
                        u"vbleh": u"shizzle"
                    }
                }}))

    def test_create_vlan(self):
        self.nc.edit_config(target=u'candidate', config=dict_2_etree({u"config": {u"configuration": {
            u"vlans": {
                u"vlan": [
                    {u"name": u"VLAN2999"},
                    {u"description": u"WHAAT"},
                    {u"vlan-id": u"2995"}
                ]
            }
        }}}))

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))

        assert_that(result.xpath(u"data/*"), has_length(1))
        assert_that(result.xpath(u"data/configuration/*"), has_length(1))
        assert_that(result.xpath(u"data/configuration/vlans/*"), has_length(1))
        assert_that(result.xpath(u"data/configuration/vlans/vlan/*"), has_length(3))

        vlan2995 = result.xpath(u"data/configuration/vlans/vlan")[0]

        assert_that(vlan2995.xpath(u"name")[0].text, equal_to(u"VLAN2999"))
        assert_that(vlan2995.xpath(u"description")[0].text, equal_to(u"WHAAT"))
        assert_that(vlan2995.xpath(u"vlan-id")[0].text, equal_to(u"2995"))

        self.cleanup(vlan(u"VLAN2999"))

    def test_vlan_configuration_merging(self):
        self.edit({
            u"vlans": {
                u"vlan": [
                    {u"name": u"VLAN2999"},
                    {u"vlan-id": u"2995"}
                ]}})
        self.edit({
            u"vlans": {
                u"vlan": [
                    {u"name": u"VLAN2999"},
                    {u"description": u"shizzle"}
                ]}})
        self.nc.commit()

        self.edit({
            u"vlans": {
                u"vlan": [
                    {u"name": u"VLAN2999"},
                    {u"vlan-id": u"2996"},
                    {u"description": {XML_ATTRIBUTES: {u"operation": u"delete"}}}
                ]}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))

        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(1))

        vlan2995 = result.xpath(u"data/configuration/vlans/vlan")[0]

        assert_that(vlan2995.xpath(u"name")[0].text, equal_to(u"VLAN2999"))
        assert_that(vlan2995.xpath(u"description"), has_length(0))
        assert_that(vlan2995.xpath(u"vlan-id")[0].text, equal_to(u"2996"))

        self.cleanup(vlan(u"VLAN2999"))

    def test_deletion_errors(self):
        self.edit({
            u"vlans": {
                u"vlan": [
                    {u"name": u"VLAN2999"},
                    {u"vlan-id": u"2995"}]}})

        with self.assertRaises(RPCError):
            self.edit({
                u"vlans": {
                    u"vlan": {
                        u"name": u"VLAN3000",
                        XML_ATTRIBUTES: {u"operation": u"delete"}}}})

        with self.assertRaises(RPCError):
            self.edit({
                u"vlans": {
                    u"vlan": [
                        {u"name": u"VLAN2999"},
                        {u"description": {XML_ATTRIBUTES: {u"operation": u"delete"}}}
                    ]}})

        self.nc.commit()

        with self.assertRaises(RPCError):
            self.edit({
                u"vlans": {
                    u"vlan": {
                        u"name": u"VLAN3000",
                        XML_ATTRIBUTES: {u"operation": u"delete"}}}})

        with self.assertRaises(RPCError):
            self.edit({
                u"vlans": {
                    u"vlan": [
                        {u"name": u"VLAN2999"},
                        {u"description": {XML_ATTRIBUTES: {u"operation": u"delete"}}}
                    ]}})

        self.cleanup(vlan(u"VLAN2999"))

    def test_access_mode(self):
        self.edit({
            u"vlans": {
                u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"access",
                                u"vlan": [
                                    {u"members": u"2995"},
                                ]}}}]}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]

        assert_that(int003.xpath(u"name")[0].text, equal_to(u"ge-0/0/3"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/*"), has_length(2))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/interface-mode")[0].text,
                    equal_to(u"access"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members"), has_length(1))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members")[0].text, equal_to(u"2995"))

        self.cleanup(vlan(u"VLAN2995"), reset_interface(u"ge-0/0/3"))

    def test_assigning_unknown_vlan_in_a_range_raises(self):
        self.edit({
            u"vlans": {
                u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": {u"members": u"2995-2996"}}}}]}]}})

        with self.assertRaises(RPCError):
            self.nc.commit()

    def test_assigning_unknown_vlan_raises(self):
        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"vlan": {u"members": u"2000"}}}}]}]}})

        with self.assertRaises(RPCError):
            self.nc.commit()

    def test_trunk_mode_does_not_allow_no_vlan_members(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
                {u"vlan": [
                    {u"name": u"VLAN2996"},
                    {u"vlan-id": u"2996"}]},
                {u"vlan": [
                    {u"name": u"VLAN2997"},
                    {u"vlan-id": u"2997"}]},
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"2996"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk"
                                }}}]}]}})
        with self.assertRaises(RPCError) as context:
            self.nc.commit()

            assert_that(etree.tostring(context.exception._raw.xpath(u'/*/*')[0]), xml_equals_to(
        u"""<?xml version="1.0" encoding="UTF-8"?><commit-results xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:junos="http://xml.juniper.net/junos/11.4R1/junos">
<rpc-error>
  <error-tag>operation-failed</error-tag>
  <error-message>
For trunk interface, please ensure either vlan members is configured or inner-vlan-id-list is configured
</error-message>
  <error-severity>error</error-severity>
  <error-path>
[edit interfaces ge-0/0/3 unit 0 family]
</error-path>
  <error-type>protocol</error-type>
  <error-info>
    <bad-element>ethernet-switching</bad-element>
  </error-info>
</rpc-error>
<rpc-error>
  <error-severity>error</error-severity>
  <error-tag>operation-failed</error-tag>
  <error-type>protocol</error-type>
  <error-message>
configuration check-out failed
</error-message>
</rpc-error>
</commit-results>"""))

        self.cleanup(vlan(u"VLAN2995"), vlan(u"VLAN2996"), vlan(u"VLAN2997"),
                         reset_interface(u"ge-0/0/3"))
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_trunk_mode(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
                {u"vlan": [
                    {u"name": u"VLAN2996"},
                    {u"vlan-id": u"2996"}]},
                {u"vlan": [
                    {u"name": u"VLAN2997"},
                    {u"vlan-id": u"2997"}]},
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"2996"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"2995"},
                                    {u"members": u"2997"},
                                ]}}}]}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]

        assert_that(int003.xpath(u"name")[0].text, equal_to(u"ge-0/0/3"))
        assert_that(int003.xpath(u"native-vlan-id")[0].text, equal_to(u"2996"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/*"), has_length(2))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/interface-mode")[0].text,
                    equal_to(u"trunk"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members"), has_length(2))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members")[0].text, equal_to(u"2995"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members")[1].text, equal_to(u"2997"))

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"vlan": [
                                    {u"members": {XML_TEXT: u"2995", XML_ATTRIBUTES: {u"operation": u"delete"}}},
                                ]}}}]}]}})
        self.nc.commit()
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))
        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members"), has_length(1))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members")[0].text, equal_to(u"2997"))

        self.cleanup(vlan(u"VLAN2995"), vlan(u"VLAN2996"), vlan(u"VLAN2997"),
                     reset_interface(u"ge-0/0/3"))
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_interface_trunk_native_vlan_merge(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
                {u"vlan": [
                    {u"name": u"VLAN2996"},
                    {u"vlan-id": u"2996"}]},
                {u"vlan": [
                    {u"name": u"VLAN2997"},
                    {u"vlan-id": u"2997"}]},
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"2995"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"2997"},
                                ]}}}]}]}})
        self.nc.commit()

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"2996"},
                    ]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int003.xpath(u"native-vlan-id")[0].text, equal_to(u"2996"))

        self.cleanup(vlan(u"VLAN2995"), vlan(u"VLAN2996"), vlan(u"VLAN2997"),
                     reset_interface(u"ge-0/0/3"))
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_interface_set_trunk_native_vlan_then_set_members_after(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
                {u"vlan": [
                    {u"name": u"VLAN2996"},
                    {u"vlan-id": u"2996"}]},
                {u"vlan": [
                    {u"name": u"VLAN2997"},
                    {u"vlan-id": u"2997"}]},
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"2996"}
                                ]
                            }}}]}]}})
        self.nc.commit()

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"2995"}
                    ]}})
        self.nc.commit()

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"vlan": [
                                    {u"members": u"2997"},
                                ]}}}]}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int003.xpath(u"native-vlan-id")[0].text, equal_to(u"2995"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members"), has_length(2))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members")[0].text, equal_to(u"2996"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members")[1].text, equal_to(u"2997"))

        self.cleanup(vlan(u"VLAN2995"), vlan(u"VLAN2996"), vlan(u"VLAN2997"),
                     reset_interface(u"ge-0/0/3"))
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_passing_from_trunk_mode_to_access_gets_rid_of_stuff_in_trunk_mode(self):

        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN1100"},
                    {u"vlan-id": u"1100"}]},
                {u"vlan": [
                    {u"name": u"VLAN1200"},
                    {u"vlan-id": u"1200"}]},
                {u"vlan": [
                    {u"name": u"VLAN1300"},
                    {u"vlan-id": u"1300"}]},
                {u"vlan": [
                    {u"name": u"VLAN1400"},
                    {u"vlan-id": u"1400"}]},
            ]})
        self.nc.commit()

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"1200"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"1100"},
                                    {u"members": u"1300"},
                                    {u"members": u"1400"},
                                ]}}}]}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int003.xpath(u"native-vlan-id")[0].text, equal_to(u"1200"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/interface-mode")[0].text, equal_to(u"trunk"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members"), has_length(3))

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"access"
                            }}}]}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int003.xpath(u"native-vlan-id"), has_length(0))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/interface-mode")[0].text, equal_to(u"access"))
        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members"), has_length(0))

        self.cleanup(vlan(u"VLAN1100"), vlan(u"VLAN1200"), vlan(u"VLAN1300"), vlan(u"VLAN1400"),
                     reset_interface(u"ge-0/0/3"))
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_display_interface_with_description_and_trunk_native_vlan(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
                {u"vlan": [
                    {u"name": u"VLAN2996"},
                    {u"vlan-id": u"2996"}]},
                {u"vlan": [
                    {u"name": u"VLAN2997"},
                    {u"vlan-id": u"2997"}]},
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"description": u"I see what you did there!"},
                    {u"native-vlan-id": u"2996"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"2995"},
                                    {u"members": u"2997"},
                                ]}}}]}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int003.xpath(u"name")[0].text, equal_to(u"ge-0/0/3"))
        assert_that(int003.xpath(u"native-vlan-id")[0].text, equal_to(u"2996"))
        assert_that(int003.xpath(u"description")[0].text, equal_to(u"I see what you did there!"))

        assert_that(int003.xpath(u"unit/family/ethernet-switching/vlan/members")), has_length(2)

        members = int003.xpath(u"unit/family/ethernet-switching/vlan/members")
        assert_that(members[0].text, equal_to(u"2995"))
        assert_that(members[1].text, equal_to(u"2997"))

        self.cleanup(vlan(u"VLAN2995"), vlan(u"VLAN2996"), vlan(u"VLAN2997"),
                     reset_interface(u"ge-0/0/3"))
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_assigning_unknown_native_vlan_raises(self):
        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"2000"}
                    ]}})

        with self.assertRaises(RPCError):
            self.nc.commit()

    def test_display_interface_trunk_native_vlan_and_no_ethernet_switching(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2996"},
                    {u"vlan-id": u"2996"}]}
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"native-vlan-id": u"2996"}
                    ]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/3"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int003 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int003.xpath(u"name")[0].text, equal_to(u"ge-0/0/3"))
        assert_that(int003.xpath(u"native-vlan-id")[0].text, equal_to(u"2996"))

        self.cleanup(vlan(u"VLAN2996"), reset_interface(u"ge-0/0/3"))
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"vlans": {}}}
        }))
        assert_that(result.xpath(u"data/configuration/vlans/vlan"), has_length(0))

    def test_set_spanning_tree_options(self):
        self.edit({
            u"protocols": {
                u"rstp": {
                    u"interface": [
                        {u"name": u"ge-0/0/3"},
                        {u"edge": u""},
                        {u"no-root-port": u""}]}}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"protocols": {u"rstp": {u"interface": {u"name": u"ge-0/0/3"}}}}}
        }))

        assert_that(result.xpath(u"data/configuration/protocols/rstp/interface"), has_length(1))

        interface = result.xpath(u"data/configuration/protocols/rstp/interface")[0]

        assert_that(interface, has_length(3))
        assert_that(interface.xpath(u"name")[0].text, equal_to(u"ge-0/0/3"))
        assert_that(interface.xpath(u"edge"), has_length(1))
        assert_that(interface.xpath(u"no-root-port"), has_length(1))

        self.edit({
            u"protocols": {
                u"rstp": {
                    u"interface": {
                        XML_ATTRIBUTES: {u"operation": u"delete"},
                        u"name": u"ge-0/0/3"}}}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"protocols": u""}}
        }))

        assert_that(result.xpath(u"data/configuration/protocols"), has_length(0))

    def test_deleting_spanning_tree_options(self):
        self.edit({
            u"protocols": {
                u"rstp": {
                    u"interface": [
                        {u"name": u"ge-0/0/3"},
                        {u"edge": u""},
                        {u"no-root-port": u""}]}}})

        self.nc.commit()

        self.edit({
            u"protocols": {
                u"rstp": {
                    u"interface": [
                        {u"name": u"ge-0/0/3"},
                        {u"edge": {XML_ATTRIBUTES: {u"operation": u"delete"}}},
                        {u"no-root-port": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]}}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"protocols": {u"rstp": {u"interface": {u"name": u"ge-0/0/3"}}}}}
        }))

        assert_that(result.xpath(u"data/configuration/protocols/rstp/interface"), has_length(0))

    def test_set_lldp(self):
        self.edit({
            u"protocols": {
                u"lldp": {
                    u"interface": [
                        {u"name": u"ge-0/0/3"},
                        {u"disable": u""}]}}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"protocols": {u"lldp": {u"interface": {u"name": u"ge-0/0/3"}}}}}
        }))

        assert_that(result.xpath(u"data/configuration/protocols/lldp/interface"), has_length(1))

        interface = result.xpath(u"data/configuration/protocols/lldp/interface")[0]

        assert_that(interface, has_length(2))
        assert_that(interface.xpath(u"name")[0].text, equal_to(u"ge-0/0/3"))
        assert_that(len(interface.xpath(u"disable")), equal_to(1))

        self.edit({
            u"protocols": {
                u"lldp": {
                    u"interface": [
                        {u"name": u"ge-0/0/3"},
                        {u"disable": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]}}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"protocols": {u"lldp": {u"interface": {u"name": u"ge-0/0/3"}}}}}
        }))
        assert_that(result.xpath(u"data/configuration/protocols/lldp/interface")[0], has_length(1))

        self.edit({
            u"protocols": {
                u"lldp": {
                    u"interface": {
                        XML_ATTRIBUTES: {u"operation": u"delete"},
                        u"name": u"ge-0/0/3"}}}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"protocols": u""}}
        }))

        assert_that(result.xpath(u"data/configuration/protocols"), has_length(0))

    def test_set_interface_description(self):
        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"description": u"Hey there beautiful"}]}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/2"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int002 = result.xpath(u"data/configuration/interfaces/interface")[0]

        assert_that(int002.xpath(u"name")[0].text, equal_to(u"ge-0/0/2"))
        assert_that(int002.xpath(u"description")[0].text, equal_to(u"Hey there beautiful"))

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"description": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/2"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(0))

    def test_set_interface_disabling(self):
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/2"}}}}}))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(0))

        self.edit({u"interfaces": {u"interface": [{u"name": u"ge-0/0/2"}, {u"disable": u""}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/2"}}}}}))

        int002 = result.xpath(u"data/configuration/interfaces/interface")[0]
        assert_that(int002.xpath(u"disable"), has_length(1))

        self.edit({u"interfaces": {
            u"interface": [{u"name": u"ge-0/0/2"}, {u"disable": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]}})
        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/2"}}}}}))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(0))

    def test_set_interface_trunk_native_vlan_id(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2996"},
                    {u"vlan-id": u"2996"}]}
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"native-vlan-id": u"2996"}]}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/2"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(1))

        int002 = result.xpath(u"data/configuration/interfaces/interface")[0]

        assert_that(int002.xpath(u"name")[0].text, equal_to(u"ge-0/0/2"))
        assert_that(int002.xpath(u"native-vlan-id")[0].text, equal_to(u"2996"))

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"native-vlan-id": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]}})

        self.nc.commit()

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ge-0/0/2"}}}}
        }))

        assert_that(result.xpath(u"data/configuration/interfaces/interface"), has_length(0))

        self.cleanup(vlan(u"VLAN2996"), reset_interface(u"ge-0/0/2"))

    def test_set_interface_raises_on_aggregated_out_of_range_port(self):
        with self.assertRaises(RPCError) as exc:
            self.edit({
                u"interfaces": {
                    u"interface": [
                        {u"name": u"ae9000"},
                        {u"aggregated-ether-options": {
                            u"link-speed": u"10g"}}
                    ]}})
        assert_that(str(exc.exception), contains_string(u"device value outside range 0..999 for '9000' in 'ae9000'"))

    def test_create_aggregated_port(self):
        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ae1"},
                    {u"description": u"This is a Greg hated"}]}})
        self.nc.commit()

        ae1 = self.get_interface(u"ae1")
        assert_that(ae1.xpath(u"*"), has_length(2))
        assert_that(ae1.xpath(u"description")[0].text, is_(u"This is a Greg hated"))

        self.edit({
            u"interfaces": {
                u"interface": [
                    {u"name": u"ae1"},
                    {u"description": {XML_ATTRIBUTES: {u"operation": u"delete"}}},
                    {u"aggregated-ether-options": {
                        u"link-speed": u"10g",
                        u"lacp": {
                            u"active": {},
                            u"periodic": u"slow"}}}]}})
        self.nc.commit()

        ae1 = self.get_interface(u"ae1")
        assert_that(ae1.xpath(u"*"), has_length(2))
        assert_that(ae1.xpath(u"aggregated-ether-options/*"), has_length(2))
        assert_that(ae1.xpath(u"aggregated-ether-options/link-speed")[0].text, is_(u"10g"))
        assert_that(ae1.xpath(u"aggregated-ether-options/lacp/*"), has_length(2))
        assert_that(ae1.xpath(u"aggregated-ether-options/lacp/active"), has_length(1))
        assert_that(ae1.xpath(u"aggregated-ether-options/lacp/periodic")[0].text, is_(u"slow"))

        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
                {u"vlan": [
                    {u"name": u"VLAN2997"},
                    {u"vlan-id": u"2997"}]},
            ],
            u"interfaces": {
                u"interface": [
                    {u"name": u"ae1"},
                    {u"aggregated-ether-options": {
                        u"link-speed": {XML_ATTRIBUTES: {u"operation": u"delete"}},
                        u"lacp": {
                            u"active": {XML_ATTRIBUTES: {u"operation": u"delete"}},
                            u"periodic": u"slow"}}},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"2995"},
                                    {u"members": u"2997"}]}}}]}]}})
        self.nc.commit()

        ae1 = self.get_interface(u"ae1")
        assert_that(ae1.xpath(u"*"), has_length(3))
        assert_that(ae1.xpath(u"aggregated-ether-options/*"), has_length(1))
        assert_that(ae1.xpath(u"aggregated-ether-options/lacp/periodic")[0].text, is_(u"slow"))
        assert_that(ae1.xpath(u"unit/family/ethernet-switching/vlan/members"), has_length(2))

        self.cleanup(vlan(u"VLAN2995"), vlan(u"VLAN2997"), reset_interface(u"ae1"))

        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": u"ae1"}}}}}))

        assert_that(result.xpath(u"configuration/interfaces"), has_length(0))

    def test_assign_port_to_aggregated_interface(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
            ],
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/1"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"access"}}}]}]},
                {u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"access"}}}]}]},
            ]})
        self.nc.commit()

        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
            ],
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ae1"},
                    {u"aggregated-ether-options": {
                        u"link-speed": u"10g",
                        u"lacp": {
                            u"active": {},
                            u"periodic": u"slow"}}},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"2995"}]}}}]}]},
                {u"interface": [
                    {u"name": u"ge-0/0/1"},
                    {u"ether-options": {
                        u"auto-negotiation": {},
                        u"speed": {u"ethernet-10g": {}},
                        u"ieee-802.3ad": {u"bundle": u"ae1"}}},
                    {u"unit": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]},
                {u"interface": [{XML_ATTRIBUTES: {u"operation": u"replace"}},
                               {u"name": u"ge-0/0/2"},
                               {u"ether-options": {
                                   u"speed": {u"ethernet-10g": {}},
                                   u"ieee-802.3ad": {u"bundle": u"ae1"}}}]},
            ]})
        self.nc.commit()

        ge001 = self.get_interface(u"ge-0/0/1")
        assert_that(ge001.xpath(u"*"), has_length(2))
        assert_that(ge001.xpath(u"unit"), has_length(0))
        assert_that(ge001.xpath(u"ether-options/*"), has_length(3))
        assert_that(ge001.xpath(u"ether-options/auto-negotiation"), has_length(1))
        assert_that(ge001.xpath(u"ether-options/speed/ethernet-10g"), has_length(1))
        assert_that(ge001.xpath(u"ether-options/ieee-802.3ad/bundle")[0].text, is_(u"ae1"))

        ge002 = self.get_interface(u"ge-0/0/2")
        assert_that(ge002.xpath(u"*"), has_length(2))
        assert_that(ge002.xpath(u"unit"), has_length(0))
        assert_that(ge002.xpath(u"ether-options/*"), has_length(2))
        assert_that(ge002.xpath(u"ether-options/speed/ethernet-10g"), has_length(1))
        assert_that(ge002.xpath(u"ether-options/ieee-802.3ad/bundle")[0].text, is_(u"ae1"))

        self.edit({
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/1"},
                    {u"ether-options": {
                        u"auto-negotiation": {XML_ATTRIBUTES: {u"operation": u"delete"}},
                        u"speed": u"10g",
                        u"ieee-802.3ad": {XML_ATTRIBUTES: {u"operation": u"delete"}}}}]},
                {u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"ether-options": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]},
            ]})
        self.nc.commit()

        ge001 = self.get_interface(u"ge-0/0/1")
        assert_that(ge001.xpath(u"unit"), has_length(0))
        assert_that(ge001.xpath(u"ether-options/*"), has_length(1))
        assert_that(ge001.xpath(u"ether-options/speed/ethernet-10g"), has_length(1))

        ge002 = self.get_interface(u"ge-0/0/2", )
        assert_that(ge002, is_(None))

        self.cleanup(vlan(u"VLAN2995"), reset_interface(u"ae1"), reset_interface(u"ge-0/0/1"), reset_interface(u"ge-0/0/2"))

    def test_auto_negotiation_and_no_auti_negotiation_are_mutually_exclusive(self):
        self.edit({
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/1"},
                    {u"ether-options": {
                        u"auto-negotiation": {}}}]}]})
        self.nc.commit()

        ge001 = self.get_interface(u"ge-0/0/1")
        assert_that(ge001.xpath(u"ether-options/auto-negotiation"), has_length(1))
        assert_that(ge001.xpath(u"ether-options/no-auto-negotiation"), has_length(0))

        self.edit({
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/1"},
                    {u"ether-options": {
                        u"no-auto-negotiation": {}}}]}]})
        self.nc.commit()

        ge001 = self.get_interface(u"ge-0/0/1")
        assert_that(ge001.xpath(u"ether-options/auto-negotiation"), has_length(0))
        assert_that(ge001.xpath(u"ether-options/no-auto-negotiation"), has_length(1))

        self.edit({
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/1"},
                    {u"ether-options": {
                        u"no-auto-negotiation": {XML_ATTRIBUTES: {u"operation": u"delete"}}}}]}]})
        self.nc.commit()

        assert_that(self.get_interface(u"ge-0/0/1"), is_(None))

    def test_posting_delete_on_both_auto_negotiation_flags_delete_and_raises(self):
        with self.assertRaises(RPCError) as expect:
            self.edit({
                u"interfaces": [
                    {u"interface": [
                        {u"name": u"ge-0/0/1"},
                        {u"ether-options": {
                            u"auto-negotiation": {XML_ATTRIBUTES: {u"operation": u"delete"}},
                            u"no-auto-negotiation": {XML_ATTRIBUTES: {u"operation": u"delete"}}}}]}]})

        assert_that(str(expect.exception), contains_string(u"warning: statement not found: no-auto-negotiation"))
        assert_that(str(expect.exception), contains_string(u"warning: statement not found: auto-negotiation"))

        with self.assertRaises(RPCError) as expect:
            self.edit({
                u"interfaces": [
                    {u"interface": [
                        {u"name": u"ge-0/0/1"},
                        {u"ether-options": {
                            u"auto-negotiation": {},
                            u"no-auto-negotiation": {}}}]}]})

        assert_that(str(expect.exception), contains_string(u"syntax error"))

        self.edit({
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/1"},
                    {u"ether-options": {
                        u"auto-negotiation": {}}}]}]})
        self.nc.commit()

        with self.assertRaises(RPCError) as expect:
            self.edit({
                u"interfaces": [
                    {u"interface": [
                        {u"name": u"ge-0/0/1"},
                        {u"ether-options": {
                            u"auto-negotiation": {XML_ATTRIBUTES: {u"operation": u"delete"}},
                            u"no-auto-negotiation": {XML_ATTRIBUTES: {u"operation": u"delete"}}}}]}]})
        self.nc.commit()

        assert_that(str(expect.exception), contains_string(u"warning: statement not found: no-auto-negotiation"))
        assert_that(str(expect.exception), is_not(contains_string(u"warning: statement not found: auto-negotiation")))

        e = self.get_interface(u"ge-0/0/1")
        assert_that(e, is_(None))

    def test_compare_configuration(self):

        result = self.nc.compare_configuration()

        output = result.xpath(u"configuration-information/configuration-output")[0]
        assert_that(output.text, is_not(u"There were some changes"))

        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN2995"},
                    {u"vlan-id": u"2995"}]},
            ]})

        result = self.nc.compare_configuration()

        output = result.xpath(u"configuration-information/configuration-output")[0]
        assert_that(output.text, is_(u"There were some changes"))

        self.nc.commit()

        result = self.nc.compare_configuration()

        output = result.xpath(u"configuration-information/configuration-output")[0]
        assert_that(output.text, is_not(u"There were some changes"))

        self.cleanup(vlan(u"VLAN2995"))

    def test_operational_request_get_interface_information_terse(self):
        self.edit({
            u"vlans": [
                {u"vlan": [
                    {u"name": u"VLAN1999"},
                    {u"vlan-id": u"1999"}]},
            ],
            u"interfaces": [
                {u"interface": [
                    {XML_ATTRIBUTES: {u"operation": u"delete"}},
                    {u"name": u"ge-0/0/1"}]},
                {u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"description": u"my crib"},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"access"}}}]}]},
                {u"interface": [
                    {u"name": u"ge-0/0/3"},
                    {u"description": u"bond member"},
                    {u"ether-options": {
                        u"ieee-802.3ad": {u"bundle": u"ae1"}}},
                    {u"unit": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]},
                {u"interface": [
                    {u"name": u"ge-0/0/4"},
                    {u"disable": u""}]},
                {u"interface": [
                    {u"name": u"ae3"},
                    {u"aggregated-ether-options": {
                        u"lacp": {
                            u"active": {},
                            u"periodic": u"slow"}}},
                    {u"unit": [
                        {u"name": u"0"},
                        {u"family": {
                            u"ethernet-switching": {
                                u"interface-mode": u"trunk",
                                u"vlan": [
                                    {u"members": u"1999"}]}}}]}]},
            ]})
        self.nc.commit()

        terse = self.nc.rpc(dict_2_etree({
            u"get-interface-information": {
                u"terse": {}}}))

        assert_that(terse.xpath(u"interface-information/physical-interface"), has_length(8)) # 4 physical 4 bonds

        deleted_interface = terse.xpath(u"interface-information/physical-interface/name[contains(text(),'\nge-0/0/1\n')]/..")[0]
        assert_that(deleted_interface.xpath(u"*"), has_length(4))
        assert_that(deleted_interface.xpath(u"admin-status")[0].text, is_(u"\nup\n"))
        assert_that(deleted_interface.xpath(u"oper-status")[0].text, is_(u"\ndown\n"))
        assert_that(deleted_interface.xpath(u"logical-interface/*"), has_length(4))
        assert_that(deleted_interface.xpath(u"logical-interface/name")[0].text, is_(u"\nge-0/0/1.16386\n"))
        assert_that(deleted_interface.xpath(u"logical-interface/admin-status")[0].text, is_(u"\nup\n"))
        assert_that(deleted_interface.xpath(u"logical-interface/oper-status")[0].text, is_(u"\ndown\n"))
        assert_that(deleted_interface.xpath(u"logical-interface/filter-information"), has_length(1))
        assert_that(deleted_interface.xpath(u"logical-interface/filter-information/*"), has_length(0))

        access_mode_interface = terse.xpath(u"interface-information/physical-interface/name[contains(text(),'\nge-0/0/2\n')]/..")[0]
        assert_that(access_mode_interface.xpath(u"*"), has_length(5))
        assert_that(access_mode_interface.xpath(u"admin-status")[0].text, is_(u"\nup\n"))
        assert_that(access_mode_interface.xpath(u"oper-status")[0].text, is_(u"\ndown\n"))
        assert_that(access_mode_interface.xpath(u"description")[0].text, is_(u"\nmy crib\n"))
        assert_that(access_mode_interface.xpath(u"logical-interface/*"), has_length(5))
        assert_that(access_mode_interface.xpath(u"logical-interface/name")[0].text, is_(u"\nge-0/0/2.0\n"))
        assert_that(access_mode_interface.xpath(u"logical-interface/admin-status")[0].text, is_(u"\nup\n"))
        assert_that(access_mode_interface.xpath(u"logical-interface/oper-status")[0].text, is_(u"\ndown\n"))
        assert_that(access_mode_interface.xpath(u"logical-interface/filter-information"), has_length(1))
        assert_that(access_mode_interface.xpath(u"logical-interface/filter-information/*"), has_length(0))
        assert_that(access_mode_interface.xpath(u"logical-interface/address-family/*"), has_length(1))
        assert_that(access_mode_interface.xpath(u"logical-interface/address-family/address-family-name")[0].text, is_(u"\neth-switch\n"))

        bond_member_interface = terse.xpath(u"interface-information/physical-interface/name[contains(text(),'\nge-0/0/3\n')]/..")[0]
        assert_that(bond_member_interface.xpath(u"*"), has_length(4))
        assert_that(bond_member_interface.xpath(u"admin-status")[0].text, is_(u"\nup\n"))
        assert_that(bond_member_interface.xpath(u"oper-status")[0].text, is_(u"\ndown\n"))
        assert_that(bond_member_interface.xpath(u"description")[0].text, is_(u"\nbond member\n"))

        disabled_interface = terse.xpath(u"interface-information/physical-interface/name[contains(text(),'\nge-0/0/4\n')]/..")[0]
        assert_that(disabled_interface.xpath(u"admin-status")[0].text, is_(u"\ndown\n"))

        inactive_bond = terse.xpath(u"interface-information/physical-interface/name[contains(text(),'\nae1\n')]/..")[0]
        assert_that(inactive_bond.xpath(u"*"), has_length(3))
        assert_that(inactive_bond.xpath(u"admin-status")[0].text, is_(u"\nup\n"))
        assert_that(inactive_bond.xpath(u"oper-status")[0].text, is_(u"\ndown\n"))

        active_bond = terse.xpath(u"interface-information/physical-interface/name[contains(text(),'\nae3\n')]/..")[0]
        assert_that(active_bond.xpath(u"*"), has_length(4))
        assert_that(active_bond.xpath(u"admin-status")[0].text, is_(u"\nup\n"))
        assert_that(active_bond.xpath(u"oper-status")[0].text, is_(u"\ndown\n"))
        assert_that(active_bond.xpath(u"logical-interface/*"), has_length(5))
        assert_that(active_bond.xpath(u"logical-interface/name")[0].text, is_(u"\nae3.0\n"))
        assert_that(active_bond.xpath(u"logical-interface/admin-status")[0].text, is_(u"\nup\n"))
        assert_that(active_bond.xpath(u"logical-interface/oper-status")[0].text, is_(u"\ndown\n"))
        assert_that(active_bond.xpath(u"logical-interface/filter-information"), has_length(1))
        assert_that(active_bond.xpath(u"logical-interface/filter-information/*"), has_length(0))
        assert_that(active_bond.xpath(u"logical-interface/address-family/*"), has_length(1))
        assert_that(active_bond.xpath(u"logical-interface/address-family/address-family-name")[0].text, is_(u"\neth-switch\n"))

        self.cleanup(vlan(u"VLAN1999"),
                     reset_interface(u"ae3"),
                     reset_interface(u"ge-0/0/1"),
                     reset_interface(u"ge-0/0/2"),
                     reset_interface(u"ge-0/0/3"),
                     reset_interface(u"ge-0/0/4"))

    def test_set_interface_raises_on_physical_interface_with_bad_trailing_input(self):
        with self.assertRaises(RPCError) as exc:
            self.edit({
                u"interfaces": {
                    u"interface": [
                        {u"name": u"ge-0/0/43foobar"},
                        {u"ether-options": {
                            u"auto-negotiation": {}}}
                    ]}})

        assert_that(str(exc.exception), contains_string(u"invalid trailing input 'foobar' in 'ge-0/0/43foobar'"))

    def test_set_interface_raises_for_physical_interface_for_out_of_range_port(self):
        with self.assertRaises(RPCError) as exc:
            self.edit({
                u"interfaces": {
                    u"interface": [
                        {u"name": u"ge-0/0/128"},
                        {u"ether-options": {
                            u"auto-negotiation": {}}}
                    ]}})

        assert_that(str(exc.exception), contains_string(u"port value outside range 1..127 for '128' in 'ge-0/0/128'"))

    def test_set_interface_raises_on_aggregated_invalid_interface_type(self):
        with self.assertRaises(RPCError) as exc:
            self.edit({
                u"interfaces": {
                    u"interface": [
                        {u"name": u"ae34foobar345"},
                        {u"ether-options": {
                            u"auto-negotiation": {}}}
                    ]}})

        assert_that(str(exc.exception), contains_string(u"invalid interface type in 'ae34foobar345'"))

    def test_set_interface_mtu(self):
        self.edit({
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"mtu": u"1000"}]},
                {u"interface": [
                    {u"name": u"ae2"},
                    {u"mtu": u"1500"}]},
            ]})

        self.nc.commit()

        assert_that(self._interface(u"ge-0/0/2"), has_xpath(u"mtu", equal_to(u"1000")))
        assert_that(self._interface(u"ae2"), has_xpath(u"mtu", equal_to(u"1500")))

        self.edit({
            u"interfaces": [
                {u"interface": [
                    {u"name": u"ge-0/0/2"},
                    {u"mtu": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]},
                {u"interface": [
                    {u"name": u"ae2"},
                    {u"mtu": {XML_ATTRIBUTES: {u"operation": u"delete"}}}]}
            ]})

        self.nc.commit()

        assert_that(self._interface(u"ge-0/0/2"), is_(None))
        assert_that(self._interface(u"ae2"), is_(None))

    def test_set_interface_mtu_error_messages(self):
        with self.assertRaises(RPCError) as exc:
            self.edit({
                u"interfaces": {
                    u"interface": [
                        {u"name": u"ge-0/0/2"},
                        {u"mtu": u"wat"}]}})

        assert_that(str(exc.exception), contains_string(u"Invalid numeric value: 'wat'"))

        with self.assertRaises(RPCError) as exc:
            self.edit({
                u"interfaces": {
                    u"interface": [
                        {u"name": u"ae2"},
                        {u"mtu": u"0"}]}})

        assert_that(str(exc.exception), contains_string(u"Value 0 is not within range (256..9216)"))

    def _interface(self, name):
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": name}}}}
        }))

        try:
            return result.xpath(u"data/configuration/interfaces/interface")[0]
        except IndexError:
            return None


def reset_interface(interface_name):
    def m(edit):
        edit({u"interfaces": {
            u"interface": [{XML_ATTRIBUTES: {u"operation": u"delete"}},
                          {u"name": interface_name}]}})

    return m
