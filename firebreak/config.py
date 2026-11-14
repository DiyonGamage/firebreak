from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_PSI = RAW / "psi"
RAW_META = RAW / "psi_meta"
RAW_NTRS = RAW / "ntrs"
PROCESSED = DATA / "processed"
DB_PATH = PROCESSED / "firebreak.sqlite"

PSI_BASE = "https://psi.nasa.gov"
PSI_META = PSI_BASE + "/geode-py/ws/repo/investigations/{acc}"
PSI_DOWNLOAD = (
    PSI_BASE
    + "/geode-py/ws/studies/{acc}/download?file={fid}&version=1&redirect=false"
)
PSI_PAGE = PSI_BASE + "/physci/repo/data/investigations/{acc}"

NTRS_SITE = "https://ntrs.nasa.gov"
NTRS_API = NTRS_SITE + "/api/citations"
