# Zigbee-ConBee Adapter

ConBee adapter for Mozilla IoT Gateway.

Zigbee-ConBee Adapter use DeConz REST API to access the devices. Connecting devices to the Zigbee network is done by using one of the tools from the manufacturer of ConBee USB stick (Dresden Elektronik).

In short. ZigBee-ConBee adapter talks to DeConz REST API. DeConz talks to ConBee USB stick that talk to the devices. Very simple.

# Installation
* Install the ConBee USB adapter and its tools.
* Get an authorization key. See  http://dresden-elektronik.github.io/deconz-rest-doc/authorization/
* Access http://{DeConz_REST_API_server}/api/{authorization_key}/lights Now shall all attached lights show up
* Go to the configuration for Zigbee-ConBee adapter and apply the url to DeConz REST API and the authorization key  (API key)

## Tested devices

* Switch onoff
  * manufacturer name: OSRAM
	* modelid Plug 01
    * swversion V1.04.90
    * type On/Off plug-in unit
* Bulb
  * manufacturer name: IKEA of Sweden
    * modelid: "TRADFRI bulb E27 WS opal 980lm"
    * swversion: "1.2.217"
  * manufacturer name: IKEA of Sweden
    * modelid: "TRADFRI bulb E27 W opal 1000lm"
    * swversion: "1.2.214"
* Sensors
  * manufacturer name: "IKEA of Sweden"
    *modelid: "TRADFRI motion sensor"

If you find it works for other devices create an issue and I will update the list.

# Requirements

* ConBee USB stick
* Installed DeConz REST API

# Missing support for device
Create an issue with the parameters for the device.  
Example:  
http://{url_to_DeConz_host}/api/{api_key}/lights    # for all lights  
http://{url_to_DeConz_host}/api/{api_key}/lights/1  # for the first light  
http://{url_to_DeConz_host}/api/{api_key}/sensors   # sensors
