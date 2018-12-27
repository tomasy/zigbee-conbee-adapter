"""ConBee adapter for Mozilla IoT Gateway."""

import logging
import traceback
from gateway_addon import Property

class ConBeeProperty(Property):
    """ConBee property type."""

    def __init__(self, device, name, description, value=None, func_is=None, func_set=None):
        """
        Initialize the object.

        device -- the Device this property belongs to
        name -- name of the property
        description -- description of the property, as a dictionary
        value -- current value of this property

        description e.g. {'type': 'boolean'} or more
        'visible'
        'min'
        'max'
        'type'
        'unit'
        'description'
        'minimum'
        'maximum'
        """
        Property.__init__(self, device, name, description)
        # value to and from device
        self.dev_value = 0
        self.func_is = func_is
        self.func_set = func_set
        if value is not None:
            self.set_value(value)
        logging.info("ConbeeProperty__init__ device.id: %s %s %s %s", device.id, name, description, value)

    def set_cached_value(self, new_value):
        logging.info('ccccccccccccc')
        stack_str = ''.join(traceback.format_stack())
        logging.info('set_cahced %s', stack_str)
        if 'minimum' in self.description:
            mini = int(self.description.get('minimum'))
            if new_value < mini:
                logging.info('Below minimum. was %s set to %s', new_value, mini)
                new_value = mini

        old_value = self.get_value()
        if old_value != new_value:
            super().set_cached_value(new_value)
            set_dev_val = self.prop2dev_value(new_value)
            logging.info("prop: %s New property value: %s (%s) -> Dev.Value: %s (%s)",
                         self.name, new_value, old_value, set_dev_val, self.dev_value)
            self.dev_value = set_dev_val
            if self.func_set is not None:
                self.func_set(self.device.dev_id, self.description['type'], self.name, set_dev_val)
        return new_value

    def dev2prop_value(self, value):
        """
        Convert device value to property value. e.g. 255 -> 100%
        value -- the value from device
        """
        return value

    def prop2dev_value(self, value):
        """
        Convert property value to device value. e.g. 100% -> 255
        value -- the value from device
        """
        return value

    def set_device_value(self, dvalue):
        """ The device value to set """
        if dvalue != self.dev_value:
            new_value = self.dev2prop_value(dvalue)
            self.set_value(new_value)

    def set_value(self, new_pvalue):
        """ Set the current value of the property. Overrides Property.set_value
            value -- the value to set """
        if new_pvalue != self.get_value():
            if 'minimum' in self.description:
                mini = int(self.description.get('minimum'))
                if new_pvalue < mini:
                    logging.info('Below minimum. was %s set to %s', new_pvalue, mini)
                    new_pvalue = mini

            old_pvalue = self.get_value()
            if old_pvalue != new_pvalue:
                super().set_cached_value(new_pvalue)
                set_dval = self.prop2dev_value(new_pvalue)
                logging.info("%s::%s = %s (%s) -> Dev.Value: %s (%s)",
                             self.device.name, self.name, new_pvalue, old_pvalue, set_dval, self.dev_value)
                self.dev_value = set_dval
                if self.func_set is not None:
                    self.func_set(self.device.dev_id, self.description['type'], self.name, set_dval)
            else:
                logging.error('New value the sam as old_value')
            self.device.notify_property_changed(self)

    def update(self):
        """
        Update the current value, if necessary.
        """
        if self.func_is is None:
            return
        new_dev_value = self.func_is(self.device, self)
        self.set_device_value(new_dev_value)

class ConBeeBooleanProperty(ConBeeProperty):
    # !!!! Changed order of func_is and func_set
    def __init__(self, device, label, name, read_only = False, func_set = None, func_is = None):
        """
        func_is - function with ligth as argument. Return True/false if property is on off func_is(device)
        func_set - function that change the value func_set(device, value)
        """
        desc = {'label': label, '@type': 'BooleanProperty', 'type': 'boolean', 'readOnly': read_only, 'description': 'True or False'}
        ConBeeProperty.__init__(self, device, name, desc,
                                False)
        logging.info('New Booelan property to %s', device.name)
        self.func_is = func_is
        self.func_set = func_set

class ConBeeOnOffProperty(ConBeeProperty):
    """Property on/off."""

    def __init__(self, device, func_is, func_set):
        """
        device - the deivce
        func_is - function with ligth as argument. Return True/false if property is on off func_is(device)
        func_set - function that change the value func_set(device, value)
        """
        ConBeeProperty.__init__(self, device, 'on', {'@type': 'OnOffProperty', 'type': 'boolean', 'description': 'On or Off'},
                                False)
        logging.info('OnOff property to %s', device.name)
        self.func_is = func_is
        self.func_set = func_set

class ConBeeBrightnessProperty(ConBeeProperty):
    """Dim property value."""

    def __init__(self, device, label, name, func_is = None, func_set = None, factor = 1.0, min = 0):
        """
        device - the deivce
        func_is - function with ligth as argument. Return dim value if property is on off func_is(device)
        func_set - function that change the value func_set(device, value)
        factor - factor to convert 100% to max value
        """
        self.factor = factor
        ConBeeProperty.__init__(self, device, name,
                                {'label': label, '@type': 'BrightnessProperty', 'type': 'integer', 'min': min, 'max': 100,
                                 'unit': 'percent', 'multipleOf': 10, 'description': 'property descripton'}, 50)
        logging.info('Brighness property to device %s', device.name)
        self.func_is = func_is
        self.func_set = func_set

    def dev2prop_value(self, value):
        """
        Convert device value to property value. e.g. 255 -> 100%

        value -- the value from device
        """
        return int(int(value) / self.factor)

    def prop2dev_value(self, value):
        """
        Convert property value to device value. e.g. 100% -> 255

        value -- the value from device
        """
        return int(int(value) * self.factor)


class ConBeeColorTemperatureProperty(ConBeeProperty):
    """Color Temperature property"""

    def __init__(self, device, ctmin, ctmax, func_is, func_set):
        """
        device - the deivce
        ctmin, ctmax - min and max color temperature
        func_is - function with ligth as argument. Return dim value if property is on off func_is(device)
        func_set - function that change the value func_set(device, value)
        """
        desc = {'label': 'ColorTemp', '@type': 'ColorTemperatureProperty',"type": 'integer', 'unit': 'kelvin', 'min': ctmin,
                'max': ctmax, 'description': 'property descripton'}
        ConBeeProperty.__init__(self, device, 'ct', desc, func_is=func_is, func_set=func_set)
        self.update()
        logging.info('Color temperature property to device %s', device.name)


class ConBeeMotionProperty(ConBeeProperty):
    def __init__(self, device, label, name, func_is):
        desc = {'label': label, '@type': 'MotionProperty', 'type': 'boolean', 'readOnly': True, 'description': 'motion or not descripton'}
        ConBeeProperty.__init__(self, device, name, desc, func_is=func_is)
        self.update()
        logging.info('Motion property to device %s', device.name)

class ConBeePushedProperty(ConBeeProperty):
    def __init__(self, device, func_is):
        desc = {'label': 'Pushed', '@type': 'PushedProperty', 'type': 'integer', 'readOnly': True, 'description': 'pushed descripton'}
        ConBeeProperty.__init__(self, device, 'buttonevent', desc, func_is=func_is)
        self.update()
        logging.info('PushedProperty to device %s', device.name)

class ConBeeLevelProperty(ConBeeProperty):
    def __init__(self, device, label, name, func_is):
        desc = {'label': label, '@type': 'LevelProperty', 'type': 'integer', 'minimum': 0, 'maximum': 100,
                'unit': 'percent','readOnly': True, 'description': 'Battery level'}
        ConBeeProperty.__init__(self, device, name, desc, func_is=func_is)
        logging.info('Level property to device %s', device.name)

class InstantaneousPowerProperty(ConBeeProperty):
    def __init__(self, device, label, name, func_is):
        desc = {'label': label, '@type': 'InstantaneousPowerProperty', 'type': 'integer',
                'unit': 'watt','readOnly': True, 'description': 'Power effect'}
        ConBeeProperty.__init__(self, device, name, desc, func_is=func_is)
        logging.info('InstantaneousPowerProperty to device %s', device.name)

class ReachableProperty(ConBeeProperty):
    def __init__(self, device, value):
        ConBeeProperty.__init__(self, device, 'reachable',
                                {'label': 'Reachable', '@type': 'BooleanProperty', 'type': 'boolean',
                                 'description': 'On or Off', 'readOnly': True, 'visible': True},
                                None)
        self.set_device_value(value)
        logging.info('Reachable property to %s', device.name)

    def set_device_value(self, value):
        """ The device value to set """
        value = bool(value)
        if value != self.dev_value:
            self.dev_value = value
            self.set_value(value)
            self.device.connected_notify(value)

class TemperatureProperty(ConBeeProperty):
    def __init__(self, device, label, name, func_is, unit_celsius):
        self.unit_celsius = unit_celsius
        if unit_celsius:
            unit = 'degree celsius'
        else:
            unit = 'degree fahrenheit'

        desc = {'label': label, '@type': 'TemperatureProperty', 'type': 'number', 'unit': unit,
                'readOnly': True, 'description': 'Temperature'}
        ConBeeProperty.__init__(self, device, name, desc, func_is=func_is)
        self.update()
        logging.info('Temperature property to device %s', device.name)

    def dev2prop_value(self, value):
        """
        Convert device value to property value. e.g. 1800 -> 64.4F
        value -- the value from device
        """
        # return int(int(value) / 2.55)
        # (18°C × 9/5) + 32 = 64.4°F
        if self.unit_celsius:
            return (value / 100)
        return ((value / 100) * 9/5) + 32
