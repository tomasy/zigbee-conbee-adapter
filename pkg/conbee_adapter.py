"""ConBee adapter for Mozilla IoT Gateway."""

import json
import logging
import sys
import time

from gateway_addon import Adapter

from conbee_config import Config
from conbee_device import ConBeeDimmerButton, ConBeeZHATemperatureSensor, \
                          ConBeeZHAPresenceSensor, ConBee_0010_OnOff_plug_in_unit, \
                          ConBee_0100_Dimmable_light, \
                          ConBee_0220_Color_temperature_light
from deconz_rest_api import DeconzRestApi
from ws_client import WsClient


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
        self.ws = None
        self.device_mapping = {}   # Map between ligt/sensor and device
        logging.info('init ConBeeAdapter')
        self.start_pairing(0)

    def get_uid(self, light_sensor):
        uid = light_sensor['uniqueid']
        # logging.info('uid: %s c: %s len: %s', uid, uid.count(':'), len(uid))
        if uid.count(':') == 7 and len(uid) >= 24:
            return uid[:23]
        return uid

    def create_light_device(self, uid, conbee_id, light):
        if light['type'] == 'On/Off plug-in unit':
            return ConBee_0010_OnOff_plug_in_unit(self, uid, conbee_id, light)
        if light['type'] == 'Dimmable light':
            return ConBee_0100_Dimmable_light(self, uid, conbee_id, light)
        if light['type'] == 'Color temperature light':
            return ConBee_0220_Color_temperature_light(self, uid, conbee_id, light)
        return None

    """ Add device to map of light/sensors """
    def add_device_mapping(self, light_sensor, ix, uid):
        key = '{}_{}'.format(light_sensor, ix)
        self.device_mapping[key] = uid

    def get_device_from_mapping(self, light_sensor, ix):
        key = '{}_{}'.format(light_sensor, ix)
        if key in self.device_mapping:
            device_id = self.device_mapping[key]
            return self.get_device(device_id)
        else:
            #logging.info('No device found for key: %s', key)
            return None

    def start_pairing(self, timeout):
        """  Start pairing process. """
        logging.info('START Pairing Lights')
        if self._config.log_level == 'INFO':
            logging.getLogger().setLevel(logging.INFO)
        else:
            logging.getLogger().setLevel(logging.DEBUG)

        try:
            json_dict = self.rest.get_lights()
            for k, v in json_dict.items():
                uid = self.get_uid(v)
                light = json_dict[k]
                # Check if already added
                if self.get_device(uid) != None:
                    logging.info('Light device %s already exist. Not added again', uid);
                    continue
                for kk, vv in light.items():
                    logging.info('Ligths: %s %s: %s', k, kk, vv)
                logging.info('Add light %s', uid)
                device = self.create_light_device(uid, str(k), light)
                if device is None:
                    logging.warning('Unknow type of light: %s', k)
                else:
                    self.add_device_mapping('lights', k, uid)
                    self.handle_device_added(device)
            logging.info('START Pairing Sensors')
            json_dict = self.rest.get_sensors()
            for k, v in json_dict.items():
                uid = self.get_uid(v)
                if self.get_device(uid) != None:
                    logging.info('Sensor device %s already exist. Will not crate a new device', uid);
                    self.add_device_mapping('sensors', k, uid)
                    continue
                for kk, vv in json_dict[k].items():
                    logging.info('Sensors: %s %s %s', k, kk, vv)
                if json_dict[k]['type'].startswith('ZHAPresence'):
                    device = ConBeeZHAPresenceSensor(self, uid, str(k), json_dict[k])
                    self.add_device_mapping('sensors', k, uid)
                    logging.debug('Sensor %s added', k)
                    self.handle_device_added(device)
                elif json_dict[k]['type'].startswith('ZHASwitch'):
                    device = ConBeeDimmerButton(self, uid, str(k), json_dict[k])
                    self.add_device_mapping('sensors', k, uid)
                    logging.debug('Sensor %s added', k)
                    self.handle_device_added(device)
                elif json_dict[k]['type'].startswith('ZHATemperature'):
                    device = ConBeeZHATemperatureSensor(self, uid, str(k), json_dict[k], self._config.temp_unit_celsius)
                    self.add_device_mapping('sensors', k, uid)
                    logging.debug('Sensor %s added', k)
                    self.handle_device_added(device)
                else:
                    self.add_device_mapping('sensors', k, uid)
                    logging.info('Unknow sensor. Not added')
            for ke, va in self.device_mapping.items():
                logging.info('device_mapping: %s %s', ke, va)

            if self.ws == None:
                self.ws = WsClient(self, self.get_ws_url(), 5)
        except ValueError as ex:
            logging.exception('ERROR Exception %s', ex)
            msg = 'Zigbee-Conbee Adapter: Problem during pairing of devices. Check URL.'
            self.send_error(msg)
        except Exception as ex:
            logging.exception('ERROR Exception %s', ex)

    def get_ws_url(self):
        json_config_dict = self.rest.get_config()
        logging.debug('Conbee config %s', json_config_dict)
        host = json_config_dict['ipaddress']
        port = json_config_dict['websocketport']
        ws_url = 'ws://{}:{}'.format(host, port)
        logging.info('Used websocket url: %s', ws_url)
        return ws_url


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
            logging.info('Device id: %s is_alive: %s', device.id, device.thread.is_alive())
            if device.thread.is_alive():
                logging.error('Device id: %s is_alive: %s', device.id, device.thread.is_alive())
            super().handle_device_removed(device)
            logging.info('device:' + device.name + ' is removed. Device ' + device.id)
        except Exception as ex:
            logging.exception('ERROR Exception %s', ex)
        logging.info('End device demoved %s', device.id)
