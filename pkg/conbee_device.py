"""ConBee adapter for Mozilla IoT Gateway."""

import logging
import threading
import time

from gateway_addon import Device
from conbee_action import FadeAction
from conbee_property import ConBeeBrightnessProperty, ConBeeColorTemperatureProperty, \
                            ConBeeLevelProperty, ConBeeMotionProperty, \
                            ConBeeOnOffProperty, ConBeeTemperatureProperty

class ConBeeDevice(Device):
    """ConBee device type."""

    def __init__(self, adapter, _id, dev_id, light):
        """
        adapter -- the Adapter for this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from deconz - ConBee request
        """
        Device.__init__(self, adapter, _id)
        self.etag = ''
        self.poll_interval = 2
        self.reachable = None

        self.dev_id = dev_id
        self.light = light
        if 'name' in light.keys() and len(light['name']) > 0:
            self.name = light['name']
        else:
            self.name = light['manufacturername']
        self.description = light['manufacturername'] + ' / ' + light['type']

        self.active_poll = True
        self.thread = threading.Thread(target=self.poll)
        self.thread.daemon = True
        self.thread.start()

    def add_property(self, property):
        self.properties[property.name] = property

    def is_reachable(self):
        return self.get_state_value('reachable', False)

    def get_state_value(self, key, default=None):
        return self.light['state'].get(key, default)

    def check_if_reachable(self):
        curr_reachable = self.light['state'].get('reachable')
        if self.reachable != curr_reachable:
            logging.info('Device: %s is now reachable: %s', self.name, curr_reachable)
            self.reachable = curr_reachable
            self.connected_notify(curr_reachable)


    def poll(self):
        """ Poll device for changes."""
        logging.info('poll START for %s', self.name)
        while self.active_poll:
            try:
                time.sleep(self.poll_interval)
                self.light = self.get_dev_data()
                if self.light.get('etag') != self.etag:
                    logging.debug('Changed etag %s for device %s - %s', self.etag, self.name, self.light)
                    self.etag = self.light.get('etag')
                    self.check_if_reachable()
                for prop in self.properties.values():
                    prop.update()
            except Exception as ex:
                logging.exception('Exception %s', ex)
                continue
        logging.info('POLL stop for: %s', self.name)

    @staticmethod
    def is_on(device, prop=None):
        """
        Is light on or off.

        device -- device the light is connected to
        """
        key = 'on'
        if prop is not None:
            key = prop.name
        light = device.light
        state = light['state']
        if device.is_reachable() and state[key]:
            return True
        return False

    @staticmethod
    def property_config_value(device, prop):
        """
        Determine the value of the property for the device.

        prop -- property of the light
        device -- device of the light
        """
        return  device.property_value(device, 'config',prop)

    @staticmethod
    def property_value(device, path, prop):
        """
        Determine the value of the property for the device.

        prop -- property of the light
        path - 'config' or 'state'
        device -- device of the light
        """
        value = device.light[path][prop.name]
        if 'type' in prop.description and prop.description['type'] == 'boolean':
            value = bool(value)
        return value

    @staticmethod
    def property_state_value(device, prop):
        """
        Determine the value of the property for the device.

        prop -- property of the light
        device -- device of the light
        """
        pname = prop.name
        if pname == 'brightness':
            pname = 'bri'
        if pname == 'colorTemperature':
            pname = 'ct'
        value = device.light['state'][pname]
        if 'type' in prop.description and prop.description['type'] == 'boolean':
            value = bool(value)
        return value

class ConBeeLight(ConBeeDevice):
    """ConBee smart bulb type."""

    def __init__(self, adapter, _id, dev_id, light):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeDevice.__init__(self, adapter, _id, dev_id, light)
        self._context = 'https://iot.mozilla.org/schemas'
        self._type = ['OnOffSwitch']
        # self.type = 'boolean'
        self.type = 'onOffSwitch'


        logging.info('ConBeeLight.__init__ %s', light)
        self.add_property(ConBeeOnOffProperty(self, self.is_on, self.adapter.rest.set_state))
        logging.info('ConBeeLight.__init__ OnOff added')

        if self.is_dimmable():
            self._type = ['OnOffSwitch', 'Light']
            self.type = 'dimmableColorLight'
            self.add_property(ConBeeBrightnessProperty(self, self.property_state_value, self.adapter.rest.set_state))
            # metadata = {'label': 'Fade', 'description': 'Fade down'}
            # self.add_action('fade_off', metadata)

        if light['state'].get('ct'):
            self._type = ['OnOffSwitch', 'Light', 'ColorControl']
            self.type = 'Light'
            desc = {"label": "ColorTemp", "type": "number", "unit": "kelvin", "min": light['ctmin'],
                    "max": light['ctmax'], "description": "property descripton", "@type": "ColorTemperatureProperty"}
            logging.info("Add ColorTemp property %s", desc)
            self.add_property(ConBeeColorTemperatureProperty(self, light['ctmin'], light['ctmax'],
                                                             self.property_state_value,
                                                             self.adapter.rest.set_state))
        logging.debug('Done ConBeeLight %s', str(self.as_dict()))

    def perform_action(self, action):
        logging.info('perform_action %s, Dict:%s', action.name, action.as_dict())
        if action.name == 'fade_off':
            prop = self.find_property('bri')
            logging.info('bri %s', prop.as_dict())
            FadeAction(self, prop).start()


    def get_dev_data(self):
        return self.adapter.rest.getLight(self.dev_id)

    def is_dimmable(self):
        """
        Determine whether or not the light is dimmable.
        """
        bri = self.get_state_value('bri', False)
        if bri is not False:
            return True
        return False

class ConBeeMotionSensor(ConBeeDevice):
    """ConBee sensor type."""

    def __init__(self, adapter, _id, dev_id, light):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeDevice.__init__(self, adapter, _id, dev_id, light)
        self._type = ['MotionSensor']
        self._context = 'https://iot.mozilla.org/schemas'

        logging.info('ConBeeMotionSensor.__init__ %s', light)
        self.add_property(ConBeeMotionProperty(self, self.is_motion))
        self.add_property(ConBeeLevelProperty(self, 'Battery', self.property_config_value))

        logging.info('Added ConBeeSensor %s', str(self.as_dict()))

    def get_dev_data(self):
        return self.adapter.rest.get_sensor(self.dev_id)

    @staticmethod
    def is_motion(device, prop=None):
        """
        Is light on or off.

        device -- device the light is connected to
        """
        return device.get_state_value('presence', False)

class ConBeeTemperatureSensor(ConBeeDevice):
    """ConBee sensor type."""

    def __init__(self, adapter, _id, dev_id, light):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeDevice.__init__(self, adapter, _id, dev_id, light)
        self._type = ['TemperatureSensor']
        self._context = 'https://iot.mozilla.org/schemas'

        logging.info('ConBeeTemperatureSensor.__init__ %s', light)
        self.add_property(ConBeeTemperatureProperty(self, self.property_state_value))
        # self.add_property(ConBeeLevelProperty(self, 'Battery', self.property_config_value))

        logging.info('Added ConBeeSensor %s', str(self.as_dict()))

    def get_dev_data(self):
        return self.adapter.rest.get_sensor(self.dev_id)
