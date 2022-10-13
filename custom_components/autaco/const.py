from homeassistant.components.sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import requests
from functools import partial
from requests.auth import HTTPBasicAuth
import traceback
import logging
import datetime
from collections import OrderedDict


_LOGGER = logging.getLogger(__name__)

# generals
DOMAIN = "autarco"
PLATFORM = "sensor"
VERSION = "0.1.0"
ISSUE_URL = "https://github.com/koljawindeler/autarco/issues"
SCAN_INTERVAL = datetime.timedelta(seconds=5)

# configuration
CONF_ICON = "icon"
CONF_AUTARCO_URL = "url"
CONF_NAME = "name"
CONF_INTERVAL = "interval"


# defaults
DEFAULT_ICON = 'mdi:weather-sunny'
DEFAULT_NAME = "autarco"
DEFAULT_INTERVAL = "20"

# error
ERROR_URL = "url_error"

# extend schema to load via YAML
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_AUTARCO_URL): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
	vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
	vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.Coerce(int)
})



async def async_check_data(hass, user_input):
	"""Check validity of the provided date."""
	ret = {}
	if(CONF_AUTARCO_URL in user_input):
#		try:
			_LOGGER.error("running http request")
			url = "http://"+user_input[CONF_AUTARCO_URL]+"/inverter.cgi"
			_LOGGER.error(url)
			d = await hass.async_add_executor_job(partial(requests.get, url, auth=HTTPBasicAuth('admin', '123456789'), timeout=2))
			_LOGGER.error(d)
			_LOGGER.error("result abovew")
			return {}
#		except Exception:
#			ret["base"] = ERROR_URL
#			return ret

def ensure_config(user_input):
	"""Make sure that needed Parameter exist and are filled with default if not."""
	out = {}
	out[CONF_NAME] = ""
	out[CONF_AUTARCO_URL] = ""
	out[CONF_ICON] = DEFAULT_ICON
	out[CONF_INTERVAL] = DEFAULT_INTERVAL

	if user_input is not None:
		if CONF_NAME in user_input:
			out[CONF_NAME] = user_input[CONF_NAME]
		if CONF_AUTARCO_URL in user_input:
			out[CONF_AUTARCO_URL] = user_input[CONF_AUTARCO_URL]
		if CONF_ICON in user_input:
			out[CONF_ICON] = user_input[CONF_ICON]
		if CONF_INTERVAL in user_input:
			out[CONF_INTERVAL] = user_input[CONF_INTERVAL]
	return out


def create_form(user_input):
	"""Create form for UI setup."""
	user_input = ensure_config(user_input)

	data_schema = OrderedDict()
	data_schema[vol.Required(CONF_NAME, default=user_input[CONF_NAME])] = str
	data_schema[vol.Required(CONF_AUTARCO_URL, default=user_input[CONF_AUTARCO_URL])] = str
	data_schema[vol.Optional(CONF_ICON, default=user_input[CONF_ICON])] = str
	data_schema[vol.Optional(CONF_INTERVAL, default=user_input[CONF_INTERVAL])] = vol.Coerce(int)

	return data_schema
