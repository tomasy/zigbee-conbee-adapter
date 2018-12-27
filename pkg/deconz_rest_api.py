"""
ConBee adapter for Mozilla IoT Gateway.
Rest API using DevConz API
"""
import json
import logging
import sys
import traceback
import urllib.request

class State:
    def __init__(self):
        pass

class Light:
    def __init__(self, json_def):
        self.state = State()
        self.__dict__ = json.loads(json_def)
        pass

    def isOn(self):
        return self.state['on']

# Type of keys values when sending to device
BOOLEANS = ['on', 'presence']
INTEGERS = ['bri', 'ct']


class DeconzRestApi:
    def __init__(self, conbee_url):
        self.conbee_url = conbee_url

    def get_config(self):
        json_response = urllib.request.urlopen(self.conbee_url + '/config').read()
        return json.loads(json_response.decode("utf-8"))

    def get_lights(self):
        json_response = urllib.request.urlopen(self.conbee_url + '/lights').read()
        return json.loads(json_response.decode("utf-8"))

    def get_sensors(self):
        json_response = urllib.request.urlopen(self.conbee_url + '/sensors').read()
        return json.loads(json_response.decode("utf-8"))

    def getLight(self, dev_id):
        json_response = urllib.request.urlopen(self.conbee_url + '/lights/' + str(dev_id)).read()
        return json.loads(json_response.decode("utf-8"))
    def get_sensor(self, dev_id):
        json_response = urllib.request.urlopen(self.conbee_url + '/sensors/' + str(dev_id)).read()
        return json.loads(json_response.decode("utf-8"))

    def setState(self, dev_id, state):
        """ dev_id -- device id
            stat -- new State on device True/False
        """
        self.send_state(dev_id, '{{ "on": {0} }}'.format(booleanToLower(state)))
        return

    def set_state(self, dev_id, _type, key, value):
        """ Set state on the device via a http PUT
            dev_id -- device id
            key -- device key
            value -- device value
        """
        dic = {}
        dic[key] = value
        self.set_state_values(dev_id, dic)
        return

    def set_state_values(self, dev_id, dic):
        """ Set state on the device via a http PUT
            dev_id -- device id
            dic -- dict with keys and values
        """
        json_data = '{'
        first = True
        for key, value in dic.items():
            if first:
                first = False
            else:
                json_data += ','
            if key in BOOLEANS:
                json_data += ' "{0}": {1} '.format(key, booleanToLower(value))
            elif key in INTEGERS:
                json_data += ' "{0}": {1} '.format(key, value)
            else:
                json_data += ' "{0}": "{1}" '.format(key, value)
        json_data += '}'
        self.send_state(dev_id, json_data)
        return

    def send_state(self, dev_id, json_state):
        """ dev_id -- device id
            json_state -- new State to send to device
        """
        try:
            json_state = strToBytes(json_state)
            logging.debug('set_state dev_id: %s -> %s', dev_id, json_state)
            req = urllib.request.Request(url=self.conbee_url + 'lights/' + str(dev_id) + '/state', data=json_state, method='PUT')
            with urllib.request.urlopen(req) as f:
                logging.debug('Resp. dev_id: %s f.status: %s READ: %s', dev_id, f.status, f.read())
                pass
        except Exception as ex:
            logging.exception('Exception %2', ex)
            logging.error('Exception', ex.args)
            logging.error(traceback.format_exception(None, # <- type(e) by docs, but ignored
                                         ex, ex.__traceback__), file=sys.stderr)
        return

def booleanToLower(state):
    if state: return 'true'
    return 'false'

def strToBytes(st):
    b = bytearray()
    b.extend(map(ord, st))
    return b
