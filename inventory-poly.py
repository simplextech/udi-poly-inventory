#!/usr/bin/env python

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import time
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
import re

LOGGER = polyinterface.LOGGER


class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'ISY Inventory'
        self.user = None
        self.password = None
        self.isy_ip = None
        self.poly.onConfig(self.process_config)

    def start(self):
        self.heartbeat(0)
        if self.check_params():
            self.discover()

    def shortPoll(self):
        self.discover()

    def longPoll(self):
        self.heartbeat()

    def query(self, command=None):
        self.discover()

    def discover(self, *args, **kwargs):
        nodes_url = "http://" + self.isy_ip + "/rest/nodes"
        ivars_url = "http://" + self.isy_ip + "/rest/vars/get/1"
        svars_url = "http://" + self.isy_ip + "/rest/vars/get/2"
        prog_url = "http://" + self.isy_ip + "/rest/programs?subfolders=true" \
                                             ""
        node_resp = requests.get(nodes_url, auth=HTTPBasicAuth(self.user, self.password))
        node_root = ET.fromstring(node_resp.content)

        ivars_resp = requests.get(ivars_url, auth=HTTPBasicAuth(self.user, self.password))
        ivars_root = ET.fromstring(ivars_resp.content)

        svars_resp = requests.get(svars_url, auth=HTTPBasicAuth(self.user, self.password))
        svars_root = ET.fromstring(svars_resp.content)

        prog_resp = requests.get(prog_url, auth=HTTPBasicAuth(self.user, self.password))
        prog_root = ET.fromstring(prog_resp.content)

        node_count = 0
        scene_count = 0
        insteon_count = 0
        zwave_count = 0
        ns_count = 0
        ivars_count = 0
        svars_count = 0
        prog_count = 0

        for node in node_root.iter('node'):
            node_count += 1

        for node in node_root.iter('group'):
            scene_count += 1

        for node in node_root.iter('node'):
            addr = node.find('address').text
            if re.match(r'^ZW\d+\w+', addr):
                zwave_count += 1
            elif re.match(r'^n0\d+\w+', addr):
                ns_count += 1
            else:
                insteon_count += 1

        for ivar in ivars_root.iter('var'):
            ivars_count += 1

        for svar in svars_root.iter('var'):
            svars_count += 1

        for prog in prog_root.iter('program'):
            prog_count += 1

        LOGGER.info("Total Nodes: " + str(node_count))
        LOGGER.info("Scene Count: " + str(scene_count))
        LOGGER.info("Insteon Count: " + str(insteon_count))
        LOGGER.info("Z-Wave Count: " + str(zwave_count))
        LOGGER.info("NodeServers Count: " + str(ns_count))
        LOGGER.info("Int Variables Count: " + str(ivars_count))
        LOGGER.info("State Variables Count: " + str(svars_count))
        LOGGER.info("Programs Count: " + str(prog_count))

        self.setDriver('ST', node_count)
        self.setDriver('GPV', 1)
        self.setDriver('GV0', scene_count)
        self.setDriver('GV1', insteon_count)
        self.setDriver('GV2', zwave_count)
        self.setDriver('GV3', ns_count)
        self.setDriver('GV4', ivars_count)
        self.setDriver('GV5', svars_count)
        self.setDriver('GV6', prog_count)

    def delete(self):
        LOGGER.info('Removing ISY Inventory')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def process_config(self, config):
        # this seems to get called twice for every change, why?
        # What does config represent?
        LOGGER.info("process_config: Enter config={}".format(config));
        LOGGER.info("process_config: Exit");

    def heartbeat(self, init=False):
        # LOGGER.debug('heartbeat: init={}'.format(init))
        if init is not False:
            self.hb = init
        # LOGGER.debug('heartbeat: hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON", 2)
            self.hb = 1
        else:
            self.reportCmd("DOF", 2)
            self.hb = 0

    def check_params(self):
        st = True
        self.remove_notices_all()
        default_user = "YourUserName"
        default_password = "YourPassword"
        default_isy_ip = "127.0.0.1"

        if 'user' in self.polyConfig['customParams']:
            self.user = self.polyConfig['customParams']['user']
        else:
            self.user = default_user
            LOGGER.error('check_params: user not defined in customParams, please add it.  Using {}'.format(self.user))
            st = False

        if 'password' in self.polyConfig['customParams']:
            self.password = self.polyConfig['customParams']['password']
        else:
            self.password = default_password
            LOGGER.error(
                'check_params: password not defined in customParams, please add it.  Using {}'.format(self.password))
            st = False

        if 'isy_ip' in self.polyConfig['customParams']:
            self.isy_ip = self.polyConfig['customParams']['isy_ip']
        else:
            self.isy_ip = default_isy_ip
            LOGGER.error(
                'check_params: ISY IP not defined in customParams, please add it.  Using {}'.format(self.isy_ip))
            st = False

        # Make sure they are in the params
        self.addCustomParam({'password': self.password, 'user': self.user, 'isy_ip': self.isy_ip})

        # Add a notice if they need to change the user/password from the default.
        if self.user == default_user or self.password == default_password or self.isy_ip == default_isy_ip:
            self.addNotice('Please set proper user, password and ISY IP '
                           'in configuration page, and restart this nodeserver')
            st = False

        if st:
            return True
        else:
            return False

    def remove_notices_all(self):
        LOGGER.info('remove_notices_all: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self, command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    id = 'controller'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
    }
    drivers = [
        {'driver': 'GPV', 'value': 1, 'uom': 2},
        {'driver': 'ST', 'value': 0, 'uom': 56},
        {'driver': 'GV0', 'value': 0, 'uom': 56},
        {'driver': 'GV1', 'value': 0, 'uom': 56},
        {'driver': 'GV2', 'value': 0, 'uom': 56},
        {'driver': 'GV3', 'value': 0, 'uom': 56},
        {'driver': 'GV4', 'value': 0, 'uom': 56},
        {'driver': 'GV5', 'value': 0, 'uom': 56},
        {'driver': 'GV6', 'value': 0, 'uom': 56},
   ]


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('ISY-Inventory')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        LOGGER.warning("Received interrupt or exit...")
        polyglot.stop()
    except Exception as err:
        LOGGER.error('Excption: {0}'.format(err), exc_info=True)
    sys.exit(0)
