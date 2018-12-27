"""ConBee adapter for Mozilla IoT Gateway."""

import logging
import threading
import time

from gateway_addon import Device
from conbee_action import FadeAction
from conbee_property import ConBeeBooleanProperty, \
                            ConBeeBrightnessProperty, ConBeeColorTemperatureProperty, \
                            ConBeeLevelProperty, ConBeeMotionProperty, \
                            ConBeePushedProperty, ConBeeOnOffProperty, \
                            InstantaneousPowerProperty, ReachableProperty, \
                            TemperatureProperty

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
        self.add_property(ReachableProperty(self, self.is_reachable()))

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

    def event_action(self, event):
        # {'e': 'changed', 'id': '2', 'state': {'lastupdated': '2018-12-06T20:50:28', 'power': 40}, 't': 'event', 'r': 'sensors'}
        # {'id': '3', 't': 'event', 'state': {'on': False}, 'e': 'changed', 'r': 'lights'}
        # {'t': 'event', 'id': '2', 'e': 'changed', 'r': 'lights', 'state': {'on': False}}
        # {'t': 'event', 'id': '2', 'e': 'changed', 'r': 'lights', 'state': {'bri': 229}}
        # {'t': 'event', 'id': '2', 'e': 'changed', 'r': 'lights', 'state': {'ct': 400}}
        # {'r': 'lights', 'id': '2', 'e': 'changed', 'state': {'reachable': True}, 't': 'event'}
        # {'state': {'reachable': False}, 't': 'event', 'e': 'changed', 'r': 'lights', 'id': '2'} 
        # {'id': '5', 'r': 'sensors', 'state': {'presence': True, 'dark': True, 'lastupdated': '2018-12-09T09:41:52'}, 'e': 'changed', 't': 'event'}
        # {'id': '5', 'r': 'sensors', 'e': 'changed', 'config': {'group': '58842', 'alert': 'none', 'duration': 60, 'battery': 60, 'reachable': True, 'delay': 60, 'on': True}, 't': 'event'}
        handled = False
        if 'config' in event:
            for prop in ['battery', 'reachable']:
                found = self.update_property_from_event(event['config'], prop)
                if found == True:
                    handled = True
        if 'state' in event:
            for prop in ['bri', 'ct', 'dark', 'on', 'power', 'reachable', 'temperature']:
                found = self.update_property_from_event(event['state'], prop)
                if found == True:
                    handled = True
        if handled == False:
            logging.info('Unhandled event. event: %s', event)
        return handled


    def check_if_reachable(self):
        curr_reachable = self.light['state'].get('reachable')
        if curr_reachable == None:
            curr_reachable = self.light['config'].get('reachable')
        if curr_reachable == None:
            logging.error('check_if_reach: %s', curr_reachable)
        self.set_reachable(curr_reachable)

    def set_reachable(self, status):
        status = bool(status)
        if self.reachable != status:
            logging.info('Device: %s is now reachable: %s', self.name, status)
            self.reachable = status
            self.connected_notify(status)

    def update_property_from_event(self, state_config, prop):
        # Return True if this property exist in event
        if prop in state_config:
            val = state_config[prop]
            property = self.find_property(prop)
            property.set_device_value(val)
            return True
        return False

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
    def property_path_value(device, path, prop, name):
        """
        Determine the value of the property for the device.

        prop -- property of the light
        path - 'config' or 'state'
        device -- device of the light
        """
        value = device.light[path][name]
        if 'type' in prop.description and prop.description['type'] == 'boolean':
            value = bool(value)
        return value

class ConBeeAbstractLight(ConBeeDevice):
    def __init__(self, adapter, _id, dev_id, light):
        """ adapter -- the Adapter managing this device
            _id     -- ID of this device
            dev_id  -- id on the conbee device
            light   -- device info from ConBee request """
        ConBeeDevice.__init__(self, adapter, _id, dev_id, light)
        self._context = 'https://iot.mozilla.org/schemas'

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

class ConBee_0010_OnOff_plug_in_unit(ConBeeAbstractLight):
    """ConBee switch type."""
    def __init__(self, adapter, _id, dev_id, light):
        """ adapter -- the Adapter managing this device
            _id -- ID of this device
            dev_id -- id on the conbee device
            light -- device info from ConBee request """
        ConBeeAbstractLight.__init__(self, adapter, _id, dev_id, light)
        self._type = ['OnOffSwitch']
        self.type = 'onOffSwitch'
        logging.info('ConBee_0010_OnOff_plug_in_unit.__init__ %s', light)
        self.add_property(ConBeeOnOffProperty(self,
                                              lambda d, p : self.property_path_value(self, 'state', p, 'on'),
                                              self.adapter.rest.set_state))
        self.add_property(InstantaneousPowerProperty(self, 'Power', 'power', None))

        logging.info('Added: ConBee_0010_OnOff_plug_in_unit')

class ConBee_0100_Dimmable_light(ConBeeAbstractLight):
    def __init__(self, adapter, _id, dev_id, light):
        """
        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeAbstractLight.__init__(self, adapter, _id, dev_id, light)
        self._type = ['Light']
        self.type = 'dimmableColorLight'
        self.add_property(ConBeeOnOffProperty(self, lambda d, p : self.property_path_value(self, 'state', p, 'on'),
                                              self.adapter.rest.set_state))
        self.add_property(ConBeeBrightnessProperty(self, 'Brightness', 'bri',
                                                   lambda d, p : self.property_path_value(self, 'state', p, 'bri'),
                                                   self.adapter.rest.set_state, 2.55, min=10))
        logging.debug('Done ConBee_0100_Dimmable_light %s', str(self.as_dict()))

class ConBee_0220_Color_temperature_light(ConBeeAbstractLight):
    def __init__(self, adapter, _id, dev_id, light):
        """
        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeAbstractLight.__init__(self, adapter, _id, dev_id, light)
        self._type = ['ColorControl', 'Light']
        self.type = 'dimmableColorLight'
        logging.info('ConBee_0220_Color_temperature_light.__init__ %s', light)

        self.add_property(ConBeeOnOffProperty(self, lambda d, p : self.property_path_value(self, 'state', p, 'on'), self.adapter.rest.set_state))
        if self.is_dimmable():
            self.add_property(ConBeeBrightnessProperty(self, 'Brightness', 'bri',
                                                       lambda d, p : self.property_path_value(self, 'state', p, 'bri'),
                                                       self.adapter.rest.set_state, 2.55, min=10))
        if light['state'].get('ct'):
            desc = {"label": "ColorTemp", "type": "number", "unit": "kelvin", "min": light['ctmin'],
                    "max": light['ctmax'], "description": "property descripton", "@type": "ColorTemperatureProperty"}
            logging.info("Add ColorTemp property %s", desc)
            self.add_property(ConBeeColorTemperatureProperty(self, light['ctmin'], light['ctmax'],
                                                             lambda d, p : self.property_path_value(self, 'state', p, 'ct'),
                                                             self.adapter.rest.set_state))
        logging.debug('Done ConBee_0220_Color_temperature_light %s', str(self.as_dict()))

    def perform_action(self, action):
        logging.info('perform_action %s, Dict:%s', action.name, action.as_dict())
        if action.name == 'fade_off':
            prop = self.find_property('bri')
            logging.info('bri %s', prop.as_dict())
            FadeAction(self, prop).start()

class ConBeeAbstractSensor(ConBeeDevice):
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

    def get_dev_data(self):
        return self.adapter.rest.get_sensor(self.dev_id)

class ConBeeZHAPresenceSensor(ConBeeAbstractSensor):
    """ConBee sensor type."""

    def __init__(self, adapter, _id, dev_id, light):
        """
        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeAbstractSensor.__init__(self, adapter, _id, dev_id, light)
        self._type = ['MotionSensor']
        self._context = 'https://iot.mozilla.org/schemas'

        logging.info('ConBeeZHAPresenceSensor.__init__ %s', light)
        self.add_property(ConBeeMotionProperty(self, 'Motion', 'presence',
                                               lambda d, p : self.get_state_value('presence', False)))
        self.add_property(ConBeeLevelProperty(self, 'Battery', 'battery',
                                              lambda d, p : self.property_path_value(self, 'config', p, 'battery')))
        self.add_property(ConBeeBooleanProperty(self, 'Dark', 'dark', False))
        #self.add_property(ReachableProperty(self))
        logging.info('Added ConBeeSensor %s', str(self.as_dict()))

class ConBeeDimmerButton(ConBeeAbstractSensor):
    """
    Dimmer sensor
    properties: dimmer, battery
    events: dimmer
    """

    def __init__(self, adapter, _id, dev_id, light):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeAbstractSensor.__init__(self, adapter, _id, dev_id, light)
        self._type = ['MultiLevelSwitch']
        self._context = 'https://iot.mozilla.org/schemas'

        logging.info('ConBeeDimmerButton.__init__ %s', light)
        self.add_property(ConBeeBrightnessProperty(self, 'Brightness', 'level'))
        self.add_property(ConBeeLevelProperty(self, 'Battery', 'battery', lambda d, p : self.property_path_value(self, 'config', p, 'battery')))

        logging.info('Added ConBeeDimmerButton %s', str(self.as_dict()))

    def event_action(self, event):
        # "state":{"buttonevent":2002,"lastupdated":"2018-12-02T22:25:34"},
        # {'config': {'on': True, 'group': '23917', 'battery': 16, 'alert': 'none', 'reachable': True},
        #  'id': '8', 'e': 'changed', 'r': 'sensors', 't': 'event'} 
        handled = False
        if 'state' in event:
            if 'buttonevent' in event['state']:
                handled = True
                button = event['state']['buttonevent']
                property = self.find_property('level')
                level = property.get_value()
                if level is None:
                    level = 0
                if button == 4002:
                    level = 0
                if button == 3002:
                    if level > 0:
                        level -= 10
                if button == 2002:
                    if level < 100:
                        level += 10
                if button == 1002:
                    level = 100
                property.set_device_value(level)
        if handled == False:
            handled = super().event_action(event)
        return handled

class ConBeeZHATemperatureSensor(ConBeeAbstractSensor):
    """ConBee sensor type."""

    def __init__(self, adapter, _id, dev_id, light, unit_celsius):
        """
        adapter -- the Adapter managing this device
        _id -- ID of this device
        dev_id -- id on the conbee device
        light -- device info from ConBee request
        """
        ConBeeAbstractSensor.__init__(self, adapter, _id, dev_id, light)
        self._type = ['TemperatureSensor']
        self._context = 'https://iot.mozilla.org/schemas'

        # every 5 minutes
        self.poll_interval = 300

        logging.info('ConBeeTemperatureSensor.__init__ %s', light)
        self.add_property(TemperatureProperty(self, 'Temperature', 'temperature',
                                                    lambda d, p : self.get_state_value('temperature', 0), unit_celsius))
        #self.add_property(ConBeeLevelProperty(self, 'Battery', self.property_config_value))
        self.add_property(ConBeeLevelProperty(self, 'Battery', 'battery',
                                              lambda d, p : self.property_path_value(self, 'config', p, 'battery')))

        logging.info('Added ConBeeSensor %s', str(self.as_dict()))

    def get_dev_data(self):
        return self.adapter.rest.get_sensor(self.dev_id)
