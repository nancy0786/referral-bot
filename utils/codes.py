# utils/codes.py
import json, re, time
from pathlib import Path
from typing import Optional, Dict, Any
import aiofiles

CODES_PATH = Path(__file__).resolve().parent.parent / "data" / "codes.json"
CODES_PATH.parent.mkdir(parents=True, exist_ok=True)

# Code format: exactly 16 chars, A-Z and 0-9
CODE_RE = re.compile(r"^[A-Z0-9]{16}$")

async def _ensure_file():
    if not CODES_PATH.exists():
        async with aiofiles.open(CODES_PATH, "w", encoding="utf-8") as f:
            await f.write(json.dumps({"codes": {}}, ensure_ascii=False, indent=2))

async def _read_all() -> Dict[str, Any]:
    await _ensure_file()
    async with aiofiles.open(CODES_PATH, "r", encoding="utf-8") as f:
        raw = await f.read()
    try:
        data = json.loads(raw)
    except Exception:
        data = {"codes": {}}
    if "codes" not in data:
        data["codes"] = {}
    return data

async def _write_all(data: Dict[str, Any]) -> None:
    async with aiofiles.open(CODES_PATH, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

async def get_code_info(code: str) -> Optional[Dict[str, Any]]:
    """
    Returns a dict like:
    {
      "reward": {"credits": 25}  OR  {"plan": {"name":"Premium","days":30}},
      "used_by": 123456789 or null,
      "used_at": 1720000000 or null
    }
    """
    code = code.upper().strip()
    if not CODE_RE.match(code):
        return None
    data = await _read_all()
    return data["codes"].get(code)

async def mark_code_used(code: str, user_id: int) -> None:
    code = code.upper().strip()
    data = await _read_all()
    if code in data["codes"]:
        data["codes"][code]["used_by"] = user_id
        data["codes"][code]["used_at"] = int(time.time())
        await _write_all(data)

async def add_code(code: str, reward: Dict[str, Any]) -> bool:
    """
    Admin creation helper (will be wired in Step 11).
    Returns True if added, False if invalid or already exists.
    """
    code = code.upper().strip()
    if not CODE_RE.match(code):
        return False
    data = await _read_all()
    if code in data["codes"]:
        return False
    data["codes"][code] = {"reward": reward, "used_by": None, "used_at": None}
    await _write_all(data)
    return True
