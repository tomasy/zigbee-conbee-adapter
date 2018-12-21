"""Action for Mozilla IoT Gateway."""

import logging
import threading
import time

from gateway_addon import Action

class FadeAction(Action):
    """DT action type."""
    def __init__(self, device, property_):
        self.property = property_
        """
        Initialize the object.
        id_ ID of this action
        device -- the device this action belongs to
        name -- name of the action
        input_ -- any action inputs
        """
        # Action. __init__(self, id_, device, name, input_):
        metadata = {'label': 'Fadde', 'description': 'Desc', 'input': {'type': 'number'}}
        Action. __init__(self, 'fade_', device, 'fade', metadata)

    def start(self):
        """Start performing the action."""
        # self.status = 'pending'
        # self.device.action_notify(self)
        def fade_action_fn(action, property):
            try:
                logging.info('fade action %s prop %s', action, property)
                iix = 20
                while iix > 0:
                    value = property.get_value()
                    property.set_value(value - 5)
                    iix -= 1
                    time.sleep(0.5)
                    logging.info('act perform')
            except Exception as ex:
                logging.exception('ERROR Exception %s', ex)
            logging.info('act done')
            action.finish()
        self.make_thread(fade_action_fn, args=(self, self.property))
        super.start()

    def finish(self):
        """Finish performing the action."""
#        self.status = 'completed'
#        self.time_completed = timestamp()
#        self.device.action_notify(self)
        logging.info('Action finished')
        super.finish()

    @staticmethod
    def make_thread(target, args=()):
        """
        Start up a thread in the background.
        target -- the target function
        args -- arguments to pass to target
        """
        t = threading.Thread(target=target, args=args)
        t.daemon = True
        t.start()
