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
        self.isy_port = '80'
        self.debug_enable = 'False'
        self.poly.onConfig(self.process_config)

    def start(self):
        if 'debug_enable' in self.polyConfig['customParams']:
            self.debug_enable = self.polyConfig['customParams']['debug_enable']
        self.heartbeat(0)
        if self.check_params():
            self.discover()

    def shortPoll(self):
        self.discover()

    def longPoll(self):
        self.heartbeat()

    def query(self, command=None):
        self.discover()

    def get_request(self, url):
        try:
            r = requests.get(url, auth=HTTPBasicAuth(self.user, self.password))
            if r.status_code == requests.codes.ok:
                if self.debug_enable == 'True' or self.debug_enable == 'true':
                    print(r.content)

                return r.content
            else:
                LOGGER.error("ISY-Inventory.get_request:  " + r.content)
                return None

        except requests.exceptions.RequestException as e:
            LOGGER.error("Error: " + str(e))

    def discover(self, *args, **kwargs):
        if self.isy_ip is not None:
            nodes_url = "http://" + self.isy_ip + ":" + self.isy_port + "/rest/nodes"
            ivars_url = "http://" + self.isy_ip + ":" + self.isy_port + "/rest/vars/get/1"
            svars_url = "http://" + self.isy_ip + ":" + self.isy_port + "/rest/vars/get/2"
            progs_url = "http://" + self.isy_ip + ":" + self.isy_port + "/rest/programs?subfolders=true"

            node_count = 0
            scene_count = 0
            insteon_count = 0
            zwave_count = 0
            ns_count = 0
            ivars_count = 0
            svars_count = 0
            progs_count = 0

            node_resp = self.get_request(nodes_url)
            if node_resp is not None:
                node_root = ET.fromstring(node_resp)
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

            ivars_resp = self.get_request(ivars_url)
            if ivars_resp is not None:
                ivars_root = ET.fromstring(ivars_resp)
                for ivar in ivars_root.iter('var'):
                    ivars_count += 1

            svars_resp = self.get_request(svars_url)
            if svars_resp is not None:
                svars_root = ET.fromstring(svars_resp)
                for svar in svars_root.iter('var'):
                    svars_count += 1

            progs_resp = self.get_request(progs_url)
            if progs_resp is not None:
                progs_root = ET.fromstring(progs_resp)
                for prog in progs_root.iter('program'):
                    progs_count += 1

            if self.debug_enable == 'True' or self.debug_enable == 'true':
                LOGGER.info("Total Nodes: " + str(node_count))
                LOGGER.info("Scene Count: " + str(scene_count))
                LOGGER.info("Insteon Count: " + str(insteon_count))
                LOGGER.info("Z-Wave Count: " + str(zwave_count))
                LOGGER.info("NodeServers Count: " + str(ns_count))
                LOGGER.info("Int Variables Count: " + str(ivars_count))
                LOGGER.info("State Variables Count: " + str(svars_count))
                LOGGER.info("Programs Count: " + str(progs_count))

            self.setDriver('ST', node_count, force=True)
            self.setDriver('GPV', 1)
            self.setDriver('GV0', scene_count, force=True)
            self.setDriver('GV1', insteon_count, force=True)
            self.setDriver('GV2', zwave_count, force=True)
            self.setDriver('GV3', ns_count, force=True)
            self.setDriver('GV4', ivars_count, force=True)
            self.setDriver('GV5', svars_count, force=True)
            self.setDriver('GV6', progs_count, force=True)
        else:
            LOGGER.info("ISY IP is not configured")

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
        default_isy_port = "80"

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

        if 'isy_port' in self.polyConfig['customParams']:
            self.isy_port = self.polyConfig['customParams']['isy_port']
        else:
            self.isy_port = default_isy_port
            LOGGER.error(
                'check_params: ISY Port not defined in customParams, please add it. Using {}'.format(self_isy_port))
            st = False

        if 'debug_enable' in self.polyConfig['customParams']:
            self.debug_enable = self.polyConfig['customParams']['debug_enable']

        # Make sure they are in the params
        self.addCustomParam({'password': self.password, 'user': self.user,
                             'isy_ip': self.isy_ip, 'is_port': self.isy_port, 'debug_enable': self.debug_enable})

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
