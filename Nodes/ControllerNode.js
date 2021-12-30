'use strict';

const axios = require('axios');
const xml2js = require('xml2js');
let parser = new xml2js.Parser();

const nodeDefId = 'CONTROLLER';

module.exports = function(Polyglot) {
  const logger = Polyglot.logger;

  class Controller extends Polyglot.Node {
    constructor(polyInterface, primary, address, name) {
      super(nodeDefId, polyInterface, primary, address, name);

      this.commands = {
        DISCOVER: this.onDiscover,
      };

      this.drivers = {
        ST: { value: '0', uom: 2 },
        GV0: { value: '0', uom: 56},
        GV1: { value: '0', uom: 56},
        GV2: { value: '0', uom: 56},
        GV3: { value: '0', uom: 56},
        GV4: { value: '0', uom: 56},
        GV5: { value: '0', uom: 56},
        GV6: { value: '0', uom: 56},
        GV7: { value: '0', uom: 56},
        GV8: { value: '0', uom: 56},
      };

      this.isController = true;

    }

    async onDiscover() {
      logger.info('Discovering');

      let ip_address = this.polyInterface.getCustomParam('IP_Address');
      let isy_port = this.polyInterface.getCustomParam('ISY_Port');

      if (ip_address.length > 0 && isy_port.length > 0) {
        let nodes_url = "http://" + ip_address + ":" + isy_port + "/rest/nodes"
        let ivars_url = "http://" + ip_address + ":" + isy_port + "/rest/vars/get/1"
        let svars_url = "http://" + ip_address + ":" + isy_port + "/rest/vars/get/2"
        let progs_url = "http://" + ip_address + ":" + isy_port + "/rest/programs?subfolders=true"
  
        let nodes = await this.getInv(nodes_url)
        let ivars = await this.getInv(ivars_url);
        let svars = await this.getInv(svars_url);
        let progs = await this.getInv(progs_url);
  
        this.processNodes(nodes);
        this.processIvars(ivars);
        this.processSvars(svars);
        this.processPrograms(progs);
      } else {
        logger.info('Nodeserver Not Configured: Missing IP Address or Port');
      }
      
  
    }

    async getInv(URL) {
      let username = this.polyInterface.getCustomParam('Username');
      let password = this.polyInterface.getCustomParam('Password');
      
      if (username.length > 0 && password.length > 0) {
        try {
          const response = await axios.get(URL, {
            auth: {username: username, password: password}
          });
          return response.data;
        } catch (error) {
          logger.error('getInv() Error: ' + URL);
        }
      } else {
        logger.info('Nodeserver Not Configured: Missing Username or Password');
      }
      
    }

    processNodes(xml) {
      let node_count = 0;
      let group_count = 0;
      let folder_count = 0;
      let zwave_count = 0;
      let ns_count = 0;
      let insteon_count = 0;

      parser.parseString(xml, function(err, result) {
        if (err) {
          logger.error('processNode() Error');
        } else {
          node_count = result.nodes.node.length;
          group_count = result.nodes.group.length;
          if (result.nodes.folder) {
            folder_count = result.nodes.folder.length;
          }

          for (let i in result.nodes.node) {
            // logger.info(result.nodes.node[i].address);
            let n = result.nodes.node[i].address[0];
            if (n.match(/^ZW\d+\w+/)) {
              zwave_count++;
            } else if (n.match(/^n\d+\w+/)) {
              ns_count++;
            } else {
              insteon_count++
            }
          }
        }
      });

      let total_count = node_count + group_count + folder_count;
      this.setDriver('GV0', total_count, true);
      this.setDriver('GV1', group_count, true);
      this.setDriver('GV2', insteon_count, true);
      this.setDriver('GV3', zwave_count, true);
      this.setDriver('GV4', ns_count, true);
      this.setDriver('GV8', folder_count, true);

    }

    processIvars(xml) {
      let ivars_count = 0;

      parser.parseString(xml, function(err, result) {
        if (err) {
          logger.error('processIvars Error');
        } else {
          ivars_count = result.vars.var.length;
        }
      });

      this.setDriver('GV5', ivars_count, true);
    }

    processSvars(xml) {
      let svars_count = 0;

      parser.parseString(xml, function(err, result) {
        if (err) {
          logger.error('processSvars Error');
        } else {
          svars_count = result.vars.var.length;
        }
      });

      this.setDriver('GV6', svars_count, true);
    }

    processPrograms(xml) {
      let progs_count = 0;

      parser.parseString(xml, function(err, result) {
        if (err) {
          logger.error('processPrograms Error');
        } else {
          progs_count = result.programs.program.length;
        }
      });

      this.setDriver('GV7', progs_count, true);
    }

  };

  Controller.nodeDefId = nodeDefId;

  return Controller;
};