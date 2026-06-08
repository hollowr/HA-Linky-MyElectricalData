import logging
import json
import os
from datetime import date, timedelta, datetime, timezone

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
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
            update_interval=timedelta(hours=6),
        )
        self.pdl = pdl
        self.token = token
        self._hass = hass
        self._history_injected = False
        self._daily_cache = {}
        self._daily_cache_date = None
        self._last_data = None
        self._history_cache_file = os.path.join(
            hass.config.path(".storage"), f"myelectricaldata_history_{pdl}.json"
        )
        self._load_local_history_cache()

    def _load_local_history_cache(self) -> None:
        """Load historical data from local cache file."""
        if os.path.exists(self._history_cache_file):
            try:
                with open(self._history_cache_file, "r") as f:
                    data = json.load(f)
                    self._daily_cache = data.get("daily", {})
                    self._history_injected = data.get("injected", False)
                    _LOGGER.debug(f"Loaded {len(self._daily_cache)} days from local cache")
            except Exception as err:
                _LOGGER.warning(f"Failed to load history cache: {err}")

    def _save_local_history_cache(self) -> None:
        """Save historical data to local cache file."""
        try:
            with open(self._history_cache_file, "w") as f:
                json.dump(
                    {"daily": self._daily_cache, "injected": self._history_injected},
                    f,
                )
        except Exception as err:
            _LOGGER.warning(f"Failed to save history cache: {err}")

    async def _fetch(self, session: aiohttp.ClientSession, path: str) -> dict:
        """Fetch data from MyElectricalData API."""
        url = f"{API_BASE}/{path}"
        async with session.get(
            url,
            headers={"Authorization": self.token},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 409:
                raise QuotaExceededError("Quota journalier dépassé — réessai demain")
            if resp.status != 200:
                raise UpdateFailed(f"Erreur API {resp.status} — {url}")
            return await resp.json()

    async def _async_update_data(self) -> dict:
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch only recent daily data (last 8 days) to minimize API quota usage
                recent_start = today - timedelta(days=8)
                if self._daily_cache_date != today:
                    daily_recent = await self._fetch(
                        session,
                        f"daily_consumption/{self.pdl}/start/{recent_start}/end/{today}",
                    )
                    # Update cache with recent data
                    recent_daily = {
                        r["date"][:10]: round(int(r["value"]) / 1000, 2)
                        for r in daily_recent.get("meter_reading", {}).get("interval_reading", [])
                    }
                    self._daily_cache.update(recent_daily)
                    self._daily_cache_date = today
                    self._save_local_history_cache()

                # Load curve for current power and max today
                curve = await self._fetch(
                    session,
                    f"consumption_load_curve/{self.pdl}/start/{yesterday}/end/{today}",
                )

        except QuotaExceededError as err:
            _LOGGER.warning("MyElectricalData: %s", err)
            if self._last_data:
                return self._last_data
            raise UpdateFailed(str(err)) from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Erreur connexion: {err}") from err

        # Use cached daily data
        daily_by_date = self._daily_cache

        # Calculate cumulative total from all cached data
        cumulative = 0.0
        cumulative_by_date = {}
        for d in sorted(daily_by_date):
            cumulative = round(cumulative + daily_by_date[d], 2)
            cumulative_by_date[d] = cumulative

        # Current power = latest load curve reading
        lc_readings = curve.get("meter_reading", {}).get("interval_reading", [])
        current_power = int(lc_readings[-1]["value"]) if lc_readings else 0

        # Inject historical statistics once (persisted to file)
        if not self._history_injected:
            await self._inject_statistics(cumulative_by_date)
            self._history_injected = True
            self._save_local_history_cache()

        data = {
            "today_kwh":       daily_by_date.get(str(today), daily_by_date.get(str(yesterday), 0.0)),
            "yesterday_kwh":   daily_by_date.get(str(yesterday), 0.0),
            "week_kwh":        round(sum(v for k, v in daily_by_date.items() if k >= str(week_ago)), 2),
            "current_power":   current_power,
            "max_power_today": max((int(r["value"]) for r in lc_readings), default=0),
            "total_kwh":       cumulative_by_date.get(str(yesterday), 0.0),
            "daily_history":   daily_by_date,
        }
        self._last_data = data
        return data

    async def _inject_statistics(self, cumulative_by_date: dict) -> None:
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Linky — Énergie totale",
            source=DOMAIN,
            statistic_id=STATS_STATISTIC_ID,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )

        statistics = [
            StatisticData(
                start=datetime.fromisoformat(day_str).replace(
                    hour=23, minute=0, second=0, tzinfo=timezone.utc
                ),
                sum=kwh,
            )
            for day_str, kwh in sorted(cumulative_by_date.items())
        ]

        async_add_external_statistics(self.hass, metadata, statistics)
        _LOGGER.info("Linky: %d jours injectés dans les statistiques HA", len(statistics))


class QuotaExceededError(Exception):
    pass
