"""
Custom component to grab data from a autarco solar inverter.

@ Author	  : Kolja Windeler
@ Date		  : 2022/10/09
@ Description : Grabs and parses the data of a autarco inverter
"""
import logging
from homeassistant.const import TEMP_CELSIUS, ENERGY_KILO_WATT_HOUR
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (CONF_NAME)

from tzlocal import get_localzone
from functools import partial
import requests
import datetime
import traceback
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
	"""Run setup via YAML."""
	_LOGGER.debug("Config via YAML")
	if(config is not None):
		async_add_entities([autarco_power_sensor(hass, config)], True)
		async_add_entities([autarco_temp_sensor(hass, config)], update_before_add=False)
		async_add_entities([autarco_kwh_total_sensor(hass, config)], update_before_add=False)


async def async_setup_entry(hass, config, async_add_devices):
	"""Run setup via Storage."""
	_LOGGER.debug("Config via Storage/UI")
	if(len(config.data) > 0):
		async_add_devices([autarco_power_sensor(hass, config)], True)
		async_add_devices([autarco_temp_sensor(hass, config)], update_before_add=False)
		async_add_devices([autarco_kwh_total_sensor(hass, config)], update_before_add=False)


class autarco_power_sensor(Entity):
	"""Representation of a Sensor."""
	def __init__(self, hass, config):
		"""Initialize the sensor."""
		self._state_attributes = None
		self._state = None

		self.hass = hass
		self._unique_id = config.entry_id

		self._url = config.data.get(CONF_AUTARCO_URL)
		self._name = config.data.get(CONF_NAME)
		self._icon = config.data.get(CONF_ICON)
		self._interval = int(config.data.get(CONF_INTERVAL))

		now = datetime.datetime.now(get_localzone()).replace(microsecond=0)
		self._lastUpdate = now - datetime.timedelta(seconds = self._interval)
		self._id = self._url.split('.')[-1]

		_LOGGER.debug("AUTARCO config: ")
		_LOGGER.debug("\tname: " + self._name)
		_LOGGER.debug("\turl: " + self._url)
		_LOGGER.debug("\ticon: " + str(self._icon))

		self.autarco = {
			'extra': {
				'firmware_version': "loading",
				'inverter_model': "loading",
				'serial_number': "loading",
				'temp': 0,
				'kwh_total': 0,
				'kwh_today': 0,
				'max_power': 0,
				'alerts': "loading",

				'last_updated': None,
				'reload_at': None,
			},
			'power': 0,
		}

		self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "autarco_"+str(self._id), hass=hass)

	@property
	def name(self):
		"""Return the name of the sensor."""
		return self._name

	@property
	def extra_state_attributes(self):
		"""Return the state attributes."""
		return self._state_attributes

	@property
	def unit_of_measurement(self):
		"""Return the unit the value is expressed in."""
		return "W"

	@property
	def state(self):
		"""Return the state of the sensor."""
		return self._state

	@property
	def icon(self):
		"""Return the icon to use in the frontend."""
		return self._icon

	def exc(self):
		"""Print nicely formated exception."""
		_LOGGER.error("\n\n============= AUTARCO Integration Error ================")
		_LOGGER.error("unfortunately AUTARCO hit an error, please open a ticket at")
		_LOGGER.error("https://github.com/KoljaWindeler/autarco/issues")
		_LOGGER.error("and paste the following output:\n")
		_LOGGER.error(traceback.format_exc())
		_LOGGER.error("\nthanks, Kolja")
		_LOGGER.error("============= AUTARCO Integration Error ================\n\n")

	async def get_data(self):
		url = "http://"+self._url+"/inverter.cgi"

		try:
			now = datetime.datetime.now(get_localzone()).replace(microsecond=0)

			d = await self.hass.async_add_executor_job(partial(requests.get, url, auth=HTTPBasicAuth('admin', '123456789'), timeout=2))
			ds = d.content.decode('ISO-8859-1').split(';')

			if(len(ds)>=8):
				self._lastUpdate = now
				self.autarco['extra']['last_updated'] = now
				self.autarco['extra']['reload_at'] = now + datetime.timedelta(seconds = self._interval)

				self.autarco['extra']['firmware_version'] = ds[1]
				self.autarco['extra']['inverter_model'] = ds[2]
				self.autarco['extra']['serial_number'] = ds[0][-16:]
				self.autarco['extra']['kwh_today'] = float(ds[5])
				self.autarco['extra']['alerts'] = ds[7]
				self.autarco['power'] = round(float(ds[4]))

				if(self.autarco['power'] > self.autarco['extra']['max_power']):
					self.autarco['extra']['max_power'] = self.autarco['power']

				# only update dependnant sensor if we get info
				self.hass.data[DOMAIN][self._unique_id]['temp'] = float(ds[3])
				self.hass.data[DOMAIN][self._unique_id]['kwh_total'] = float(ds[6])
				await self.hass.data[DOMAIN][self._unique_id]['temp_sensor'].async_update()
				await self.hass.data[DOMAIN][self._unique_id]['kwh_total_sensor'].async_update()
			else:
				self.autarco['power'] = 0
				if(now.day != self._lastUpdate.day):
					self.autarco['extra']['kwh_today'] = 0
				self.autarco['extra']['alterts'] = "offline"



		except requests.exceptions.Timeout:
			pass
			#print("timeout exception on autarco integration")
		except Exception:
			self.exc()


	async def async_update(self):
		"""Fetch new state data for the sensor.
		This is the only method that should fetch new data for Home Assistant.
		"""
		try:
			# first run
			if(self.autarco['extra']['reload_at'] is None):
				await self.get_data()
			# check if we're past reload_at
			elif(self.autarco['extra']['reload_at'] <= datetime.datetime.now(get_localzone())):
				await self.get_data()

			# update states
			self._state_attributes = self.autarco['extra']
			self._state = self.autarco['power']
		except Exception:
			self._state = "error"
			self.exc()


############## TEMP ####################
class autarco_temp_sensor(Entity):
	"""Representation of a Sensor."""

	def __init__(self, hass, config):
		"""Initialize the sensor."""
		self._state = None
		self._name = config.data.get(CONF_NAME)+"_temp"
		self._icon = config.data.get(CONF_ICON)
		self._url = config.data.get(CONF_AUTARCO_URL)
		self._id = self._url.split('.')[-1]

		self.hass = hass
		self._unique_id = config.entry_id
		self.hass.data[DOMAIN][self._unique_id]['temp_sensor'] = self
		self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "autarco_temp_"+str(self._id), hass=hass)

	@property
	def name(self):
		"""Return the name of the sensor."""
		return self._name

	@property
	def unit_of_measurement(self):
		"""Return the unit the value is expressed in."""
		return TEMP_CELSIUS

	@property
	def should_poll(self):
		# No polling needed.
		return False

	@property
	def state(self):
		"""Return the state of the sensor."""
		return self._state

	@property
	def icon(self):
		"""Return the icon to use in the frontend."""
		return self._icon

	async def async_update(self):
		"""Fetch new state data for the sensor.
		This is the only method that should fetch new data for Home Assistant.
		"""
		try:
			self._state = self.hass.data[DOMAIN][self._unique_id]['temp']
			self.async_schedule_update_ha_state()
		except:
			_LOGGER.debug("temp sensor update failed")
			pass

############## kwh_total ####################
class autarco_kwh_total_sensor(Entity):
	"""Representation of a Sensor."""
	def __init__(self, hass, config):
		"""Initialize the sensor."""
		self._state = None
		self._name = config.data.get(CONF_NAME)+"_kwh_total"
		self._icon = config.data.get(CONF_ICON)
		self._url = config.data.get(CONF_AUTARCO_URL)
		self._id = self._url.split('.')[-1]

		self.hass = hass
		self._unique_id = config.entry_id
		self.hass.data[DOMAIN][self._unique_id]['kwh_total_sensor'] = self
		self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "autarco_kwh_total_"+str(self._id), hass=hass)

	@property
	def name(self):
		"""Return the name of the sensor."""
		return self._name

	@property
	def unit_of_measurement(self):
		"""Return the unit the value is expressed in."""
		return ENERGY_KILO_WATT_HOUR

	@property
	def should_poll(self):
		# No polling needed.
		return False

	@property
	def state(self):
		"""Return the state of the sensor."""
		return self._state

	@property
	def icon(self):
		"""Return the icon to use in the frontend."""
		return self._icon

	async def async_update(self):
		"""Fetch new state data for the sensor.
		This is the only method that should fetch new data for Home Assistant.
		"""
		try:
			self._state = self.hass.data[DOMAIN][self._unique_id]['kwh_total']
			self.async_schedule_update_ha_state()
		except:
			_LOGGER.debug("kwh sensor update failed")
			pass
