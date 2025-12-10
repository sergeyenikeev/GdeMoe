import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import httpx


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: Dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        attr_dict = dict(attrs)
        key = attr_dict.get("property") or attr_dict.get("name")
        val = attr_dict.get("content")
        if key and val:
            self.meta[key.lower()] = val


def _parse_ld_json_blocks(html: str) -> List[Dict[str, Any]]:
    blocks = re.findall(
        r'<script[^>]*type=["\\\']application/ld\\+json["\\\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parsed: list[dict[str, Any]] = []
    for raw in blocks:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, list):
            parsed.extend([d for d in data if isinstance(d, dict)])
        elif isinstance(data, dict):
            parsed.append(data)
    return parsed


def _extract_from_product_node(
    node: dict,
) -> Tuple[Dict[str, str], List[str], Optional[str], Optional[float], Optional[str]]:
    attrs: dict[str, str] = {}
    images: list[str] = []
    title = node.get("name")
    description = node.get("description")
    image_val = node.get("image")
    if isinstance(image_val, list):
        images.extend([str(v) for v in image_val if v])
    elif isinstance(image_val, str):
        images.append(image_val)

    def set_attr(key: str, value: Any):
        if value is None:
            return
        text = str(value).strip()
        if text:
            attrs[key] = text

    brand = node.get("brand")
    if isinstance(brand, dict):
        set_attr("brand", brand.get("name") or brand.get("@id"))
    elif isinstance(brand, str):
        set_attr("brand", brand)

    for field in ["sku", "productID", "gtin", "gtin13", "gtin14", "mpn", "model", "color", "size", "material"]:
        if node.get(field):
            set_attr(field.lower(), node.get(field))

    additional_props = node.get("additionalProperty") or node.get("additionalProperties")
    if isinstance(additional_props, list):
        for prop in additional_props:
            if isinstance(prop, dict):
                name = prop.get("name")
                value = prop.get("value") or prop.get("propertyID")
                if name and value:
                    set_attr(name, value)

    offers = node.get("offers")
    price = None
    currency = None
    if isinstance(offers, dict):
        price = offers.get("price")
        currency = offers.get("priceCurrency")
    elif isinstance(offers, list) and offers:
        first_offer = offers[0]
        if isinstance(first_offer, dict):
            price = first_offer.get("price")
            currency = first_offer.get("priceCurrency")

    try:
        price_val = float(price) if price is not None else None
    except Exception:
        price_val = None

    return attrs, images, description, price_val, currency


async def fetch_public_product(url: str) -> Dict[str, Optional[str]]:
    """Извлекает данные с публичной страницы товара через meta/schema.org без учёток."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception:
        return {}

    parser = _MetaParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    meta = parser.meta
    title = meta.get("og:title") or meta.get("twitter:title") or meta.get("title")
    desc = meta.get("og:description") or meta.get("description")
    image = meta.get("og:image") or meta.get("twitter:image")
    attrs: dict[str, str] = {}
    images: list[str] = [image] if image else []

    price = None
    currency = None
    price_raw = meta.get("product:price:amount") or meta.get("og:price:amount")
    currency = meta.get("product:price:currency") or meta.get("og:price:currency")
    if price_raw:
        try:
            price = float(re.sub(r"[^0-9.,]", "", price_raw).replace(",", "."))
        except Exception:
            price = None

    # schema.org / ld+json fallback
    ld_nodes = _parse_ld_json_blocks(html)
    for node in ld_nodes:
        node_type = node.get("@type") or node.get("type")
        types = []
        if isinstance(node_type, list):
            types = [str(t).lower() for t in node_type]
        elif node_type:
            types = [str(node_type).lower()]
        if not any("product" in t for t in types) and not any("offer" in t for t in types):
            continue
        parsed_attrs, parsed_images, parsed_desc, offer_price, offer_currency = _extract_from_product_node(node)
        attrs.update({k: v for k, v in parsed_attrs.items() if v})
        images.extend([img for img in parsed_images if img])
        if not desc and parsed_desc:
            desc = parsed_desc
        if price is None and offer_price is not None:
            price = offer_price
        if currency is None and offer_currency:
            currency = str(offer_currency)
        if not title:
            title = node.get("name")
        break

    # ozon heuristics: page stores data inside __INITIAL_STATE__ JSON
    if not title or not images:
        m_state = re.search(r"__INITIAL_STATE__\"?\\?\":\\?\"({.+?})\"", html)
        if m_state:
            try:
                # unescape
                raw_json = m_state.group(1)
                raw_json = raw_json.encode().decode("unicode_escape")
                data = json.loads(raw_json)
                product = data.get("webProductDetailV2") or data.get("webProductMain") or {}
                if isinstance(product, dict):
                    # pick first item node
                    node = next(iter(product.values())) if product else {}
                    if isinstance(node, dict):
                        title = title or node.get("title") or node.get("name")
                        desc = desc or node.get("description")
                        img_list = node.get("images") or node.get("image") or []
                        if isinstance(img_list, list):
                            images.extend([str(x) for x in img_list if x])
                        price_val = node.get("price") or node.get("finalPrice") or node.get("priceWithBadge")
                        try:
                            price = price or (float(price_val) if price_val is not None else None)
                        except Exception:
                            pass
                        cur_val = node.get("currency")
                        if cur_val:
                            currency = currency or str(cur_val)
            except Exception:
                pass

    unique_images = []
    seen = set()
    for img in images:
        if img and img not in seen:
            seen.add(img)
            unique_images.append(img)

    return {
        "title": title,
        "description": desc,
        "image_url": unique_images[0] if unique_images else None,
        "images": unique_images,
        "attributes": attrs or None,
        "price": price,
        "currency": currency,
        "product_url": url,
    }
