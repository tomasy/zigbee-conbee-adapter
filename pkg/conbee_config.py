import logging
from gateway_addon import Database

class Config(Database):
    def __init__(self, package_name):
        Database.__init__(self, package_name, None)
        self.open()

    def conbee_url(self):
        url = None
        apikey = None
        try:
            config = self.load_config()
#            config = json.loads(config.decode('utf-8'))
            logging.info('config %s', config)
            url = config['url']
            apikey = config['apikey']
        except Exception as ex:
            logging.exception('Strange config', config)

        return url + '/api/' + apikey + '/'
