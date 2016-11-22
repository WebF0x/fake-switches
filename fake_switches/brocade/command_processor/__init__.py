from fake_switches.switch_configuration import split_port_name


def explain_missing_port(port_name):
    name, number = split_port_name(port_name)
    try:
        slot, port = number.split(u'/', 1)

        if int(port) > 64:
            return [u'Invalid input -> {}'.format(number),
                    u'Type ? for a list']
        else:
            if int(slot) > 1:
                return [u'Error - interface {} is not an ETHERNET interface'.format(number)]
            else:
                return [u"Error - invalid interface {}".format(number)]
    except ValueError:
        return [u'Invalid input -> {0}  {1}'.format(name.replace(u'ethe ', u''), number),
                u'Type ? for a list']
