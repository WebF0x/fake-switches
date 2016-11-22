import unittest

from flexmock import flexmock_teardown
from tests.util.global_reactor import cisco_switch_ip, \
    cisco_auto_enabled_switch_ssh_port, cisco_auto_enabled_switch_telnet_port
from tests.util.protocol_util import SshTester, TelnetTester, with_protocol


class TestCiscoAutoEnabledSwitchProtocol(unittest.TestCase):
    __test__ = False

    def setUp(self):
        self.protocol = self.create_client()

    def tearDown(self):
        flexmock_teardown()

    @with_protocol
    def test_enable_command_requires_a_password(self, t):
        t.write(u"enable")
        t.read(u"my_switch#")
        t.write(u"terminal length 0")
        t.read(u"my_switch#")
        t.write(u"terminal width 0")
        t.read(u"my_switch#")
        t.write(u"configure terminal")
        t.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        t.read(u"my_switch(config)#")
        t.write(u"exit")
        t.read(u"my_switch#")

    def create_client(self):
        return TelnetTester(u"telnet", cisco_switch_ip, cisco_auto_enabled_switch_telnet_port, u'root', u'root')
        raise NotImplementedError()


class TestCiscoSwitchProtocolSSH(TestCiscoAutoEnabledSwitchProtocol):
    __test__ = True

    def create_client(self):
        #raise NotImplementedError()
        return SshTester(u"ssh", cisco_switch_ip, cisco_auto_enabled_switch_ssh_port, u'root', u'root')


class TestCiscoSwitchProtocolTelnet(TestCiscoAutoEnabledSwitchProtocol):
    __test__ = True

    def create_client(self):
        #raise NotImplementedError()
        return TelnetTester(u"telnet", cisco_switch_ip, cisco_auto_enabled_switch_telnet_port, u'root', u'root')
