'use strict';

trapUncaughExceptions();

const fs = require('fs');
const markdown = require('markdown').markdown;
const AsyncLock = require('async-lock');

const Polyglot = require('polyinterface-v3');

const logger = Polyglot.logger;
const lock = new AsyncLock({ timeout: 500 });

const ControllerNode = require('./Nodes/ControllerNode.js')(Polyglot);

const defaultParams = {
  Username: '',
  Password: '',
  IP_Address: '',
  ISY_Port: '80'
};

logger.info('Starting Node Server');

// classes that we will be using.
const poly = new Polyglot.Interface([ControllerNode]);

poly.on('mqttConnected', function() {
  logger.info('MQTT Connection started');
});

poly.on('config', function(config) {
  const nodesCount = Object.keys(config.nodes).length;
  logger.info('Config received has %d nodes', nodesCount);

  if (config.isInitialConfig) {
    poly.removeNoticesAll();
    const md = fs.readFileSync('./configdoc.md');
    poly.setCustomParamsDoc(markdown.toHTML(md.toString()));

    if (!nodesCount) {
      try {
        logger.info('Auto-creating controller');
        callAsync(autoCreateController());
      } catch (err) {
        logger.error('Error while auto-creating controller node:', err);
      }
    }
  }
});

poly.on('customParams', function(params) {
  initializeCustomParams(params)
});

poly.on('poll', function(longPoll) {
  callAsync(doPoll(longPoll));
});

poly.on('stop', async function() {
  logger.info('Graceful stop');
  poly.stop();
});

poly.on('delete', function() {
  logger.info('Nodeserver is being deleted');

  // We can do some cleanup, then stop.
  poly.stop();
});

poly.on('mqttEnd', function() {
  logger.info('MQTT connection ended.'); // May be graceful or not.
});

poly.on('messageReceived', function(message) {
  // Only display messages other than config
  if (!message['config']) {
    logger.debug('Message Received: %o', message);
  }
});

poly.on('messageSent', function(message) {
  logger.debug('Message Sent: %o', message);
});

async function doPoll(longPoll) {
  // Prevents polling logic reentry if an existing poll is underway
  const nodes = poly.getNodes();

  try {
    await lock.acquire('poll', function() {
      logger.info('%s', longPoll ? 'Long poll' : 'Short poll');
      if (longPoll) {
        logger.info('Long Poll: Inventory');
      } else {
        logger.info('Short Poll: Invetory');
        Object.keys(nodes).forEach(function (address) {
          if ('onDiscover' in nodes[address]) {
            nodes[address].onDiscover();
          }
        });
      }
    });
  } catch (err) {
    logger.error('Error while polling: %s', err.message);
  }
}

async function autoCreateController() {
  try {
    await poly.addNode(
      new ControllerNode(poly, 'controller', 'controller', 'ISY-Inventory')
    );
  } catch (err) {
    logger.error('Error creating controller node');
  }

  poly.addNoticeTemp('newController', 'Controller node initialized', 5);
}

function initializeCustomParams(currentParams) {
  const defaultParamKeys = Object.keys(defaultParams);
  const currentParamKeys = Object.keys(currentParams);

  // Get orphan keys from either currentParams or defaultParams
  const differentKeys = defaultParamKeys.concat(currentParamKeys)
  .filter(function(key) {
    return !(key in defaultParams) || !(key in currentParams);
  });

  if (differentKeys.length) {
    let customParams = {};

    // Only keeps params that exists in defaultParams
    // Sets the params to the existing value, or default value.
    defaultParamKeys.forEach(function(key) {
      customParams[key] = currentParams[key] ?
        currentParams[key] : defaultParams[key];
    });

    poly.saveCustomParams(customParams);
  }
}

function callAsync(promise) {
  (async function() {
    try {
      await promise;
    } catch (err) {
      logger.error('Error with async function: %s %s', err.message, err.stack);
    }
  })();
}

function trapUncaughExceptions() {
  // If we get an uncaugthException...
  process.on('uncaughtException', function(err) {
    logger.error(`uncaughtException REPORT THIS!: ${err.stack}`);
  });
}

poly.start();
