import uuid
from pathlib import Path
from datetime import datetime
from io import BytesIO
import re

import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.schemas.imports import (
    ProductImportRequest,
    ProductImportResponse,
    ReceiptImportResponse,
    ReceiptItem,
)
from app.services.imports.product_fetcher import fetch_public_product
from app.core.config import settings

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/product-link", response_model=ProductImportResponse)
async def import_product_link(payload: ProductImportRequest):
    data = await fetch_public_product(str(payload.url))
    if not data:
        raise HTTPException(status_code=400, detail="Не удалось вытащить данные со страницы товара")
    return ProductImportResponse(**data, source=payload.source, product_url=str(payload.url))


@router.post("/receipt", response_model=ReceiptImportResponse)
async def import_receipt(
    file: UploadFile = File(...),
    workspace_id: int = Form(2),
    scope: str = Form("private"),
):
    content = await file.read()
    ext = Path(file.filename or "").suffix.lower() or ".bin"
    receipt_id = str(uuid.uuid4())
    base = Path(settings.media_private_path if scope == "private" else settings.media_public_path)
    target_dir = base / "receipts" / datetime.utcnow().strftime("%Y%m%d")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{receipt_id}{ext}"

    async with aiofiles.open(target_path, "wb") as out:
        await out.write(content)

    text = ""
    if "pdf" in (file.content_type or "") or ext == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            text = ""

    def _parse_receipt_text(raw: str):
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        note = None
        if lines and lines[0].lower().startswith("кассовый чек"):
            note = lines[0]
        # дата/время
        m_dt = re.search(r"(\d{2}\.\d{2}\.\d{4}[ T]\d{2}:\d{2})", raw)
        purchased_at = m_dt.group(1).replace(" ", "T") if m_dt else None
        # сумма итог
        m_total = re.findall(r"(\d+[.,]\d{2})", raw)
        total = None
        if m_total:
            try:
                total = float(m_total[-1].replace(",", "."))
            except Exception:
                total = None
        currency = "RUB" if total is not None else None
        # магазин / продавец
        store_name = None
        vendor = None
        for ln in lines:
            low = ln.lower()
            if "ozon" in low and not store_name:
                store_name = ln
            if "ооо" in low and not store_name:
                store_name = ln
            if "technology" in low or "ltd" in low:
                vendor = ln
        # парсинг позиций
        items: list[ReceiptItem] = []
        last_name = None
        price_line_re = re.compile(r"(\d+[.,]?\d*)\s*[xх]\s*(\d+[.,]\d{2})")
        for ln in lines:
            if re.match(r"^\d+\.$", ln):
                last_name = None
                continue
            m_price = price_line_re.search(ln)
            if m_price and last_name:
                qty = float(m_price.group(1).replace(",", "."))
                price_val = float(m_price.group(2).replace(",", "."))
                items.append(ReceiptItem(name=last_name, price=price_val, quantity=qty, total=price_val * qty))
                last_name = None
                continue
            # длинные строки считаем названием товара
            if len(ln) > 15 and not any(ch.isdigit() for ch in ln[:4]):
                last_name = ln
        if not items and last_name:
            items.append(ReceiptItem(name=last_name, price=total, quantity=1, total=total))
        return note, store_name, vendor, purchased_at, total, currency, items

    note, store, vendor, purchased_at, total, currency, items = _parse_receipt_text(text) if text else (None, None, None, None, None, None, [])
    if vendor and not store:
        store = vendor
    elif vendor:
        note = f"{note or ''} {vendor}".strip()

    file_url = f"/api/v1/media/file/{receipt_id}"
    return ReceiptImportResponse(
        receipt_id=receipt_id,
        store=store,
        purchased_at=purchased_at,
        total=total,
        currency=currency,
        items=items,
        file_url=file_url,
        note=note or "Чек сохранён. Парсинг ограничен (без OCR); при необходимости скорректируйте данные вручную.",
    )
