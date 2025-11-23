from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Path, Depends

from typing import List, Optional
from uuid import UUID, uuid4
import uvicorn
from sqlalchemy.orm import Session

from models.ranking import RankingRead, RankingUpdate, RankingCreate, Origin, RankedItem, RankedItemUpdate
from database import get_db, init_db, RankingDB, RankedItemDB

app = FastAPI(
    title="Matchamania – Rankings API",
    description="This ranking API allows users to rank their favorite matcha powders and cafes.",
    version="1.0.0",
    contact={"email": "you@your-company.com"},
    license_info={
        "name": "Apache 2.0",
        "url": "http://www.apache.org/licenses/LICENSE-2.0.html"
    }
)


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    print("✅ Database initialized")


@app.get("/health")
def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


def db_to_pydantic(db_ranking: RankingDB) -> RankingRead:
    """Convert database model to Pydantic model"""
    return RankingRead(
        id=UUID(db_ranking.id),
        user_id=UUID(db_ranking.user_id),
        items=[
            RankedItem(
                name=item.name,
                origin=Origin(item.origin.value),
                rating=item.rating,
                cost_per_gram=item.cost_per_gram
            )
            for item in db_ranking.items
        ],
        created_at=db_ranking.created_at,
        updated_at=db_ranking.updated_at
    )


@app.get("/ranking", response_model=List[RankingRead], tags=["ranking"])
def list_rankings(
        user_id: UUID = Query(..., description="User to get rankings for"),
        min_rating: Optional[float] = Query(None, ge=0, le=5),
        max_rating: Optional[float] = Query(None, ge=0, le=5),
        max_cost: Optional[float] = Query(None, ge=0),
        origin: Optional[Origin] = Query(None),
        db: Session = Depends(get_db)
):
    """List rankings for a user with optional filters"""
    # Get all rankings for user
    rankings = db.query(RankingDB).filter(
        RankingDB.user_id == str(user_id)
    ).all()

    results = []
    for ranking in rankings:
        filtered_items = list(ranking.items)

        # Apply filters
        if min_rating is not None:
            filtered_items = [i for i in filtered_items if i.rating >= min_rating]
        if max_rating is not None:
            filtered_items = [i for i in filtered_items if i.rating <= max_rating]
        if max_cost is not None:
            filtered_items = [i for i in filtered_items if i.cost_per_gram <= max_cost]
        if origin is not None:
            filtered_items = [i for i in filtered_items if i.origin.value == origin.value]

        # Only include rankings with matching items
        if filtered_items:
            # Create temporary ranking with filtered items
            temp_ranking = RankingDB(
                id=ranking.id,
                user_id=ranking.user_id,
                created_at=ranking.created_at,
                updated_at=ranking.updated_at
            )
            temp_ranking.items = filtered_items
            results.append(db_to_pydantic(temp_ranking))

    return results


@app.post("/ranking", response_model=RankingRead, status_code=201, tags=["ranking"])
def create_ranking(
        payload: RankingCreate,
        db: Session = Depends(get_db)
):
    """Create a new ranking"""
    # Check for duplicate items
    existing = db.query(RankingDB).filter(
        RankingDB.user_id == str(payload.user_id)
    ).first()

    if existing:
        # Check for duplicate item names/origins
        for existing_item in existing.items:
            for new_item in payload.items:
                if (existing_item.name == new_item.name and
                        existing_item.origin.value == new_item.origin.value):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Item '{new_item.name}' with origin '{new_item.origin}' already exists"
                    )

    # Create new ranking
    db_ranking = RankingDB(
        id=str(payload.id),
        user_id=str(payload.user_id)
    )

    # Add items
    for item in payload.items:
        db_item = RankedItemDB(
            id=str(uuid4()),
            ranking_id=db_ranking.id,
            name=item.name,
            origin=item.origin.value,
            rating=item.rating,
            cost_per_gram=item.cost_per_gram
        )
        db_ranking.items.append(db_item)

    db.add(db_ranking)
    db.commit()
    db.refresh(db_ranking)

    return db_to_pydantic(db_ranking)


@app.get("/ranking/{id}", response_model=RankingRead, tags=["ranking"])
def get_ranking(
        id: UUID = Path(...),
        db: Session = Depends(get_db)
):
    """Get a specific ranking"""
    ranking = db.query(RankingDB).filter(RankingDB.id == str(id)).first()

    if not ranking:
        raise HTTPException(status_code=404, detail="Not found")

    return db_to_pydantic(ranking)


@app.put("/ranking/{id}", response_model=RankingRead, tags=["ranking"])
def replace_ranking(
        id: UUID,
        payload: RankingUpdate,
        db: Session = Depends(get_db)
):
    """Replace all items in a ranking"""
    ranking = db.query(RankingDB).filter(RankingDB.id == str(id)).first()

    if not ranking:
        raise HTTPException(status_code=404, detail="Not found")

    # Delete all existing items
    for item in ranking.items:
        db.delete(item)

    # Add new items
    for item in payload.items:
        db_item = RankedItemDB(
            id=str(uuid4()),
            ranking_id=str(id),
            name=item.name,
            origin=item.origin.value,
            rating=item.rating,
            cost_per_gram=item.cost_per_gram
        )
        db.add(db_item)

    ranking.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ranking)

    return db_to_pydantic(ranking)


@app.delete("/ranking/{id}", status_code=204, tags=["ranking"])
def delete_ranking(
        id: UUID,
        db: Session = Depends(get_db)
):
    """Delete a ranking"""
    ranking = db.query(RankingDB).filter(RankingDB.id == str(id)).first()

    if not ranking:
        raise HTTPException(status_code=404, detail="Not found")

    db.delete(ranking)
    db.commit()
    return None


@app.patch("/ranking/{id}/item/{item_index}", tags=["ranking"])
def update_single_item(
        id: UUID,
        item_index: int,
        payload: RankedItemUpdate,
        db: Session = Depends(get_db)
):
    """Update a single item in a ranking (helper endpoint)"""
    ranking = db.query(RankingDB).filter(RankingDB.id == str(id)).first()

    if not ranking:
        raise HTTPException(status_code=404, detail="Ranking not found")

    if not (0 <= item_index < len(ranking.items)):
        raise HTTPException(status_code=404, detail="Item not found")

    item = ranking.items[item_index]

    # Update fields if provided
    if payload.name is not None:
        item.name = payload.name
    if payload.origin is not None:
        item.origin = payload.origin.value
    if payload.rating is not None:
        item.rating = payload.rating
    if payload.cost_per_gram is not None:
        item.cost_per_gram = payload.cost_per_gram

    ranking.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Item updated"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)