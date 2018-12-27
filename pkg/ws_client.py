#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import logging

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect

#def on_msg(msg):
#    #logging.info(msg)
#    #json_msg = json.loads(msg.decode("utf-8"))
#    json_msg = json.loads(msg)
#    logging.info(json_msg)
#    #logging.info('msg: %s', str(json_msg))

class WsClient(object):
    def __init__(self, adapter, url, timeout):
        self.adapter = adapter
        self.url = url
        self.timeout = timeout
        self.ioloop = IOLoop.instance()
        self.ws = None
        logging.info('ws init 1')
        self.connect()
        logging.info('ws init 2')
        #PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
        #PeriodicCallback(self.keep_alive, 20000).start()
        self.ioloop.start()
        logging.info('ws init 3')

    def on_msg(self, msg):
        #logging.info(msg)
        #json_msg = json.loads(msg.decode("utf-8"))
        json_msg = json.loads(msg)
        device = self.adapter.get_device_from_mapping(json_msg['r'], json_msg['id'])
        if device is None:
            logging.info('EVENT : %s', json_msg)
        else:
            device.event_action(json_msg)

    @gen.coroutine
    def connect(self):
        logging.info('trying to connect')
        try:
            self.ws = yield websocket_connect(self.url, on_message_callback=self.on_msg)
        except Exception as e:
            logging.exception('connection error %s', e)
        else:
            logging.info('connected')
            self.run()

    @gen.coroutine
    def run(self):
        try:
            logging.info('ws run()')
            while True:
                msg = yield self.ws.read_message()
                logging.debug('run msg: %s', msg)
                if msg is None:
                    logging.info('connection closed')
                    self.ws = None
                    break
        except Exception as e:
            logging.exception('connection error %s', e)

    def keep_alive(self):
        logging.info('ws keep_alive %s', self.ws)
        if self.ws is None:
            self.connect()
        #else:
        #    self.ws.write_message("keep alive")

#if __name__ == "__main__":
#    client = Client("ws://localhost:3000", 5)
