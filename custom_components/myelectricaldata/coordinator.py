import logging
from datetime import date, timedelta, datetime, timezone

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import UnitOfEnergy

from .const import DOMAIN, API_BASE

_LOGGER = logging.getLogger(__name__)

STATS_STATISTIC_ID = f"{DOMAIN}:linky_energy_total"


class MyElectricalDataCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, pdl: str, token: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )
        self.pdl = pdl
        self.token = token
        self._history_injected = False

    async def _fetch(self, session: aiohttp.ClientSession, path: str) -> dict:
        url = f"{API_BASE}/{path}"
        async with session.get(
            url,
            headers={"Authorization": self.token},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"Erreur API {resp.status} — {url}")
            return await resp.json()

    async def _async_update_data(self) -> dict:
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        try:
            async with aiohttp.ClientSession() as session:
                # Full history for cumulative total + statistics injection
                history_start = date(2025, 1, 1)
                daily_all = await self._fetch(
                    session,
                    f"daily_consumption/{self.pdl}/start/{history_start}/end/{today}",
                )
                curve = await self._fetch(
                    session,
                    f"consumption_load_curve/{self.pdl}/start/{yesterday}/end/{today}",
                )
                maxpow = await self._fetch(
                    session,
                    f"daily_consumption_max_power/{self.pdl}/start/{week_ago}/end/{today}",
                )
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Erreur connexion: {err}") from err

        # Build daily dict (Wh → kWh)
        daily_by_date = {
            r["date"][:10]: round(int(r["value"]) / 1000, 2)
            for r in daily_all.get("meter_reading", {}).get("interval_reading", [])
        }

        # Cumulative total (always increasing)
        cumulative = 0.0
        cumulative_by_date = {}
        for d in sorted(daily_by_date):
            cumulative = round(cumulative + daily_by_date[d], 2)
            cumulative_by_date[d] = cumulative

        # Max power by date
        max_by_date = {
            r["date"][:10]: int(r["value"])
            for r in maxpow.get("meter_reading", {}).get("interval_reading", [])
        }

        # Current power = latest load curve reading
        lc_readings = curve.get("meter_reading", {}).get("interval_reading", [])
        current_power = int(lc_readings[-1]["value"]) if lc_readings else 0

        # Inject historical statistics once
        if not self._history_injected:
            await self._inject_statistics(cumulative_by_date)
            self._history_injected = True

        return {
            "today_kwh":       daily_by_date.get(str(today), daily_by_date.get(str(yesterday), 0.0)),
            "yesterday_kwh":   daily_by_date.get(str(yesterday), 0.0),
            "week_kwh":        round(sum(v for k, v in daily_by_date.items() if k >= str(week_ago)), 2),
            "current_power":   current_power,
            "max_power_today": max_by_date.get(str(today), max_by_date.get(str(yesterday), 0)),
            "total_kwh":       cumulative_by_date.get(str(yesterday), 0.0),
            "daily_history":   daily_by_date,
        }

    async def _inject_statistics(self, cumulative_by_date: dict) -> None:
        """Inject daily statistics into HA recorder for Energy Dashboard."""
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Linky — Énergie totale",
            source=DOMAIN,
            statistic_id=STATS_STATISTIC_ID,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )

        statistics = []
        for day_str in sorted(cumulative_by_date):
            dt = datetime.fromisoformat(day_str).replace(
                hour=23, minute=0, second=0, tzinfo=timezone.utc
            )
            statistics.append(
                StatisticData(
                    start=dt,
                    sum=cumulative_by_date[day_str],
                )
            )

        async_add_external_statistics(self.hass, metadata, statistics)
        _LOGGER.info("Linky: %d jours d'historique injectés dans les statistiques HA", len(statistics))
