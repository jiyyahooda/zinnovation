"""Configured CPCB JSON gateway; normalization verifies source and station."""
import os
import httpx

async def fetch():
    url=os.getenv('CIVICFLUX_CPCB_URL')
    if not url: return None
    async with httpx.AsyncClient(timeout=10,follow_redirects=False) as client:
        response=await client.get(url);response.raise_for_status();return response.json()
