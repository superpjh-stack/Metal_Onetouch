"""DXF/DWG 파싱 서비스 — ezdxf 기반 CAD 객체 추출"""
import fnmatch
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import DxfLayerMapping


YOLO_CLASS_MAP = {"hole": 0, "bend": 1, "cut": 2, "weld": 3, "slot": 4}

_DEFAULT_MAPPINGS = [
    {"layer_pattern": "HOLE*",  "process_type": "drilling", "priority": 10},
    {"layer_pattern": "DRILL*", "process_type": "drilling", "priority": 9},
    {"layer_pattern": "BEND*",  "process_type": "bending",  "priority": 10},
    {"layer_pattern": "FOLD*",  "process_type": "bending",  "priority": 9},
    {"layer_pattern": "CUT*",   "process_type": "cutting",  "priority": 10},
    {"layer_pattern": "*SLOT*", "process_type": "cutting",  "priority": 8},
    {"layer_pattern": "WELD*",  "process_type": "welding",  "priority": 10},
]

_PROCESS_TO_OBJ_TYPE = {
    "drilling": "hole",
    "bending":  "bend",
    "cutting":  "cut",
    "welding":  "weld",
}


class DxfParserService:
    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self._db = db
        self._mappings: Optional[list[dict]] = None

    async def _load_mappings(self) -> list[dict]:
        if self._mappings is not None:
            return self._mappings
        if self._db is not None:
            rows = (await self._db.execute(
                select(DxfLayerMapping)
                .where(DxfLayerMapping.is_active == True)
                .order_by(DxfLayerMapping.priority.desc())
            )).scalars().all()
            if rows:
                self._mappings = [
                    {"layer_pattern": r.layer_pattern, "process_type": r.process_type, "priority": r.priority}
                    for r in rows
                ]
                return self._mappings
        self._mappings = sorted(_DEFAULT_MAPPINGS, key=lambda x: x["priority"], reverse=True)
        return self._mappings

    def _match_layer(self, layer_name: str, mappings: list[dict]) -> Optional[str]:
        upper = layer_name.upper()
        for m in mappings:
            if fnmatch.fnmatch(upper, m["layer_pattern"].upper()):
                return _PROCESS_TO_OBJ_TYPE.get(m["process_type"], "cut")
        return None

    def _extract_circles(self, msp, mappings: list[dict]) -> list[dict]:
        objects = []
        try:
            for entity in msp:
                if entity.dxftype() == "CIRCLE":
                    layer = entity.dxf.layer or ""
                    obj_type = self._match_layer(layer, mappings) or "hole"
                    diameter = round(entity.dxf.radius * 2, 4)
                    center = entity.dxf.center
                    objects.append({
                        "type": obj_type,
                        "diameter": diameter,
                        "count": 1,
                        "x": round(float(center.x), 4),
                        "y": round(float(center.y), 4),
                        "layer": layer,
                    })
        except Exception:
            pass
        # 동일 레이어+직경 그룹 집계
        grouped: dict[tuple, dict] = {}
        for obj in objects:
            key = (obj["layer"], obj.get("diameter", 0))
            if key in grouped:
                grouped[key]["count"] += 1
            else:
                grouped[key] = dict(obj)
        return list(grouped.values())

    def _extract_lines(self, msp, mappings: list[dict]) -> list[dict]:
        objects = []
        try:
            for entity in msp:
                if entity.dxftype() in ("LINE", "LWPOLYLINE", "POLYLINE"):
                    layer = entity.dxf.layer or ""
                    obj_type = self._match_layer(layer, mappings) or "cut"
                    if obj_type not in ("cut", "weld", "slot"):
                        continue
                    length = 0.0
                    if entity.dxftype() == "LINE":
                        start = entity.dxf.start
                        end = entity.dxf.end
                        length = round(((end.x - start.x)**2 + (end.y - start.y)**2) ** 0.5, 4)
                    elif hasattr(entity, "length"):
                        try:
                            length = round(float(entity.length()), 4)
                        except Exception:
                            pass
                    if length > 0:
                        objects.append({
                            "type": obj_type,
                            "length": length,
                            "count": 1,
                            "layer": layer,
                        })
        except Exception:
            pass
        return objects

    def _extract_arcs(self, msp, mappings: list[dict]) -> list[dict]:
        objects = []
        try:
            for entity in msp:
                if entity.dxftype() == "ARC":
                    layer = entity.dxf.layer or ""
                    obj_type = self._match_layer(layer, mappings) or "bend"
                    if obj_type != "bend":
                        continue
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    angle = end_angle - start_angle
                    if angle < 0:
                        angle += 360
                    radius = round(entity.dxf.radius, 4)
                    objects.append({
                        "type": "bend",
                        "angle": round(angle, 2),
                        "radius": radius,
                        "count": 1,
                        "layer": layer,
                    })
        except Exception:
            pass
        return objects

    def _infer_dimensions(self, msp) -> dict:
        try:
            import ezdxf
            min_x = min_y = float("inf")
            max_x = max_y = float("-inf")
            for entity in msp:
                if entity.dxftype() in ("LINE", "CIRCLE", "ARC", "LWPOLYLINE"):
                    try:
                        bbox = entity.get_bounding_box()
                        if bbox:
                            min_x = min(min_x, bbox.extmin.x)
                            min_y = min(min_y, bbox.extmin.y)
                            max_x = max(max_x, bbox.extmax.x)
                            max_y = max(max_y, bbox.extmax.y)
                    except Exception:
                        pass
            if min_x < float("inf"):
                return {
                    "length": round(max_x - min_x, 4),
                    "width": round(max_y - min_y, 4),
                    "thickness": 0.0,
                }
        except Exception:
            pass
        return {"length": 0.0, "width": 0.0, "thickness": 0.0}

    async def parse(self, file_bytes: bytes) -> dict:
        """DXF 바이트 → parsed_objects 표준 JSON 구조"""
        import io
        import ezdxf

        try:
            doc = ezdxf.read(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
        except Exception:
            try:
                doc = ezdxf.read(io.StringIO(file_bytes.decode("latin-1", errors="replace")))
            except Exception as exc:
                return {
                    "objects": [],
                    "dimensions": {"length": 0.0, "width": 0.0, "thickness": 0.0},
                    "layers": [],
                    "material_hint": None,
                    "confidence": 0.0,
                    "source": "dxf",
                    "error": str(exc),
                }

        mappings = await self._load_mappings()
        msp = doc.modelspace()

        objects = (
            self._extract_circles(msp, mappings)
            + self._extract_lines(msp, mappings)
            + self._extract_arcs(msp, mappings)
        )

        layers = list({e.dxf.layer for e in msp if hasattr(e, "dxf") and hasattr(e.dxf, "layer")})
        dimensions = self._infer_dimensions(msp)

        return {
            "objects": objects,
            "dimensions": dimensions,
            "layers": layers,
            "material_hint": None,
            "confidence": 1.0,
            "source": "dxf",
        }
