"""ConBee Addon for Mozilla IoT Gateway!"""

from os import path
import functools
import gateway_addon
import logging
import signal
import sys
import time
import traceback

sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

from pkg.conbee_adapter import ConBeeAdapter

_API_VERSION = {
    'min': 2,
    'max': 2,
}
_ADAPTER = None

print = functools.partial(print, flush=True)


def cleanup(signum, frame):
    """Clean up any resources before exiting."""
    if _ADAPTER is not None:
        _ADAPTER.close_proxy()

    sys.exit(0)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)s %(levelname)s %(message)s",
        stream = sys.stdout
    )
    logging.info('Starting Zigbee Conbee Addon')
    if gateway_addon.API_VERSION < _API_VERSION['min'] or \
            gateway_addon.API_VERSION > _API_VERSION['max']:
        logging.error('Unsupported API version. ver: %s', gateway_addon.API_VERSION)
        sys.exit(0)

    try:
        logging.info('Starting zigbee-conbee-adapter. gateway_addon.API_VERSION: %s', gateway_addon.API_VERSION)
        logging.info('Arguments list: %s', str(sys.argv))
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
        _ADAPTER = ConBeeAdapter(verbose=True)
        logging.debug('adapter created')
        # Wait until proxy stops running. this indicats that the gateway has shut down.
        while _ADAPTER.proxy_running():
            time.sleep(2)
    except Exception as ex:
        print('EXECPTION')
        print(ex)
        print(ex.args)
        print(traceback.format_exception(None, # <- type(e) by docs, but ignored
                                         ex, ex.__traceback__), file=sys.stdout)
    logging.info('STOPPED Zigbee Conbee Addon')
