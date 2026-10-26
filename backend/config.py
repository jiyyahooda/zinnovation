import os
from pathlib import Path
from dotenv import load_dotenv
from project_paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / '.env')
db_path = Path(os.getenv('CIVICFLUX_DB', 'var/civicflux.sqlite3'))
DB_PATH = db_path if db_path.is_absolute() else PROJECT_ROOT / db_path
ADMIN_ID = os.getenv('CIVICFLUX_ADMIN_ID', 'ADMIN001')
ADMIN_PASSWORD = os.getenv('CIVICFLUX_ADMIN_PASSWORD', '001')
