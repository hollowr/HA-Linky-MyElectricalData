from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyElectricalDataCoordinator, STATS_STATISTIC_ID

SENSORS = [
    {
        "key": "total_kwh",
        "name": "Linky — Énergie totale",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:transmission-tower",
        "energy_dashboard": True,
    },
    {
        "key": "current_power",
        "name": "Linky — Puissance actuelle",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:lightning-bolt",
    },
    {
        "key": "today_kwh",
        "name": "Linky — Consommation aujourd'hui",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:home-lightning-bolt",
    },
    {
        "key": "yesterday_kwh",
        "name": "Linky — Consommation hier",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:calendar-today",
    },
    {
        "key": "week_kwh",
        "name": "Linky — Consommation semaine",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:calendar-week",
    },
    {
        "key": "max_power_today",
        "name": "Linky — Puissance max aujourd'hui",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge-full",
    },
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: MyElectricalDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(LinkySensor(coordinator, entry, s) for s in SENSORS)


class LinkySensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator: MyElectricalDataCoordinator, entry, sensor_def: dict) -> None:
        super().__init__(coordinator)
        self._key = sensor_def["key"]
        self._attr_name = sensor_def["name"]
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_native_unit_of_measurement = sensor_def["unit"]
        self._attr_device_class = sensor_def["device_class"]
        self._attr_state_class = sensor_def["state_class"]
        self._attr_icon = sensor_def["icon"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.pdl)},
            "name": f"Linky {coordinator.pdl}",
            "manufacturer": "Enedis",
            "model": "Compteur Linky",
        }

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)
