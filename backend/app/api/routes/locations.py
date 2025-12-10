from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.location import Location
from app.models.item import Item
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.schemas.item import ItemOut
from app.api.routes.items import _serialize_item

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/", response_model=list[LocationOut])
async def list_locations(db: AsyncSession = Depends(get_db)) -> list[Location]:
    res = await db.execute(select(Location).order_by(Location.parent_id.nullsfirst(), Location.id))
    return res.scalars().all()


@router.post("/", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(payload: LocationCreate, db: AsyncSession = Depends(get_db)) -> Location:
    location = Location(**payload.dict())
    # простая генерация path; в проде заменить на ltree
    if payload.parent_id:
        parent = await db.get(Location, payload.parent_id)
        if not parent:
            raise HTTPException(status_code=400, detail="Parent not found")
        location.path = f"{parent.path or parent.id}.{payload.name}"
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(location_id: int, payload: LocationUpdate, db: AsyncSession = Depends(get_db)) -> Location:
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(loc, k, v)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: int, db: AsyncSession = Depends(get_db)):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    await db.delete(loc)
    await db.commit()
    return None


@router.get("/{location_id}/items", response_model=list[ItemOut])
async def items_for_location(location_id: int, db: AsyncSession = Depends(get_db)) -> list[ItemOut]:
    stmt = select(Item).where(Item.location_id == location_id).order_by(Item.created_at.desc())
    items = (await db.execute(stmt)).scalars().all()
    return [await _serialize_item(item, db) for item in items]
