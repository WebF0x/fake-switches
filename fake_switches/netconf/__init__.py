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

import re
from lxml import etree

RUNNING = u"running"
CANDIDATE = u"candidate"
NS_BASE_1_0 = u"urn:ietf:params:xml:ns:netconf:base:1.0"

XML_ATTRIBUTES = u"__xml_attributes__"
XML_TEXT = u"__xml_text__"
XML_NS = u"__xml_ns__"

class SimpleDatastore(object):
    def __init__(self):
        self.data = {
            RUNNING: {},
            CANDIDATE: {}
        }

    def set_data(self, source, data):
        self.data[source] = data

    def to_etree(self, source):
        return dict_2_etree({u"data": self.data[source]})

    def edit(self, target, config):
        pass

    def lock(self):
        pass

    def unlock(self):
        pass

class Response(object):
    def __init__(self, elements, require_disconnect=False):
        self.elements = elements if isinstance(elements, list) else [elements]
        self.require_disconnect = require_disconnect


def dict_2_etree(source_dict):

    def append(root, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k == XML_ATTRIBUTES:
                    for a, val in sorted(v.items()):
                        root.set(a, val)
                elif k == XML_TEXT:
                    root.text = v
                else:
                    if XML_NS in v:
                        sub = etree.SubElement(root, k, xmlns=v[XML_NS])
                        del v[XML_NS]
                    else:
                        sub = etree.SubElement(root, k)
                    append(sub, v)
        elif isinstance(data, list):
            for e in data:
                append(root, e)
        else:
            root.text = data

    root_element = list(source_dict.keys())[0]
    root_etree = etree.Element(root_element)
    append(root_etree, source_dict[root_element])
    return root_etree

def resolve_source_name(xml_tag):
    if xml_tag.endswith(RUNNING):
        return RUNNING
    elif xml_tag.endswith(CANDIDATE):
        return CANDIDATE
    else:
        raise Exception(u"What is this source : %s" % xml_tag)

def first(node):
    return node[0] if node else None


def normalize_operation_name(element):
    tag = unqualify(element)
    return re.sub(u"-", u"_", tag)


def unqualify(lxml_element):
    return re.sub(u"\{.*\}", u"", lxml_element.tag)


class NetconfError(Exception):
    def __init__(self, msg, severity=u"error", err_type=None, tag=None, info=None, path=None):
        super(NetconfError, self).__init__(msg)
        self.severity = severity
        self.type = err_type
        self.tag = tag
        self.info = info
        self.path = path


class MultipleNetconfErrors(Exception):
    def __init__(self, errors):
        self.errors = errors


class AlreadyLocked(NetconfError):
    def __init__(self):
        super(AlreadyLocked, self).__init__(u"Configuration database is already open")


class CannotLockUncleanCandidate(NetconfError):
    def __init__(self):
        super(CannotLockUncleanCandidate, self).__init__(u"configuration database modified")


class UnknownVlan(NetconfError):
    def __init__(self, vlan, interface, unit):
        super(UnknownVlan, self).__init__(u"No vlan matches vlan tag %s for interface %s.%s" % (vlan, interface, unit))


class AggregatePortOutOfRange(NetconfError):
    def __init__(self, port, interface, max_range=999):
        super(AggregatePortOutOfRange, self).__init__(u"device value outside range 0..{} for '{}' in '{}'".format(max_range, port, interface))


class PhysicalPortOutOfRange(NetconfError):
    def __init__(self, port, interface):
        super(PhysicalPortOutOfRange, self).__init__(u"port value outside range 1..127 for '{}' in '{}'".format(port, interface))


class InvalidTrailingInput(NetconfError):
    def __init__(self, port, interface):
        super(InvalidTrailingInput, self).__init__(u"invalid trailing input '{}' in '{}'".format(port, interface))


class InvalidInterfaceType(NetconfError):
    def __init__(self, interface):
        super(InvalidInterfaceType, self).__init__(u"invalid interface type in '{}'".format(interface))


class InvalidNumericValue(NetconfError):
    def __init__(self, value):
        super(InvalidNumericValue, self).__init__(u"Invalid numeric value: '{}'".format(value))


class InvalidMTUValue(NetconfError):
    def __init__(self, value):
        super(InvalidMTUValue, self).__init__(u"Value {} is not within range (256..9216)".format(value))


class OperationNotSupported(NetconfError):
    def __init__(self, name):
        super(OperationNotSupported, self).__init__(
            u"Operation %s not found amongst current capabilities" % name,
            severity=u"error",
            err_type=u"protocol",
            tag=u"operation-not-supported"
        )


class TrunkShouldHaveVlanMembers(NetconfError):
    def __init__(self, interface):
        super(TrunkShouldHaveVlanMembers, self).__init__(msg=u'\nFor trunk interface, please ensure either vlan members is configured or inner-vlan-id-list is configured\n',
                                                         severity=u'error',
                                                         err_type=u'protocol',
                                                         tag=u'operation-failed',
                                                         info={u'bad-element': u'ethernet-switching'},
                                                         path=u'\n[edit interfaces {} unit 0 family]\n'.format(interface))

class ConfigurationCheckOutFailed(NetconfError):
    def __init__(self):
        super(ConfigurationCheckOutFailed, self).__init__(msg=u'\nconfiguration check-out failed\n',
                                                          severity=u'error',
                                                          err_type=u'protocol',
                                                          tag=u'operation-failed',
                                                          info=None)


class FailingCommitResults(Exception):
    def __init__(self, netconf_errors):
        self.netconf_errors = netconf_errors


def xml_equals(actual_node, node):
    if unqualify(node) != unqualify(actual_node): return False
    if len(node) != len(actual_node): return False
    if node.text is not None:
        if actual_node.text is None: return False
        elif node.text.strip() != actual_node.text.strip(): return False
    elif actual_node.text is not None: return False
    for name, value in node.attrib.items():
        if name not in actual_node.attrib: return False
        if actual_node.attrib[name] != value: return False
    if actual_node.nsmap != node.nsmap: return False
    return _compare_children(node, actual_node)

def _compare_children(expected, actual):
    for i, node in enumerate(expected):
        actual_node = actual[i]
        if not xml_equals(actual_node, node):
            return False

    return True
