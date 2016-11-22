import unittest

from fake_switches.netconf import dict_2_etree, XML_ATTRIBUTES
from hamcrest import assert_that, has_length


class BaseJuniper(unittest.TestCase):

    def setUp(self):
        self.nc = self.create_client()

    def tearDown(self):
        assert_that(self.nc.get_config(source=u"running").xpath(u"data/configuration/*"), has_length(0))
        try:
            self.nc.discard_changes()
        finally:
            self.nc.close_session()

    def edit(self, config):
        result = self.nc.edit_config(target=u"candidate", config=dict_2_etree({
            u"config": {
                u"configuration": config
            }
        }))
        assert_that(result.xpath(u"//rpc-reply/ok"), has_length(1))

    def cleanup(self, *args):
        for clean_it in args:
            clean_it(self.edit)
        self.nc.commit()

    def get_interface(self, name):
        result = self.nc.get_config(source=u"running", filter=dict_2_etree({u"filter": {
            u"configuration": {u"interfaces": {u"interface": {u"name": name}}}}}))
        if len(result.xpath(u"data/configuration")) == 0:
            return None
        return result.xpath(u"data/configuration/interfaces/interface")[0]


def vlan(vlan_name):
    def m(edit):
        edit({u"vlans": {
            u"vlan": {u"name": vlan_name, XML_ATTRIBUTES: {u"operation": u"delete"}}
        }})

    return m

