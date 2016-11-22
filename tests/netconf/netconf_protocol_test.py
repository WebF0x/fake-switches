import logging
import unittest

from hamcrest.core.base_matcher import BaseMatcher
import re
from hamcrest import assert_that, ends_with, equal_to, has_length, has_key
from mock import Mock
from ncclient.xml_ import to_ele, to_xml
from fake_switches.netconf import RUNNING, dict_2_etree
from fake_switches.netconf.capabilities import filter_content
from fake_switches.netconf.netconf_protocol import NetconfProtocol


class NetconfProtocolTest(unittest.TestCase):
    def setUp(self):
        self.netconf = NetconfProtocol(logger=logging.getLogger())
        self.netconf.transport = Mock()

    def test_says_hello_upon_connection_and_receive_an_hello(self):
        self.netconf.connectionMade()

        self.assert_xml_response(u"""
            <hello>
              <session-id>1</session-id>
              <capabilities>
                <capability>urn:ietf:params:xml:ns:netconf:base:1.0</capability>
              </capabilities>
            </hello>
            """)

    def test_close_session_support(self):
        self.netconf.connectionMade()
        self.say_hello()

        self.netconf.dataReceived(u'<nc:rpc xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="12345">\n')
        self.netconf.dataReceived(u'  <nc:close-session/>\n')
        self.netconf.dataReceived(u'</nc:rpc>\n')
        self.netconf.dataReceived(u']]>]]>\n')

        self.assert_xml_response(u"""
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="12345">
                <ok/>
            </rpc-reply>
            """)
        self.netconf.transport.loseConnection.assert_called_with()

    def test_get_config_support(self):
        self.netconf.datastore.set_data(RUNNING, {u"configuration": {u"stuff": u"is cool!"}})
        self.netconf.connectionMade()
        self.say_hello()

        self.netconf.dataReceived(u"""
            <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="67890">
              <get-config>
                <source><running /></source>
              </get-config>
            </rpc>
            ]]>]]>""")

        self.assert_xml_response(u"""
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="67890">
                <data>
                  <configuration>
                    <stuff>is cool!</stuff>
                  </configuration>
                </data>
            </rpc-reply>
            """)

        assert_that(self.netconf.transport.loseConnection.called, equal_to(False))

    def test_request_with_namespace(self):
        self.netconf.datastore.set_data(RUNNING, {u"configuration": {u"stuff": u"is cool!"}})
        self.netconf.connectionMade()
        self.say_hello()

        self.netconf.dataReceived(u"""
            <nc:rpc xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="67890">
              <nc:get-config>
                <nc:source><nc:running/></nc:source>
              </nc:get-config>
            </nc:rpc>
            ]]>]]>""")

        self.assert_xml_response(u"""
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="67890">
                <data>
                  <configuration>
                    <stuff>is cool!</stuff>
                  </configuration>
                </data>
            </rpc-reply>
            """)

    def test_edit_config(self):
        self.netconf.datastore.set_data(RUNNING, {u"configuration": {u"stuff": {u"substuff": u"is cool!"}}})
        self.netconf.connectionMade()
        self.say_hello()

        data = u"""<?xml version="1.0" encoding="UTF-8"?>
            <nc:rpc xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="urn:uuid:346c9f18-c420-11e4-8e4c-fa163ecd3b0a">
                <nc:edit-config>
                    <nc:target>
                        <nc:candidate/>
                    </nc:target>
                    <nc:config>
                        <nc:configuration><nc:stuff><substuff>is hot!</substuff></nc:stuff></nc:configuration>
                    </nc:config>
                </nc:edit-config>
            </nc:rpc>]]>]]>"""
        self.netconf.dataReceived(data)

        self.assert_xml_response(u"""
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="urn:uuid:346c9f18-c420-11e4-8e4c-fa163ecd3b0a">
                <ok/>
            </rpc-reply>
            """)

    def test_reply_includes_additional_namespaces(self):
        self.netconf.additionnal_namespaces = {
            u"junos": u"http://xml.juniper.net/junos/11.4R1/junos",
            u"nc": u"urn:ietf:params:xml:ns:netconf:base:1.0",
        }
        self.netconf.connectionMade()
        self.say_hello()

        self.netconf.dataReceived(u"""
            <nc:rpc xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="67890">
              <nc:get-config>
                <nc:source><nc:running/></nc:source>
              </nc:get-config>
            </nc:rpc>
            ]]>]]>""")

        assert_that(self.netconf.transport.write.call_args[0][0].decode(), xml_equals_to(u"""
            <rpc-reply xmlns:junos="http://xml.juniper.net/junos/11.4R1/junos" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="67890">
              <data/>
            </rpc-reply>
            ]]>]]>
            """
                                                                                ))

    def test_filtering(self):
        content = dict_2_etree({
            u"data": {
                u"configuration": [
                    {u"shizzle": {
                        u"whizzle": {}
                    }},
                    {u"shizzle": {
                        u"whizzle": {
                            u"howdy": {}
                        },
                        u"not-whizzle": {
                            u"not-howdy": {}
                        }
                    }},
                    {u"zizzle": {
                        u"nothing": {}
                    }},
                    {u"outzzle": {
                        u"nothing": {}
                    }}
                ]
            }
        })

        content_filter = dict_2_etree({
            u"filter": {
                u"configuration": {
                    u"shizzle": {u"whizzle": {}},
                    u"zizzle": {},
                }
            }
        })

        filter_content(content, content_filter)

        assert_that(content.xpath(u"//data/configuration/shizzle"), has_length(2))
        assert_that(content.xpath(u"//data/configuration/shizzle/*"), has_length(2))
        assert_that(content.xpath(u"//data/configuration/shizzle/whizzle/howdy"), has_length(1))
        assert_that(content.xpath(u"//data/configuration/zizzle"), has_length(1))
        assert_that(content.xpath(u"//data/configuration/outzzle"), has_length(0))

    def test_filtering_with_a_value(self):
        content = dict_2_etree({
            u"data": {
                u"configuration": [
                    {u"element": {
                        u"element-key": u"MY-KEY",
                        u"attribute": {u"sub-attribute": {}}
                    }},
                    {u"element": {
                        u"element-key": u"MY-OTHER-KEY",
                        u"other-attribute": {u"sub-attribute": {}}
                    }},
                ]
            }
        })

        content_filter = dict_2_etree({
            u"filter": {
                u"configuration": {
                    u"element": {
                        u"element-key": u"MY-KEY"
                    },
                }
            }
        })

        filter_content(content, content_filter)

        assert_that(content.xpath(u"//data/configuration/element"), has_length(1))
        assert_that(content.xpath(u"//data/configuration/element/*"), has_length(2))
        assert_that(content.xpath(u"//data/configuration/element/attribute/*"), has_length(1))

    def say_hello(self):
        self.netconf.dataReceived(
            u'<hello xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"><capabilities><capability>urn:ietf:params:xml:ns:netconf:base:1.0</capability></capabilities></hello>]]>]]>')

    def assert_xml_response(self, expected):
        data = self.netconf.transport.write.call_args[0][0].decode()
        assert_that(data, ends_with(u"]]>]]>\n"))
        data = data.replace(u"]]>]]>", u"")
        assert_that(data, xml_equals_to(expected))


def xml_equals_to(string):
    return XmlEqualsToMatcher(string)


class XmlEqualsToMatcher(BaseMatcher):
    def __init__(self, expected):
        self.expected = to_ele(expected)
        self.last_error = None

    def _matches(self, other):
        otherxml = other if not isinstance(other, str) else to_ele(other)
        try:
            self.compare_nodes(self.expected, otherxml)
            return True
        except AssertionError as e:
            self.last_error = e
            return False

    def describe_to(self, description):
        description.append_text(to_xml(self.expected, pretty_print=True))

    def describe_mismatch(self, item, mismatch_description):
        itemxml = item if not isinstance(item, str) else to_ele(item)
        mismatch_description.append_text(u"WAS : \n" + to_xml(itemxml, pretty_print=True) + u"\n\n")
        mismatch_description.append_text(u"IN WHICH : " + str(self.last_error))

    def compare_nodes(self, actual_node, node):
        assert_that(unqualify(node.tag), equal_to(unqualify(actual_node.tag)))
        assert_that(node, has_length(len(actual_node)))
        if node.text is not None:
            if node.text.strip() == u"":
                assert_that(actual_node.text is None or actual_node.text.strip() == u"")
            else:
                assert_that(node.text.strip(), equal_to(actual_node.text.strip()))
        for name, value in node.attrib.items():
            assert_that(actual_node.attrib, has_key(name))
            assert_that(actual_node.attrib[name], equal_to(value))
        assert_that(actual_node.nsmap, equal_to(node.nsmap))
        self.compare_children(node, actual_node)

    def compare_children(self, expected, actual):
        assert_that(actual, has_length(len(expected)))
        tested_nodes = []
        for node in expected:
            actual_node = get_children_by_unqualified_tag(unqualify(node.tag), actual, excluding=tested_nodes)
            self.compare_nodes(actual_node, node)
            tested_nodes.append(actual_node)


def unqualify(tag):
    return re.sub(u"\{[^\}]*\}", u"", tag)


def get_children_by_unqualified_tag(tag, node, excluding):
    for child in node:
        if child not in excluding and unqualify(child.tag) == tag:
            return child

    raise AssertionError(u"Missing element {} in {}".format(tag, to_xml(node, pretty_print=True)))
