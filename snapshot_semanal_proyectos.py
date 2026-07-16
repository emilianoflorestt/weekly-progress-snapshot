"""
Snapshot semanal de progreso por proyecto.
Frecuencia esperada: Lunes 06:00 AM MX (12:00 UTC).
"""

import os
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# -----------------------------
# Configuración Inicial
# -----------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("snapshot_semanal")

def get_engine():
    """Genera el motor de conexión a la base de datos."""
    USER = os.getenv("MYSQL_USER")
    RAW_PW = os.getenv("MYSQL_PASS")
    HOST  = os.getenv("MYSQL_HOST")
    PORT  = os.getenv("MYSQL_PORT", "3306")
    DB    = os.getenv("MYSQL_DB_WORKS") or os.getenv("MYSQL_DB") 

    if not all([USER, RAW_PW, HOST, PORT, DB]):
        raise RuntimeError("Faltan variables de entorno MySQL para el snapshot")

    PW = quote_plus(RAW_PW)
    DATABASE_URL = f"mysql+pymysql://{USER}:{PW}@{HOST}:{PORT}/{DB}"
    return create_engine(DATABASE_URL)

# -----------------------------
# Lógica Core
# -----------------------------
def run_weekly_snapshot():
    log.info("▶ Iniciando captura del snapshot semanal de proyectos...")
    engine = get_engine()
    
    # NOW() en BD fija la misma marca temporal exacta para todo el bloque.
    # El modelo Wide maneja el NULL de mlProgress explícitamente para Carbono y P3.
    query = text("""
        INSERT INTO project_progress_history (RowID, projectId, weekDate, areaProgress, mlProgress, create_at)
        SELECT 
            UUID(), 
            p.RowID, 
            NOW(), 
            COALESCE(p.areaProgress, 0), 
            CASE 
                WHEN p.businessUnit = 'Soluciones hídricas' THEN COALESCE(p.mlProgress, 0)
                ELSE NULL 
            END, 
            NOW()
        FROM projects p
        WHERE p.status = 'Implementación'
        ON DUPLICATE KEY UPDATE
            areaProgress = VALUES(areaProgress),
            mlProgress = VALUES(mlProgress);
    """)
    
    try:
        with engine.begin() as conn:
            res = conn.execute(query)
            log.info(f"✅ Snapshot semanal completado exitosamente. Filas insertadas/actualizadas: {res.rowcount}")
    except Exception as e:
        log.error(f"❌ Error al ejecutar el snapshot semanal: {e}")
        raise

# -----------------------------
# Entrypoints
# -----------------------------
def main_http(request=None):
    """Entrypoint genérico para Google Cloud Functions (HTTP Trigger)."""
    run_weekly_snapshot()
    return "Snapshot completado", 200

if __name__ == "__main__":
    """Entrypoint para ejecución local o Cloud Run Jobs."""
    run_weekly_snapshot()