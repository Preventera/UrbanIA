"""
=============================================================================
Connecteur Données Ouvertes Montréal — Base
=============================================================================
Client HTTP asynchrone pour l'API CKAN de donnees.montreal.ca
Utilisé par tous les connecteurs Couche 3 (CIFS, piétons, vélos, etc.)

API: https://donnees.montreal.ca/api/3/action/
=============================================================================
"""

import logging
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

MTL_API_BASE = "https://donnees.montreal.ca/api/3/action"


class MTLOpenDataClient:
    """
    Client pour l'API de données ouvertes de Montréal.
    Supporte CKAN datastore_search et package_show.
    """

    def __init__(self, cache_dir: str = "./data/mtl_sources"):
        self.base_url = MTL_API_BASE
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("🏙️ MTLOpenDataClient initialisé")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # =========================================================================
    # API CALLS
    # =========================================================================

    async def datastore_search(
        self,
        resource_id: str,
        filters: Optional[Dict] = None,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Recherche dans un datastore CKAN.
        
        Args:
            resource_id: ID de la ressource CKAN
            filters: Filtres clé-valeur
            limit: Nombre max de résultats
            offset: Décalage pour pagination
            sort: Champ de tri (ex: "date desc")
            fields: Liste des champs à retourner
        """
        client = await self._get_client()
        params = {
            "resource_id": resource_id,
            "limit": limit,
            "offset": offset,
        }
        if filters:
            params["filters"] = json.dumps(filters)
        if sort:
            params["sort"] = sort
        if fields:
            params["fields"] = ",".join(fields)

        try:
            resp = await client.get(f"{self.base_url}/datastore_search", params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("success"):
                result = data["result"]
                logger.debug(
                    f"  📦 {resource_id[:12]}... → {len(result.get('records', []))} "
                    f"enregistrements (total: {result.get('total', '?')})"
                )
                return result
            else:
                logger.error(f"  ❌ API error: {data.get('error')}")
                return {"records": [], "total": 0}

        except httpx.HTTPStatusError as e:
            logger.error(f"  ❌ HTTP {e.response.status_code}: {e}")
            return {"records": [], "total": 0}
        except Exception as e:
            logger.error(f"  ❌ Erreur: {e}")
            return {"records": [], "total": 0}

    async def package_show(self, package_id: str) -> Dict[str, Any]:
        """Récupère les métadonnées d'un dataset."""
        client = await self._get_client()
        try:
            resp = await client.get(
                f"{self.base_url}/package_show", params={"id": package_id}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}) if data.get("success") else {}
        except Exception as e:
            logger.error(f"  ❌ package_show({package_id}): {e}")
            return {}

    async def fetch_all_records(
        self,
        resource_id: str,
        filters: Optional[Dict] = None,
        batch_size: int = 1000,
        max_records: int = 50000,
    ) -> List[Dict]:
        """Récupère tous les enregistrements par pagination."""
        all_records = []
        offset = 0

        while offset < max_records:
            result = await self.datastore_search(
                resource_id, filters=filters, limit=batch_size, offset=offset
            )
            records = result.get("records", [])
            if not records:
                break

            all_records.extend(records)
            offset += len(records)

            total = result.get("total", 0)
            if offset >= total:
                break

        logger.info(f"  📊 Total récupéré: {len(all_records)} enregistrements")
        return all_records

    # =========================================================================
    # CACHE
    # =========================================================================

    def save_cache(self, key: str, data: Any):
        """Sauvegarde des données en cache local."""
        path = self.cache_dir / f"{key}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "data": data}, f, ensure_ascii=False)
        logger.debug(f"  💾 Cache sauvé: {key}")

    def load_cache(self, key: str, max_age_minutes: int = 60) -> Optional[Any]:
        """Charge des données depuis le cache si pas trop vieilles."""
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            ts = datetime.fromisoformat(cached["timestamp"])
            age = (datetime.now() - ts).total_seconds() / 60

            if age > max_age_minutes:
                logger.debug(f"  ⏰ Cache expiré: {key} ({age:.0f} min)")
                return None

            logger.debug(f"  ✅ Cache valide: {key} ({age:.0f} min)")
            return cached["data"]
        except Exception:
            return None
