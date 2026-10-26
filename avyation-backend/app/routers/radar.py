"""Free ADS-B radar proxy for Avyation.

Uses the community Open Data endpoint from adsb.fi. No API key is required.
Aircraft positions are not flight-status or disruption data.
"""
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/radar", tags=["Flight Radar"])


ADSBFI_BASE = "https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{radius}"
REQUEST_TIMEOUT_SECONDS = 12.0


@router.get("/aircraft")
async def radar_aircraft(
    lat: float = Query(28.6139, ge=-90, le=90),
    lon: float = Query(77.2090, ge=-180, le=180),
    radius: int = Query(150, ge=10, le=250, description="Search radius in nautical miles"),
) -> dict[str, Any]:
    """Return normalized aircraft positions around a map centre."""
    url = ADSBFI_BASE.format(lat=lat, lon=lon, radius=radius)
    headers = {
        "User-Agent": "AvyationStudentProject/1.0 (flight-operations radar demo)",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Aircraft data provider returned HTTP {exc.response.status_code}. Try again later.",
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve aircraft data from the upstream provider.",
        ) from exc

    aircraft = []
    raw_aircraft = payload.get("ac") or payload.get("aircraft") or []
    for item in raw_aircraft:
        if item.get("lat") is None or item.get("lon") is None:
            continue
        aircraft.append({
            "hex": item.get("hex"),
            "callsign": (item.get("flight") or "").strip() or "Unknown callsign",
            "latitude": item.get("lat"),
            "longitude": item.get("lon"),
            "altitude_ft": item.get("alt_baro"),
            "ground_speed_kt": item.get("gs"),
            "track_deg": item.get("track"),
            "vertical_rate_fpm": item.get("baro_rate"),
            "last_seen_seconds": item.get("seen"),
            "aircraft_type": item.get("t"),
            "registration": item.get("r"),
            "on_ground": item.get("alt_baro") == "ground",
        })

    return {
        "source": "adsb.fi Open Data",
        "is_live_feed": True,
        "center": {"lat": lat, "lon": lon},
        "radius_nm": radius,
        "count": len(aircraft),
        "raw_count": len(raw_aircraft),
        "aircraft": aircraft,
        "provider_timestamp": payload.get("now"),
        "note": "ADS-B positions reflect aircraft received by the provider; they do not establish delay, cancellation, or compensation eligibility.",
    }
