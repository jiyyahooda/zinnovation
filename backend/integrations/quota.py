"""Persist request accounting in the existing SQLite database; count actual attempts."""
import os
from datetime import datetime,timezone
from backend.db.connection import connection

def reserve(provider='tomtom'):
    now=datetime.now(timezone.utc);month=now.strftime('%Y-%m');day=now.strftime('%Y-%m-%d')
    monthly=int(os.getenv('CIVICFLUX_TOMTOM_MONTHLY_LIMIT','18000'));daily=int(os.getenv('CIVICFLUX_TOMTOM_DAILY_LIMIT','600'))
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS provider_usage(provider TEXT,period TEXT,n INTEGER,PRIMARY KEY(provider,period))')
        db.execute('BEGIN IMMEDIATE')
        for period,limit in [(month,monthly),(day,daily)]:
            row=db.execute('SELECT n FROM provider_usage WHERE provider=? AND period=?',(provider,period)).fetchone()
            if row and row['n']>=limit:return False
        for period in [month,day]:db.execute('INSERT INTO provider_usage VALUES (?,?,1) ON CONFLICT(provider,period) DO UPDATE SET n=n+1',(provider,period))
    return True
