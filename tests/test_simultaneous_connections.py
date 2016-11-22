import unittest

from tests.util.global_reactor import brocade_privileged_password, cisco_privileged_password
from tests.util.global_reactor import brocade_switch_ip, brocade_switch_ssh_port, cisco_switch_ip, \
    cisco_switch_telnet_port
from tests.util.protocol_util import SshTester, TelnetTester


class RoutingEngineTest(unittest.TestCase):
    def test_2_ssh(self):
        tester1 = SshTester(u"ssh-1", brocade_switch_ip, brocade_switch_ssh_port, u'root', u'root')
        tester2 = SshTester(u"ssh-2", brocade_switch_ip, brocade_switch_ssh_port, u'root', u'root')

        tester1.connect()
        tester1.write(u"enable")
        tester1.read(u"Password:")
        tester1.write_invisible(brocade_privileged_password)
        tester1.read(u"SSH@my_switch#")
        tester1.write(u"skip-page-display")
        tester1.read(u"SSH@my_switch#")

        tester2.connect()

        tester1.write(u"skip-page-display")
        tester1.read(u"SSH@my_switch#")

        tester2.write(u"enable")
        tester2.read(u"Password:")
        tester2.write_invisible(brocade_privileged_password)
        tester2.read(u"SSH@my_switch#")
        tester2.write(u"configure terminal")
        tester2.read(u"SSH@my_switch(config)#")

        tester1.write(u"skip-page-display")
        tester1.read(u"SSH@my_switch#")

        tester2.write(u"exit")
        tester2.read(u"SSH@my_switch#")

        tester1.write(u"exit")
        tester1.read_eof()
        tester1.disconnect()

        tester2.write(u"exit")
        tester2.read_eof()
        tester2.disconnect()

    def test_2_telnet(self):
        tester1 = TelnetTester(u"telnet-1", cisco_switch_ip, cisco_switch_telnet_port, u'root', u'root')
        tester2 = TelnetTester(u"telnet-2", cisco_switch_ip, cisco_switch_telnet_port, u'root', u'root')

        tester1.connect()
        tester1.write(u"enable")
        tester1.read(u"Password: ")
        tester1.write_invisible(cisco_privileged_password)
        tester1.read(u"my_switch#")
        tester1.write(u"terminal length 0")
        tester1.read(u"my_switch#")

        tester2.connect()

        tester1.write(u"terminal length 0")
        tester1.read(u"my_switch#")

        tester2.write(u"enable")
        tester2.read(u"Password: ")
        tester2.write_invisible(cisco_privileged_password)
        tester2.read(u"my_switch#")
        tester2.write(u"configure terminal")
        tester2.readln(u"Enter configuration commands, one per line.  End with CNTL/Z.")
        tester2.read(u"my_switch(config)#")

        tester1.write(u"terminal length 0")
        tester1.read(u"my_switch#")

        tester2.write(u"exit")
        tester2.read(u"my_switch#")

        tester1.write(u"exit")
        tester1.read_eof()
        tester1.disconnect()

        tester2.write(u"exit")
        tester2.read_eof()
        tester2.disconnect()
