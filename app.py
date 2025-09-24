# --- add near the top of app.py
import os, re, ipaddress, math
from typing import Optional, List, Literal, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Request, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, text, String, Boolean, Enum, DateTime, func
import enum
import random
from dotenv import load_dotenv
import ssl
from sqlalchemy.ext.asyncio import create_async_engine
from fastapi.responses import HTMLResponse
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy import select, func
from utils.ip_utils import hash_ip



INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>1 Hard Thing a Day</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-gray-50 text-gray-900">
  <main class="max-w-xl mx-auto p-6">
    <h1 class="text-3xl font-bold mb-2">🏔️ 1 Hard Thing a Day</h1>
    <p class="text-sm text-gray-600 mb-4">You're getting soft. Spin for a daily challenge—full item or a pair of halves.</p>

    <section class="bg-white rounded-2xl shadow p-5 space-y-4">
      <div class="flex gap-3">
        <button id="spinBtn" class="flex-1 px-4 py-3 rounded-xl bg-black text-white font-semibold hover:opacity-90">
          Spin 🎲
        </button>
      </div>
      <div id="result" class="p-4 bg-gray-100 rounded-xl text-lg font-medium">
        Press Spin to get your hard thing.
      </div>

      <details class="mt-2">
        <summary class="cursor-pointer font-semibold">View catalog</summary>
        <ul id="catalog" class="mt-2 list-disc list-inside text-sm text-gray-700"></ul>
      </details>

      <hr class="my-4">

      <h2 class="font-semibold">Contribute a new item</h2>
      <form id="contrib" class="space-y-2">
        <input name="name" placeholder="New hard thing" class="w-full border rounded px-3 py-2" required maxlength="60">
        <select name="category" class="w-full border rounded px-3 py-2">
          <option>Physical</option>
          <option>Discipline</option>
          <option>Mind/Skill</option>
          <option>Physical/Discipline</option>
        </select>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" name="is_half"> Counts as half (0.5)
        </label>
        <button class="px-4 py-2 rounded bg-black text-white">Submit</button>
        <p id="contribMsg" class="text-sm mt-1"></p>
      </form>
    </section>
  </main>

  <script>
    async function loadCatalog() {
      const res = await fetch('/items');
      const items = await res.json();
      const ul = document.getElementById('catalog');
      ul.innerHTML = '';
      for (const i of items) {
        const li = document.createElement('li');
        li.textContent = `${i.name} ${i.is_half ? '(0.5)' : ''} — ${i.category}`;
        ul.appendChild(li);
      }
    }

    async function spin() {
      const res = await fetch('/choice');
      const data = await res.json();
      document.getElementById('result').textContent = data.text || 'No result.';
    }

    document.getElementById('spinBtn').addEventListener('click', spin);

    document.getElementById('contrib').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const body = {
        name: fd.get('name'),
        category: fd.get('category'),
        is_half: fd.get('is_half') === 'on'
      };
      const res = await fetch('/items/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const out = await res.json();
      document.getElementById('contribMsg').textContent =
        res.ok ? 'Submitted for review ✅' : (out.detail || 'Error');
      if (res.ok) { e.target.reset(); }
    });

    loadCatalog();
  </script>
</body>
</html>
"""

load_dotenv()

app = FastAPI(title="1 Hard Thing API", version="1.0.0")

DATABASE_URL = os.getenv("DATABASE_URL")
# If using a cloud DB with self-signed cert, you may need to disable verification (not for local dev)
# Adjust as needed for your environment and security requirements
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(DATABASE_URL, connect_args={"ssl": ssl_context})
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL env var (e.g., from Supabase/Neon): postgres+asyncpg://...")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class ItemStatus(str, enum.Enum):
    approved = "approved"
    pending = "pending"
    rejected = "rejected"

ALLOWED_CATEGORIES = {"Physical","Discipline","Mind/Skill","Physical/Discipline"}

class ItemRow(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    category: Mapped[str] = mapped_column(String)
    is_half: Mapped[bool] = mapped_column(Boolean, default=False)
    weight: Mapped[float] = mapped_column(default=1.0)
    status: Mapped[ItemStatus] = mapped_column(
    SAEnum(ItemStatus, name="item_status", native_enum=True),
    default=ItemStatus.approved
)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SubmissionRow(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column()
    # Keep raw only temporarily if it still exists:
    # created_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    created_ip_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now())

async def get_db():
    async with SessionLocal() as session:
        yield session

# ---------- Pydantic models & validators ----------
class SubmitItem(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    category: str
    is_half: bool = False
    weight: float = Field(default=1.0, gt=0, le=5.0)

    @field_validator("category")
    @classmethod
    def category_allowed(cls, v):
        if v not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(ALLOWED_CATEGORIES)}")
        return v

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        v = re.sub(r"\s+", " ", v).strip()
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("name must contain letters")
        return v

class PublicItem(BaseModel):
    id: int
    name: str
    category: str
    is_half: bool
    weight: float

# ---------- util ----------
def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    return (xff.split(",")[0].strip() if xff else request.client.host)

# ---------- routes overriding earlier in-memory ones ----------
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # No auto-create here (use migrations). But this verifies connection.
        await conn.execute(text("SELECT 1"))

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(INDEX_HTML)

@app.get("/items", response_model=List[PublicItem])
async def get_items(db: AsyncSession = Depends(get_db)):
    q = select(ItemRow).where(ItemRow.status == ItemStatus.approved).order_by(ItemRow.id)
    rows = (await db.execute(q)).scalars().all()
    return [PublicItem(id=r.id, name=r.name, category=r.category, is_half=r.is_half, weight=r.weight) for r in rows]

# Add a lightweight health endpoint (good for Fly checks), and ensure you don’t hardcode host/port anywhere
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/items/submit", status_code=201)
async def submit_item(payload: SubmitItem, request: Request, db: AsyncSession = Depends(get_db)):
    # naive profanity/garbage gate (swap with a better lib if you like)
    banned = {"kill","hate","slur"}  # placeholder; expand as needed
    lowered = payload.name.lower()
    if any(b in lowered for b in banned):
        raise HTTPException(400, "name failed content checks")

    # rate limit: 10 submissions / day per IP
    ip = get_client_ip(request)
    ip_h = hash_ip(ip)
    one_day_ago = text("now() - interval '1 day'")
    count_q = select(func.count()).select_from(SubmissionRow).where(
    SubmissionRow.created_ip_hash == ip_h,
    SubmissionRow.created_at > func.now() - text("interval '1 day'")
)
    count = (await db.execute(count_q)).scalar_one()
    if count >= 10:
      raise HTTPException(429, "Rate limit exceeded. Try again tomorrow.")

    # duplicate check (case-insensitive handled by citext UNIQUE, but we preflight)
    exists = await db.execute(select(ItemRow).where(ItemRow.name == payload.name))
    if exists.scalar_one_or_none():
        raise HTTPException(409, "That item already exists.")

    # Insert as PENDING (you or an admin can approve later)
    row = ItemRow(
        name=payload.name,
        category=payload.category,
        is_half=payload.is_half,
        weight=payload.weight,
        status=ItemStatus.pending,
        #created_ip=ip
    )
    db.add(row)
    await db.flush()  # get row.id

    # submissions log with HASH ONLY
    db.add(SubmissionRow(item_id=row.id, created_ip_hash=ip_h))
    await db.commit()
    return {"ok": True, "id": row.id, "status": "pending", "message": "Submitted for review."}

# put near your other helpers
def to_public(row: ItemRow) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "is_half": row.is_half,
        "weight": row.weight,
    }


# keep your existing /choice endpoint but pull pools from DB
async def fetch_pools(db: AsyncSession, include_categories=None, exclude_categories=None, exclude_ids=None):
    q = select(ItemRow).where(ItemRow.status == ItemStatus.approved)
    rows = (await db.execute(q)).scalars().all()
    def filt(r):
        if include_categories and r.category not in include_categories: return False
        if exclude_categories and r.category in exclude_categories: return False
        if exclude_ids and r.id in exclude_ids: return False
        return True
    approved = [r for r in rows if filt(r)]
    full = [r for r in approved if not r.is_half]
    half = [r for r in approved if r.is_half]
    return full, half

@app.get("/choice")
async def get_choice(
    mode: Literal["random","full","half-pair"]="random",
    seed: Optional[int]=None,
    half_pair_probability: float=0.5,
    include_categories: Optional[List[str]]=Query(None),
    exclude_categories: Optional[List[str]]=Query(None),
    exclude_ids: Optional[List[int]]=Query(None),
    db: AsyncSession = Depends(get_db)
):
    if seed is not None: random.seed(seed)
    full_pool, half_pool = await fetch_pools(db, include_categories, exclude_categories, exclude_ids)

    def weighted_choice(rows): return random.choices(rows, weights=[r.weight for r in rows], k=1)[0]
    def weighted_two(rows):
        first = weighted_choice(rows)
        remain = [r for r in rows if r.id != first.id]
        second = weighted_choice(remain) if remain else None
        return [first, second] if second else []

    if mode == "full":
        if not full_pool: return {"type":"full","items":[],"text":"No full items available."}
        r = weighted_choice(full_pool)
        return {"type":"full","items":[PublicItem(**to_public(r))],"text":f"Today's hard thing: {r.name}"}

    if mode == "half-pair":
        if len(half_pool) < 2: return {"type":"half-pair","items":[],"text":"Not enough half items."}
        a,b = weighted_two(half_pool)
        return {"type":"half-pair","items":[PublicItem(**to_public(a)), PublicItem(**to_public(b))],"text":f"Today's hard thing (do BOTH): {a.name} + {b.name}"}

    choose_half = (random.random() < half_pair_probability) and len(half_pool) >= 2
    if choose_half:
        a,b = weighted_two(half_pool)
        return {"type":"half-pair","items":[PublicItem(**to_public(a)), PublicItem(**to_public(b))],"text":f"Today's hard thing (do BOTH): {a.name} + {b.name}"}
    if not full_pool:
        if len(half_pool) >= 2:
            a,b = weighted_two(half_pool)
            return {"type":"half-pair","items":[PublicItem(**to_public(a)), PublicItem(**to_public(b))],"text":f"Today's hard thing (do BOTH): {a.name} + {b.name}"}
        return {"type":"full","items":[],"text":"No items available."}
    r = weighted_choice(full_pool)
    return {"type":"full","items":[PublicItem(**to_public(r))],"text":f"Today's hard thing: {r.name}"}
