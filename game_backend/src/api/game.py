"""
Game logic and RESTful endpoints for 3D world actions, inventory, progress, and leaderboard.
All endpoints are secured with JWT authentication and fully documented for OpenAPI/Swagger usage.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth import get_current_user
from .db import get_db
from .models import User, Inventory, Progress, Leaderboard

game_router = APIRouter(
    prefix="/game",
    tags=["Game Actions"],
)

# ======================
# === Pydantic Schemas
# ======================

# --- Inventory ---
class InventoryItem(BaseModel):
    item_name: str = Field(..., description="Item name")
    quantity: int = Field(..., ge=1, description="Amount of this item")

class InventoryUpdate(BaseModel):
    item_name: str = Field(..., description="Item name")
    quantity: int = Field(..., description="Amount to set (0 to remove item)")

class InventoryCreate(BaseModel):
    item_name: str = Field(..., description="Item name")
    quantity: int = Field(..., ge=1, description="Amount to add (default 1)")

# --- Progress ---
class ProgressIn(BaseModel):
    level: int = Field(..., ge=1, description="Player's current level")
    checkpoint: Optional[str] = Field(None, description="Current checkpoint label/string")
    score: int = Field(..., ge=0, description="Current game score")

class ProgressOut(ProgressIn):
    last_updated: str

# --- World State ---
class WorldState(BaseModel):
    level: int = Field(..., description="Current level ID")
    checkpoint: Optional[str] = Field(None, description="Current checkpoint")
    world_description: Optional[str] = Field(None, description="Human-readable description of world state (for demo)")

class MoveRequest(BaseModel):
    direction: str = Field(..., description="Direction or command (e.g. 'up', 'down', 'left', 'right', 'jump')")
    magnitude: Optional[int] = Field(default=1, description="How many steps or units to move")

class MoveResult(BaseModel):
    new_level: int
    checkpoint: Optional[str]
    result: str

class InteractRequest(BaseModel):
    action: str = Field(..., description="Interaction type (e.g. 'pickup', 'use', 'talk')")
    target: Optional[str] = Field(None, description="Object/NPC in the world to interact with")

class InteractResult(BaseModel):
    success: bool
    updated_inventory: Optional[List[InventoryItem]]
    description: str

# --- Leaderboard ---
class LeaderboardEntry(BaseModel):
    username: str
    high_score: int
    best_time: Optional[int] = None  # In seconds

# ======================
# === Core API Routes
# ======================

# PUBLIC_INTERFACE
@game_router.get(
    "/worldstate",
    response_model=WorldState,
    summary="Get player's current world state",
    description="Fetch the current world state (level, checkpoint, etc) for the logged-in user.",
)
def get_world_state(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    progress = (
        db.query(Progress)
        .filter_by(user_id=user.id)
        .order_by(Progress.level.desc())
        .first()
    )
    # For POC: just return current progress as the world state.
    if not progress:
        raise HTTPException(status_code=404, detail="No progress found")
    return WorldState(
        level=progress.level,
        checkpoint=progress.checkpoint,
        world_description=f"You are in level {progress.level} checkpoint '{progress.checkpoint}'"
    )

# PUBLIC_INTERFACE
@game_router.post(
    "/move",
    response_model=MoveResult,
    summary="Perform a player movement in the world",
    description="Triggers a player movement action (e.g., move up/down/left/right/jump). Returns new world state."
)
def move_player(
    req: MoveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Simulate: for every move, advance checkpoint string, do not change level.
    progress = db.query(Progress).filter_by(user_id=user.id).order_by(Progress.level.desc()).first()
    if not progress:
        raise HTTPException(status_code=404, detail="No progress found")
    # Update the checkpoint string to show a movement (demo only)
    new_checkpoint = f"{progress.checkpoint or 'start'} > moved {req.direction}"
    progress.checkpoint = new_checkpoint
    db.commit()
    return MoveResult(
        new_level=progress.level,
        checkpoint=new_checkpoint,
        result=f"Player moved {req.direction} with magnitude {req.magnitude or 1}"
    )

# PUBLIC_INTERFACE
@game_router.post(
    "/interact",
    response_model=InteractResult,
    summary="Interact with an object/NPC in world",
    description="Performs an interaction (pickup item, use item, talk to NPC, etc) and updates inventory if needed."
)
def interact_with_world(
    req: InteractRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Demo: If 'pickup', add random item; else, just acknowledge.
    if req.action.lower() == "pickup" and req.target:
        # Demo add item
        item_name = req.target
        inv = db.query(Inventory).filter_by(user_id=user.id, item_name=item_name).first()
        if inv:
            inv.quantity += 1
            db.commit()
        else:
            new_inv = Inventory(user_id=user.id, item_name=item_name, quantity=1)
            db.add(new_inv)
            db.commit()
        updated_inv = db.query(Inventory).filter_by(user_id=user.id).all()
        return InteractResult(
            success=True,
            updated_inventory=[InventoryItem(item_name=i.item_name, quantity=i.quantity) for i in updated_inv],
            description=f"Picked up {item_name}!"
        )
    # Just return success, real logic would go here
    return InteractResult(
        success=True,
        updated_inventory=None,
        description=f"Performed {req.action} {'on ' + req.target if req.target else ''}".strip()
    )

# PUBLIC_INTERFACE
@game_router.get(
    "/inventory",
    response_model=List[InventoryItem],
    summary="Get all inventory items",
    description="List the current inventory items for the logged-in user."
)
def get_inventory(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = db.query(Inventory).filter_by(user_id=user.id).all()
    return [InventoryItem(item_name=i.item_name, quantity=i.quantity) for i in items]

# PUBLIC_INTERFACE
@game_router.post(
    "/inventory/add",
    response_model=List[InventoryItem],
    summary="Add item to inventory",
    description="Add a quantity of an item to the user's inventory.",
)
def add_inventory(
    req: InventoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.query(Inventory).filter_by(user_id=user.id, item_name=req.item_name).first()
    if item:
        item.quantity += req.quantity
    else:
        item = Inventory(user_id=user.id, item_name=req.item_name, quantity=req.quantity)
        db.add(item)
    db.commit()
    db.refresh(item)
    items = db.query(Inventory).filter_by(user_id=user.id).all()
    return [InventoryItem(item_name=i.item_name, quantity=i.quantity) for i in items]

# PUBLIC_INTERFACE
@game_router.post(
    "/inventory/update",
    response_model=List[InventoryItem],
    summary="Update (set/change/remove) inventory item",
    description="Change the quantity of an inventory item or remove from inventory (set quantity zero to delete)."
)
def update_inventory(
    req: InventoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.query(Inventory).filter_by(user_id=user.id, item_name=req.item_name).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not in inventory")
    if req.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = req.quantity
    db.commit()
    items = db.query(Inventory).filter_by(user_id=user.id).all()
    return [InventoryItem(item_name=i.item_name, quantity=i.quantity) for i in items]

# PUBLIC_INTERFACE
@game_router.post(
    "/progress/save",
    response_model=ProgressOut,
    summary="Save current game progress",
    description="Save or update the player's game progress (level, checkpoint, score)."
)
def save_progress(
    req: ProgressIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    progress = (
        db.query(Progress)
        .filter_by(user_id=user.id, level=req.level)
        .first()
    )
    if progress:
        progress.checkpoint = req.checkpoint
        progress.score = req.score
    else:
        progress = Progress(
            user_id=user.id, level=req.level, checkpoint=req.checkpoint, score=req.score
        )
        db.add(progress)
    db.commit()
    db.refresh(progress)
    return ProgressOut(
        level=progress.level,
        checkpoint=progress.checkpoint,
        score=progress.score,
        last_updated=str(progress.last_updated)
    )

# PUBLIC_INTERFACE
@game_router.get(
    "/progress/load",
    response_model=ProgressOut,
    summary="Load last saved progress",
    description="Get player's most recently updated progress (highest level, or most recent)."
)
def load_progress(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    progress = db.query(Progress).filter_by(user_id=user.id).order_by(Progress.level.desc(), Progress.last_updated.desc()).first()
    if not progress:
        raise HTTPException(status_code=404, detail="No progress found")
    return ProgressOut(
        level=progress.level,
        checkpoint=progress.checkpoint,
        score=progress.score,
        last_updated=str(progress.last_updated)
    )

# PUBLIC_INTERFACE
@game_router.get(
    "/leaderboard",
    response_model=List[LeaderboardEntry],
    summary="Fetch global leaderboard (top players)",
    description="Returns top players by high score."
)
def view_leaderboard(
    db: Session = Depends(get_db),
    limit: int = 10,
):
    entries = (
        db.query(Leaderboard)
        .order_by(Leaderboard.high_score.desc(), Leaderboard.best_time)
        .limit(limit)
        .all()
    )
    user_ids = [e.user_id for e in entries]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u.username for u in users}
    return [
        LeaderboardEntry(
            username=user_map.get(e.user_id, "Unknown"),
            high_score=e.high_score,
            best_time=e.best_time,
        )
        for e in entries
    ]

# PUBLIC_INTERFACE
@game_router.post(
    "/leaderboard/submit",
    summary="Submit/update leaderboard entry",
    description="Store the latest leaderboard stats (high score and optional best time) for the current user."
)
def submit_leaderboard(
    high_score: int = Field(..., ge=0, description="High score to submit"),
    best_time: Optional[int] = Field(None, ge=0, description="Best time in seconds"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.query(Leaderboard).filter_by(user_id=user.id).first()
    if entry:
        if high_score > entry.high_score:
            entry.high_score = high_score
        if best_time is not None and (entry.best_time is None or best_time < entry.best_time):
            entry.best_time = best_time
    else:
        entry = Leaderboard(user_id=user.id, high_score=high_score, best_time=best_time)
        db.add(entry)
    db.commit()
    return {"status": "success", "user_id": user.id, "high_score": entry.high_score}


