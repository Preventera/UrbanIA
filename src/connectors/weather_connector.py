"""
=============================================================================
Connecteur Météo Canada — Source #6, Couche 3
=============================================================================
Récupère les conditions météo actuelles et prévisions pour Montréal
depuis l'API d'Environnement Canada (api.weather.gc.ca).

Impact sur le scoring UrbanIA:
- Pluie: ×1.2 (surfaces glissantes autour chantiers)
- Verglas: ×1.4 (risque chute piétons/cyclistes)
- Tempête neige: ×1.3 (visibilité réduite)
- Vent fort >60km/h: ×1.3 (risque chute objets chantier)
- Canicule: ×1.1 (fatigue travailleurs → erreurs)
=============================================================================
"""

import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Station météo Montréal (Pierre-Elliott-Trudeau)
MTL_STATION = "s0000635"
WEATHER_API_BASE = "https://dd.weather.gc.ca/citypage_weather/xml/QC"


@dataclass
class WeatherCondition:
    """Conditions météo actuelles"""
    temperature: float = 0.0
    condition: str = "Inconnu"         # Ensoleillé, Nuageux, Pluie, Neige, etc.
    wind_speed: float = 0.0            # km/h
    wind_gust: float = 0.0             # km/h
    humidity: float = 0.0              # %
    visibility: float = 10.0           # km
    precipitation: float = 0.0         # mm
    feels_like: float = 0.0
    timestamp: str = ""
    risk_factor: float = 1.0           # Facteur de risque météo (1.0 = normal)
    risk_reason: str = ""


class WeatherConnector:
    """
    Connecteur pour les données météo d'Environnement Canada.
    Source #6 de la Couche 3 UrbanIA.
    """

    SOURCE_ID = "meteo"
    SOURCE_NAME = "Météo Canada"
    COUCHE = 3
    REFRESH = "horaire"

    # Facteurs de risque par condition météo
    RISK_FACTORS = {
        "verglas": 1.4,
        "pluie verglaçante": 1.4,
        "freezing rain": 1.4,
        "tempête": 1.3,
        "blizzard": 1.3,
        "neige forte": 1.3,
        "heavy snow": 1.3,
        "pluie forte": 1.2,
        "heavy rain": 1.2,
        "pluie": 1.15,
        "rain": 1.15,
        "neige": 1.15,
        "snow": 1.15,
        "brouillard": 1.15,
        "fog": 1.15,
        "orage": 1.2,
        "thunderstorm": 1.2,
    }

    def __init__(self):
        self._current: Optional[WeatherCondition] = None
        self._last_fetch: Optional[datetime] = None
        logger.info("🌤️ WeatherConnector initialisé")

    async def fetch_current(self) -> WeatherCondition:
        """Récupère les conditions météo actuelles pour Montréal."""
        # Cache de 30 minutes
        if self._current and self._last_fetch:
            age = (datetime.now() - self._last_fetch).total_seconds()
            if age < 1800:
                return self._current

        logger.info("🌤️ Récupération météo Montréal...")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Essayer l'API XML d'Environnement Canada
                url = f"{WEATHER_API_BASE}/{MTL_STATION}_f.xml"
                resp = await client.get(url)

                if resp.status_code == 200:
                    self._current = self._parse_xml(resp.text)
                else:
                    # Fallback avec des données simulées raisonnables
                    logger.warning(f"  ⚠️ API météo indisponible ({resp.status_code}), utilisation valeurs par défaut")
                    self._current = self._get_default_conditions()

        except Exception as e:
            logger.warning(f"  ⚠️ Erreur météo: {e}, utilisation valeurs par défaut")
            self._current = self._get_default_conditions()

        self._current.risk_factor = self._compute_risk_factor(self._current)
        self._last_fetch = datetime.now()
        self._current.timestamp = self._last_fetch.isoformat()

        logger.info(
            f"  🌡️ {self._current.temperature}°C | {self._current.condition} | "
            f"Vent {self._current.wind_speed} km/h | Risque ×{self._current.risk_factor}"
        )

        return self._current

    def get_risk_factor(self) -> Dict[str, Any]:
        """Retourne le facteur de risque météo pour le scoring UrbanIA."""
        if not self._current:
            return {"weather_factor": 1.0, "condition": "Inconnu", "source": self.SOURCE_ID}

        return {
            "weather_factor": self._current.risk_factor,
            "condition": self._current.condition,
            "temperature": self._current.temperature,
            "wind_speed": self._current.wind_speed,
            "risk_reason": self._current.risk_reason,
            "source": self.SOURCE_ID,
        }

    def _compute_risk_factor(self, weather: WeatherCondition) -> float:
        """Calcule le facteur de risque basé sur les conditions."""
        factor = 1.0
        reasons = []

        # Condition textuelle
        condition_lower = weather.condition.lower()
        for key, f in self.RISK_FACTORS.items():
            if key in condition_lower:
                factor = max(factor, f)
                reasons.append(key)
                break

        # Vent fort (>60 km/h = risque chute objets chantier)
        if weather.wind_speed >= 80:
            factor = max(factor, 1.4)
            reasons.append(f"vent très fort ({weather.wind_speed} km/h)")
        elif weather.wind_speed >= 60:
            factor = max(factor, 1.3)
            reasons.append(f"vent fort ({weather.wind_speed} km/h)")

        # Visibilité réduite (<2 km)
        if weather.visibility < 1:
            factor = max(factor, 1.3)
            reasons.append(f"visibilité très réduite ({weather.visibility} km)")
        elif weather.visibility < 2:
            factor = max(factor, 1.15)
            reasons.append(f"visibilité réduite ({weather.visibility} km)")

        # Température extrême
        if weather.temperature < -25:
            factor = max(factor, 1.2)
            reasons.append(f"froid extrême ({weather.temperature}°C)")
        elif weather.temperature > 35:
            factor = max(factor, 1.1)
            reasons.append(f"canicule ({weather.temperature}°C)")

        weather.risk_reason = "; ".join(reasons) if reasons else "conditions normales"
        return round(factor, 2)

    def _parse_xml(self, xml_text: str) -> WeatherCondition:
        """Parse le XML d'Environnement Canada (simplifié)."""
        import re

        def extract(pattern, text, default=""):
            m = re.search(pattern, text)
            return m.group(1) if m else default

        try:
            temp = float(extract(r'<temperature.*?unitType="metric".*?>([-\d.]+)', xml_text, "0"))
            condition = extract(r'<condition>(.*?)</condition>', xml_text, "Inconnu")
            wind = float(extract(r'<speed.*?unitType="metric".*?>([\d.]+)', xml_text, "0"))
            humidity = float(extract(r'<relativeHumidity.*?>([\d.]+)', xml_text, "50"))
            visibility = float(extract(r'<visibility.*?unitType="metric".*?>([\d.]+)', xml_text, "10"))

            return WeatherCondition(
                temperature=temp,
                condition=condition,
                wind_speed=wind,
                humidity=humidity,
                visibility=visibility,
            )
        except Exception as e:
            logger.warning(f"  ⚠️ Erreur parsing XML: {e}")
            return self._get_default_conditions()

    @staticmethod
    def _get_default_conditions() -> WeatherCondition:
        """Conditions par défaut (temps normal)."""
        month = datetime.now().month
        # Températures saisonnières approximatives Montréal
        seasonal_temp = {1: -10, 2: -8, 3: -2, 4: 6, 5: 14, 6: 20, 7: 23, 8: 22, 9: 17, 10: 9, 11: 2, 12: -6}
        return WeatherCondition(
            temperature=seasonal_temp.get(month, 10),
            condition="Partiellement nuageux",
            wind_speed=15,
            humidity=60,
            visibility=10,
        )
