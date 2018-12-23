"""ConBee adapter for Mozilla IoT Gateway."""

import json
import logging
import sys
import time

from gateway_addon import Adapter

from conbee_config import Config
from conbee_device import ConBeeLight, ConBeeMotionSensor, ConBeeTemperatureSensor
from deconz_rest_api import DeconzRestApi


class ConBeeAdapter(Adapter):
    """Adapter for Zigbee devices accessed via Conbee."""

    def __init__(self, verbose=False):
        """
        verbose -- enable verbose logging
        """
        self.name = self.__class__.__name__
        Adapter.__init__(self,
                         'zigbee-conbee-adapter',
                         'zigbee-conbee-adapter',
                         verbose=verbose)
        self._config = Config(self.package_name)
        self.conbee_url = self._config.conbee_url()
        self.rest = DeconzRestApi(self.conbee_url)
        logging.info('init ConBeeAdapter')
        self.start_pairing(0)

    def start_pairing(self, timeout):
        """  Start pairing process. """
        logging.info('START Pairing Lights')
        try:
            json_dict = self.rest.get_lights()
            for k, v in json_dict.items():
                uid = v['uniqueid']
                # Check if already added
                if self.get_device(uid) != None:
                    logging.info('uniqueid Light device %s already exist. Not added again', uid);
                    continue
                for kk, vv in json_dict[k].items():
                    logging.info('Ligths: %s %s: %s', k, kk, vv)
                logging.info('Add light %s', uid)
                device = ConBeeLight(self, uid, str(k),json_dict[k])
                self.handle_device_added(device)
            logging.info('START Pairing Sensors')
            json_dict = self.rest.get_sensors()
            for k, v in json_dict.items():
                uid = v['uniqueid']
                if self.get_device(uid) != None:
                    logging.info('uniqueid Sensor device %s already exist. Not added again', uid);
                    continue
                for kk, vv in json_dict[k].items():
                    logging.info('Sensors: %s %s %s', k, kk, vv)
                if json_dict[k]['modelid'].startswith('TRADFRI motion sensor'):
                    logging.info('Add sensor %s', k)
                    device = ConBeeMotionSensor(self, uid, str(k), json_dict[k])
                    logging.debug('Sensor %s added', k)
                    self.handle_device_added(device)
                elif json_dict[k]['modelid'].startswith('lumi.weather', '3310-G') and json_dict[k]['type'] == 'ZHATemperature':
                    logging.info('Add sensor %s', k)
                    device = ConBeeTemperatureSensor(self, uid, str(k), json_dict[k])
                    logging.debug('Sensor %s added', k)
                    self.handle_device_added(device)
                else:
                    logging.info('Unknow sensor. Not added')
        except ValueError as ex:
            logging.exception('ERROR Exception %s', ex)
            msg = 'Zigbee-Conbee Adapter: Problem during pairing of devices. Check URL.'
            self.send_error(msg)
        except Exception as ex:
            logging.exception('ERROR Exception %s', ex)

    def cancel_pairing(self):
         """Cancel pairing process."""
         logging.info('cancel_pairing')

    def unload(self):
        """Perform any necessary cleanup before adapter is shut down."""
        try:
            for device_id, device in self.get_devices().items():
                device.active_poll = False
            time.sleep(3)
            for device_id, device in self.get_devices().items():
                logging.info('ConBeeAdapter:' + self.name + 'unloaded. Device ' + device.id)
                super().unload()
        except Exception as ex:
            logging.exception('ERROR Exception %s', ex)
        logging.info('End unload all devices')

    def handle_device_removed(self, device):
        try:
            logging.info('device: ' + device.name + ' to be removed. Device id: ' + device.id)
            logging.info('Device id: %s is_alive: %s', device.id, device.thread.is_alive())
            device.active_poll = False
            #device.thread.join(20.0)
            logging.info('Device id: %s is_alive: %s', device.id, device.thread.is_alive())
            if device.thread.is_alive():
                logging.error('Device id: %s is_alive: %s', device.id, device.thread.is_alive())
            super().handle_device_removed(device)
            logging.info('device:' + device.name + ' is removed. Device ' + device.id)
        except Exception as ex:
            logging.exception('ERROR Exception %s', ex)
        logging.info('End device demoved %s', device.id)
