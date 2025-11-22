from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Path

from typing import List, Optional, Dict
from uuid import UUID, uuid4

from models.ranking import RankingRead, RankingUpdate, RankingCreate, Origin, RankingBase, RankedItem, RankedItemUpdate


db: Dict[UUID, RankingRead] = {}

app = FastAPI(
    title="Matchamania – Rankings API",
    description="This ranking API allows users to rank their favorite matcha powders and cafes.",
    version="1.0.0",
    contact={
        "email": "you@your-company.com"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "http://www.apache.org/licenses/LICENSE-2.0.html"
    }
)

def check_items_exist_for_user(new_ranking: RankingBase):
    # filter rankings of the same user
    user_rankings = [r for r in db if r.user_id == new_ranking.user_id]

    for ranking in user_rankings:
        for existing_item in ranking.items:
            for new_item in new_ranking.items:
                if existing_item.name == new_item.name and existing_item.origin == new_item.origin:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Item '{new_item.name}' with origin '{new_item.origin}' already exists for this user."
                    )

def to_public(r: RankingBase) -> RankingRead:
    return RankingRead(
        id=r.id,
        user_id=r.user_id,
        items=r.items
    )

@app.get("/ranking", response_model=List[RankingRead], tags=["ranking"])
def list_rankings(
    user_id: UUID = Query(..., description="User to get rankings for"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    max_rating: Optional[float] = Query(None, ge=0, le=5),
    max_cost: Optional[float] = Query(None, ge=0),
    origin: Optional[Origin] = Query(None),
):
    results = []

    for ranking in db.values():
        if ranking.user_id != user_id:
            continue

        filtered_items = ranking.items

        if min_rating is not None:
            filtered_items = [i for i in filtered_items if i.rating >= min_rating]

        if max_rating is not None:
            filtered_items = [i for i in filtered_items if i.rating <= max_rating]

        if max_cost is not None:
            filtered_items = [i for i in filtered_items if i.cost_per_gram <= max_cost]

        if origin is not None:
            filtered_items = [i for i in filtered_items if i.origin == origin]

        # Only include ranking if it has matching items
        if filtered_items:
            r_copy = ranking.model_copy(deep=True)
            r_copy.items = filtered_items
            results.append(to_public(r_copy))

    return results

@app.post("/ranking", response_model=RankingRead, status_code=201, tags=["ranking"])
def create_ranking(payload: RankingCreate):
    ranking_read = RankingRead(**payload.model_dump())
    db[ranking_read.id] = ranking_read
    return ranking_read

@app.get("/ranking/{id}", response_model=RankingRead, tags=["ranking"])
def get_ranking(id: UUID = Path(...)):
    if id not in db:
        raise HTTPException(status_code=404, detail="Not found")
    return to_public(db[id])


@app.delete("/ranking/{id}", status_code=204, tags=["ranking"])
def delete_ranking(id: UUID):
    if id not in db:
        raise HTTPException(status_code=404, detail="Not found")
    del db[id]
    return

# -----------------------------
# PUT /ranking/{id}  (replaceRank)
# YAML says: replace a rating based on item name
# -----------------------------
@app.put("/ranking/{id}", response_model=RankingRead, tags=["ranking"])
def replace_ranking(
    id: UUID,
    payload: RankingUpdate
):
    if id not in db:
        raise HTTPException(status_code=404, detail="Not found")

    ranking = db[id]

    # Replace entire item list
    ranking.items = payload.items
    ranking.updated_at = datetime.utcnow()

    return to_public(ranking)


# -----------------------------
# PATCH /ranking/{id}/item/{item_index}
# Internal helper endpoint (not in YAML)
# Allows updating a single RankedItem field.
# -----------------------------
@app.patch("/ranking/{id}/item/{item_index}", tags=["ranking"])
def update_single_item(id: UUID, item_id: int, payload: RankedItemUpdate):
    if id not in db:
        raise HTTPException(status_code=404, detail="Ranking not found")

    ranking = db[id]
    if len(ranking.items) > item_id >= 0:
        item = ranking.items[item_id]
        if payload.name is not None:
            item.name = payload.name
        if payload.origin is not None:
            item.origin = payload.origin
        if payload.rating is not None:
            item.rating = payload.rating
        if payload.cost_per_gram is not None:
            item.cost_per_gram = payload.cost_per_gram

        ranking.updated_at = datetime.utcnow()
        return {"message": "Item updated"}

    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

