from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import math, os, uuid

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
ALLOWED_RADIUS = 500

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def haversine(lat1, lon1, lat2, lon2):
    R=6371000
    dlat=math.radians(lat2-lat1)
    dlon=math.radians(lon2-lon1)
    a=(math.sin(dlat/2)**2 +
       math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2)
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    res = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
    if not res.data: return {"error":"invalid"}
    return {"user_id": res.data[0]["id"], "token": "dummy"}

@app.get("/locations")
def locations(user_id: str):
    res = supabase.table("user_locations").select("id,name").eq("user_id", user_id).execute()
    return res.data

@app.post("/punch-in")
async def punch_in(
    user_id: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    mode: str = Form(...),
    location_id: str = Form(None),
    location_name: str = Form(None),
    photo: UploadFile = File(...)
):
    if mode == "new":
        loc = supabase.table("user_locations").insert({
            "user_id": user_id, "name": location_name, "lat": lat, "lon": lon
        }).execute().data[0]
        location_id = loc["id"]
        dist = 0
    else:
        loc = supabase.table("user_locations").select("*").eq("id", location_id).execute().data[0]
        dist = haversine(lat, lon, loc["lat"], loc["lon"])
        if dist > ALLOWED_RADIUS:
            return {"error":"Not near existing location"}

    path = f"{user_id}/{uuid.uuid4()}.jpg"
    supabase.storage.from_("attendance-photos").upload(path, await photo.read())

    supabase.table("attendance").insert({
        "user_id": user_id,
        "location_id": location_id,
        "lat": lat,
        "lon": lon,
        "distance_meters": dist,
        "photo_url": path,
        "punch_type": "IN"
    }).execute()

    return {"ok": True}
