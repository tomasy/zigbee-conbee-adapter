"""ConBee adapter for Mozilla IoT Gateway."""

import logging

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
            self.set_cached_value(value)
        logging.info("ConbeeProperty__init__ device.id: %s %s %s %s", device.id, name, description, value)

    def set_cached_value(self, new_value):
        if 'minimum' in self.description:
            mini = int(self.description.get('minimum'))
            if new_value < mini:
                logging.info('Below minimum. was %s set to %s', new_value, mini)
                new_value = mini
        value = super().set_cached_value(new_value)
        set_dev_val = self.prop2dev_value(value)
        logging.info("prop: %s New property value: %s ==%s -> Dev.Value: %s (%s)", self.name, new_value, value, set_dev_val, self.dev_value)
        self.dev_value = set_dev_val
        if self.func_set is not None:
            self.func_set(self.device.dev_id, self.description['type'], self.name, set_dev_val)
        return value

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

    def set_value(self, value):
        """
        Set the current value of the property. Overrides Property.set_value

        value -- the value to set
        """
        self.set_cached_value(value)
        self.device.notify_property_changed(self)

    def update(self):
        """
        Update the current value, if necessary.
        """
        new_dev_value = self.func_is(self.device, self)  # 0-255

        if new_dev_value != self.dev_value:
            logging.info('Device: %s property %s = %s (%s)', self.device.name, self.name, new_dev_value, self.dev_value)
            self.dev_value = new_dev_value
            value = self.dev2prop_value(new_dev_value)

            self.set_cached_value(value)
            self.device.notify_property_changed(self)


class ConBeeOnOffProperty(ConBeeProperty):
    """Property on/off."""

    def __init__(self, device, func_is, func_set):
        """
        device - the deivce
        func_is - function with ligth as argument. Return True/false if property is on off func_is(device)
        func_set - function that change the value func_set(device, value)
        """
        ConBeeProperty.__init__(self, device, 'on', {'@type': 'OnOffProperty', 'type': 'boolean', 'description': 'On or Off'},
                                func_is(device))
        logging.info('New OnOff property to %s', device.name)
        self.func_is = func_is
        self.func_set = func_set

class ConBeeBrightnessProperty(ConBeeProperty):
    """Dim property value."""

    def __init__(self, device, func_is, func_set):
        """
        device - the deivce
        func_is - function with ligth as argument. Return dim value if property is on off func_is(device)
        func_set - function that change the value func_set(device, value)
        """
        ConBeeProperty.__init__(self, device, 'bri',
                                {'@type': 'BrightnessProperty', 'type': 'number', 'min': '1', 'max': '100',
                                 'unit': 'percent', 'description': 'property descripton'}, 50)
        logging.info('Dim property to device %s', device.name)
        self.func_is = func_is
        self.func_set = func_set

    def dev2prop_value(self, value):
        """
        Convert device value to property value. e.g. 255 -> 100%

        value -- the value from device
        """
        return int(int(value) / 2.55)

    def prop2dev_value(self, value):
        """
        Convert property value to device value. e.g. 100% -> 255

        value -- the value from device
        """
        return int(int(value) * 2.55)


class ConBeeColorTemperatureProperty(ConBeeProperty):
    """Color Temperature property"""

    def __init__(self, device, ctmin, ctmax, func_is, func_set):
        """
        device - the deivce
        ctmin, ctmax - min and max color temperature
        func_is - function with ligth as argument. Return dim value if property is on off func_is(device)
        func_set - function that change the value func_set(device, value)
        """
        desc = {"label": "ColorTemp", '@type': 'ColorTemperatureProperty',"type": "number", "unit": "kelvin", "min": ctmin,
                "max": ctmax, "description": "property descripton"}
        ConBeeProperty.__init__(self, device, 'ct', desc, func_is=func_is, func_set=func_set)
        self.update()
        logging.info('Color temperature property to device %s', device.name)


class ConBeeMotionProperty(ConBeeProperty):
    def __init__(self, device, func_is):
        desc = {'label': 'MMotion', '@type': 'MotionProperty', 'type': 'boolean', 'readOnly': True, 'description': 'motion or not descripton'}
        ConBeeProperty.__init__(self, device, 'motion', desc, func_is=func_is)
        self.update()
        logging.info('Motion property to device %s', device.name)


class ConBeeLevelProperty(ConBeeProperty):
    def __init__(self, device, label, func_is):
        desc = {'label': label, '@type': 'LevelProperty', 'type': 'number', 'minimum': 0, 'maximum': 100,
                'unit': 'percent','readOnly': True, 'description': 'Battery level'}
        ConBeeProperty.__init__(self, device, 'battery', desc, func_is=func_is)
        logging.info('Level property to device %s', device.name)


class ConBeeTemperatureProperty(ConBeeProperty):
    def __init__(self, device, func_is):
        desc = {'label': 'Temperature', '@type': 'TemperatureProperty', 'type': 'number', 'readOnly': True, 'description': 'temperature'}
        ConBeeProperty.__init__(self, device, 'temperature', desc, func_is=func_is)
        self.update()
        logging.info('Temperature property to device %s', device.name)

    def dev2prop_value(self, value):
        """
        Convert device value to property value. e.g. 1800 -> 64.4F

        value -- the value from device
        """
        # return int(int(value) / 2.55)
        return ((value / 100) * 9/5) + 32
        # (18°C × 9/5) + 32 = 64.4°F

