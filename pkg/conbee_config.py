import logging
from gateway_addon import Database

class Config(Database):
    def __init__(self, package_name):
        Database.__init__(self, package_name, None)
        self.temp_unit_celsius = True
        self.log_level = None
        self.open()
        self.load()

    def load(self):
        try:
            config = self.load_config()
            # config = json.loads(config.decode('utf-8'))
            logging.info('config %s', config)
            if config['temperature'] == 'Celsius':
                self.temp_unit_celsius = True
            else:
                self.temp_unit_celsius = False

            self.log_level = config['log_level']
        except Exception as ex:
            logging.exception('Strange config', config)

    def conbee_url(self):
        url = None
        apikey = None

        try:
            config = self.load_config()
            logging.info('config %s', config)
            url = config['url']
            apikey = config['apikey']
        except Exception as ex:
            logging.exception('Strange config', config)

        return url + '/api/' + apikey + '/'
