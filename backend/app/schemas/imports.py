from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional


class ProductImportRequest(BaseModel):
    url: HttpUrl
    source: Optional[str] = Field(default=None, description="Маркетплейс, если известно")


class ProductImportResponse(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    images: List[str] = []
    attributes: Optional[dict] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    product_url: Optional[str] = None
    source: Optional[str] = None


class ReceiptItem(BaseModel):
    name: str
    price: Optional[float] = None
    quantity: Optional[float] = None
    total: Optional[float] = None


class ReceiptImportResponse(BaseModel):
    receipt_id: str
    store: Optional[str] = None
    purchased_at: Optional[str] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    items: List[ReceiptItem] = []
    file_url: Optional[str] = None
    note: Optional[str] = None
