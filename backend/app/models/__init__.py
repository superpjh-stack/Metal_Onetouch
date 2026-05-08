import app.core.db_compat  # SQLite 호환 패치 (모델 import 전에 실행)
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.user import User
from app.models.lot import Lot, LotHistory
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.raw_material import RawMaterial
from app.models.process_type import ProcessType
from app.models.equipment import Equipment
from app.models.work_order import WorkOrder, ProcessResult
from app.models.system_log import SystemLog
from app.models.quality import QualityInspection, DefectDetail
from app.models.shipment import Shipment, ShipmentLot
from app.models.ai_agent import AIConversation, AIMessage
from app.models.inbound import RawMaterialReceipt
from app.models.order import Order, OrderItem
from app.models.kpi import KpiTarget
from app.models.file import UploadedFile
from app.models.cad import CadDrawing
from app.models.price_master import ProcessPriceMaster, MaterialPriceMaster
from app.models.quotation import Quotation, QuotationItem
from app.models.annotation import AnnotationTask, AnnotationDataset, TrainingJob, DxfLayerMapping
from app.models.bom import BomHeader, BomItem

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "Lot",
    "LotHistory",
    "Supplier",
    "Customer",
    "RawMaterial",
    "ProcessType",
    "Equipment",
    "WorkOrder",
    "ProcessResult",
    "SystemLog",
    "QualityInspection",
    "DefectDetail",
    "Shipment",
    "ShipmentLot",
    "AIConversation",
    "AIMessage",
    "RawMaterialReceipt",
    "Order",
    "OrderItem",
    "KpiTarget",
    "UploadedFile",
    "CadDrawing",
    "ProcessPriceMaster",
    "MaterialPriceMaster",
    "Quotation",
    "QuotationItem",
    "AnnotationTask",
    "AnnotationDataset",
    "TrainingJob",
    "DxfLayerMapping",
    "BomHeader",
    "BomItem",
]
