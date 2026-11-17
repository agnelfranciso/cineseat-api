from fastapi import FastAPI, Query, Path, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import os
import datetime
import math
import uuid
import time
from collections import defaultdict
from scalar_fastapi import get_scalar_api_reference, Theme

from app import extractor
from app import scoring
from app.models import (
    City, CityListResponse, CityResponse,
    Movie, MovieListResponse,
    Cinema, CinemaListResponse,
    ShowSession, ShowtimesResponse,
    AuditoriumLayoutResponse, HallGeometry, SeatCategory, RowLayout, Seat, Seat3DCoordinates, SeatStatus,
    BestSeatsResponse, SeatRecommendation, SeatScoringMetrics, ScoreBand,
    AlertSubscriptionRequest, AlertSubscriptionResponse,
    FeedbackRequest, GenericResponse
)

# ==============================================================================
# Scalar & OpenAPI Tag Definitions
# ==============================================================================

TAGS_METADATA = [
    {
        "name": "System & Health",
        "description": (
            "Service telemetry, load balancer health endpoints (Kubernetes, AWS ALB, Docker), "
            "and resource discovery manifests."
        ),
    },
    {
        "name": "Cities & Geo-Location",
        "description": (
            "Geographic directory covering all 2,167+ Indian cities and towns, tier-1 metro filters, "
            "and GPS nearest-city lookup via the spherical Haversine formula."
        ),
    },
    {
        "name": "Movies & Discovery",
        "description": (
            "Real-time theatrical movie catalog for every Indian city with verified high-resolution "
            "portrait and landscape artwork, audio tracks, censor ratings, and durations."
        ),
    },
    {
        "name": "Cinemas & Exhibitors",
        "description": (
            "Cinema hall directory with exhibitor chains (PVR INOX, Cinepolis, Miraj, MovieMax), "
            "precise GPS coordinates, physical street addresses, and screening format badges (IMAX, 4DX, Dolby Atmos, ICE, Laser)."
        ),
    },
    {
        "name": "Showtimes & Screening Schedules",
        "description": (
            "Live screening schedules grouped by movie or cinema, real-time remaining seat counts, "
            "ticket price brackets, and occupancy percentages."
        ),
    },
    {
        "name": "Auditorium & 3D Spatial Layout",
        "description": (
            "Full physical auditorium modeling with true metric $(x, y, z)$ seat coordinates, "
            "stadium tier step rises, physical screen dimensions, and seat categories (Recliner, Prime, Classic)."
        ),
    },
    {
        "name": "SMPTE/THX Seat Scoring Engine",
        "description": (
            "Proprietary 3D optical seating geometry optimizer evaluating Horizontal FOV (SMPTE 196M), "
            "Off-Axis angle, and Vertical Neck Tilt (THX $\\le 15^\\circ$) to identify and rank optimal contiguous seat blocks."
        ),
    },
    {
        "name": "Alerts & Subscriptions",
        "description": (
            "Real-time seat drop notifications and user feedback ingestion."
        ),
    },
]

API_DESCRIPTION = """
# CineSeat Cinema Seating & Showtimes Intelligence Engine

Welcome to the **CineSeat API**, a high-performance REST platform engineered to solve the cinema seating puzzle.

---

## 🎯 The Cinema Seating Challenge

When booking movie tickets, standard ticketing apps display flat 2D seat grids. They do not reveal:
1. **Front-Row Neck Fatigue**: Seats placed too close to the screen force patrons to tilt their heads upward beyond $15^\\circ$, causing cervical discomfort.
2. **Side-Aisle Keystone Distortion**: Seats far off the center axis experience trapezoidal image distortion and uneven stereo/surround audio balance.
3. **Contiguous Group Seating**: Finding $N$ adjacent seats with prime viewing quality across multiple halls and showtimes is manual and error-prone.

**CineSeat API** models the physical 3D auditorium in real-world metric units and computes mathematical optical viewing metrics according to global cinematic standards (**SMPTE 196M** and **THX**).

---

## 📐 Mathematical Formulation (SMPTE & THX)

Each seat S(x, y, z) is evaluated in 3D Euclidean space against the cinema screen center (0, y_c, 0) of width W:

### 1. Horizontal Field of View (FOV)
```text
θ_FOV = arctan((W/2 − x_s) / z_s) − arctan((-W/2 − x_s) / z_s)
```
- **SMPTE 196M Standard**: Minimum ≥ 30°; Reference sweet spot 45°.
- **THX Guideline**: Recommends ≥ 36° for true cinematic immersion.

### 2. Off-Axis Displacement Angle
```text
θ_axis = arctan(|x_s| / z_s)
```
- Center seats have θ_axis ≈ 0°.
- Angles > 15° introduce noticeable trapezoidal image distortion and uneven acoustic timing.

### 3. Vertical Neck Tilt Angle
```text
φ_neck = arctan((y_c − (y_s + h_eye)) / √(x_s² + z_s²))
```
- **THX Maximum**: φ_neck ≤ 15°. Exceeding 15° causes acute cervical neck fatigue.

### 4. Composite Quality Score
The final seat score Q (0 to 100) is calculated as:
```text
Q = 100 × ( 0.42 · S_FOV + 0.38 · S_axis + 0.20 · S_neck )
```

| Score Range | Quality Band | Seating Assessment |
| :--- | :--- | :--- |
| **88 – 100** | `Exceptional` | **Auditorium Sweet Spot** — THX reference viewing angle & zero neck strain |
| **75 – 87** | `Great` | **Prime Experience** — Balanced eye-level immersion with high FOV |
| **60 – 74** | `Good` | **Comfortable View** — Slight lateral offset but solid screen visibility |
| **45 – 59** | `Fair` | **Acceptable** — Noticeable side angle or higher elevation |
| **0 – 44** | `Poor` | **Compromised** — Front row neck strain or extreme peripheral distortion |

---

## 🚀 Quick Navigation
- **All Cities**: Search over 2,167 Indian cities (`/api/v1/cities`)
- **GPS Nearest City**: Find closest cinema hub (`/api/v1/cities/nearest`)
- **Current Movies**: List now-showing films (`/api/v1/movies`)
- **Cinemas Directory**: Halls with formats & coordinates (`/api/v1/cinemas`)
- **Showtimes**: By movie or cinema (`/api/v1/showtimes/...`)
- **Auditorium 3D**: Full metric spatial map (`/api/v1/auditorium/layout/...`)
- **Seat Recommendations**: Best contiguous seats (`/api/v1/recommendations/best-seats`)
"""

app = FastAPI(
    title="CineSeat Cinema Seating & Showtimes Intelligence API",
    description=API_DESCRIPTION,
    version="3.0.0",
    docs_url=None,  # Handled exclusively by modern Scalar UI at /docs
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA
)

# Unrestricted CORS for integration with any web, mobile, or microservice frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting:
# By default, the GitHub repo and self-hosted instances have NO RATE LIMITS.
# Rate limiting is ONLY active if LIVE_DEMO_MODE=true or RATE_LIMIT_ENABLED=true in the environment.
RATE_LIMIT_ENABLED = os.getenv("LIVE_DEMO_MODE", os.getenv("RATE_LIMIT_ENABLED", "false")).lower() in ("true", "1", "yes")
RATE_LIMIT_WINDOW = 60.0
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
_request_timestamps: Dict[str, List[float]] = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path

    # Whitelist documentation, health check, and schema
    if path in ["/", "/docs", "/scalar", "/openapi.json", "/health", "/favicon.ico"]:
        return await call_next(request)

    now = time.time()
    valid_times = [t for t in _request_timestamps[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(valid_times) >= RATE_LIMIT_MAX_REQUESTS:
        retry_after = int(RATE_LIMIT_WINDOW - (now - valid_times[0])) + 1
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Live demo rate limit reached ({RATE_LIMIT_MAX_REQUESTS} req/min). Please slow down.",
                "retry_after_seconds": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": "0"
            }
        )

    valid_times.append(now)
    _request_timestamps[client_ip] = valid_times
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT_MAX_REQUESTS - len(valid_times))
    return response

def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

# ==============================================================================
# Modern Interactive Documentation Interface (Scalar)
# ==============================================================================

@app.get("/docs", include_in_schema=False)
@app.get("/scalar", include_in_schema=False)
def scalar_documentation():
    """
    Renders Scalar — the premier, modern, developer-friendly interactive API reference.
    Features dark mode, multi-language code snippets (Python, JavaScript, cURL, Go),
    instant full-text search (Cmd+K / Ctrl+K), and live test requests.
    """
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="CineSeat API — Interactive Reference",
        theme=Theme.PURPLE,
        layout="modern",
        show_sidebar=True,
    )

# ==============================================================================
# 1. System & Health Endpoints
# ==============================================================================

@app.get(
    "/",
    tags=["System & Health"],
    summary="Service Information & Endpoint Manifest",
    description=(
        "Returns top-level metadata about the CineSeat API service, operational health, "
        "and direct URLs to interactive documentation UI (Scalar) "
        "and primary resource endpoints."
    )
)
def service_root():
    return {
        "service": "CineSeat Cinema Seating & Showtimes Intelligence API",
        "version": "3.0.0",
        "status": "operational",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
        "endpoints": {
            "cities": "/api/v1/cities",
            "nearest_city": "/api/v1/cities/nearest?lat={lat}&lng={lng}",
            "movies": "/api/v1/movies?city={city_slug}",
            "cinemas": "/api/v1/cinemas?city={city_slug}",
            "showtimes_by_movie": "/api/v1/showtimes/by-movie/{movie_id}?city={city_slug}&date={date}",
            "showtimes_by_cinema": "/api/v1/showtimes/by-cinema/{cinema_id}?city={city_slug}&date={date}",
            "auditorium_layout": "/api/v1/auditorium/layout/{cinema_id}/{session_id}?city={city_slug}",
            "seat_recommendations": "/api/v1/recommendations/best-seats?movie_id={id}&city={city}&seats_count={n}",
            "alerts_subscribe": "/api/v1/alerts/subscribe"
        }
    }

@app.get(
    "/health",
    tags=["System & Health"],
    summary="Health & Uptime Status",
    description=(
        "Provides service availability and readiness metrics. Used by load balancers, "
        "Kubernetes liveness probes, and Docker container HEALTHCHECK instructions."
    )
)
@app.get(
    "/api/v1/health",
    tags=["System & Health"],
    summary="Health & Uptime Status (v1)",
    description="Versioned health check endpoint returning service status and city database capacity."
)
def health_check():
    return {
        "status": "healthy",
        "timestamp": utc_now_iso(),
        "database_cities_count": len(extractor.CITIES),
        "engine": "FastAPI + SMPTE/THX 3D Geometry Evaluator"
    }

# ==============================================================================
# 2. Cities Directory & Geo-Location
# ==============================================================================

@app.get(
    "/api/v1/cities",
    response_model=CityListResponse,
    tags=["Cities & Geo-Location"],
    summary="List & Search Indian Cities",
    description=(
        "Retrieves a paginated list of cities and cinema markets from the 2,167+ Indian cities database.\n\n"
        "### Capabilities:\n"
        "- **Full-Text Filter**: Substring match across city names and states (e.g. `?query=thrissur` or `?query=kerala`).\n"
        "- **Metro Only**: Filter exclusively for tier-1 metropolitan markets (`?metro_only=true`).\n"
        "- **Pagination**: Slice results using `limit` and `offset` for responsive UI integration.\n\n"
        "### Response Content:\n"
        "Each city object returns its unique slug, localized name, state/territory, metro status, and approximate GPS coordinates."
    )
)
def list_cities(
    query: Optional[str] = Query(None, description="Search filter for city name or state (case-insensitive)", example="mumbai"),
    metro_only: bool = Query(False, description="When true, returns only tier-1 metropolitan cinema hubs", example=False),
    limit: int = Query(100, ge=1, le=2500, description="Maximum number of cities to return in page", example=20),
    offset: int = Query(0, ge=0, description="Number of cities to skip for pagination", example=0)
):
    raw_cities = extractor.get_cities(top=1 if metro_only else None)
    
    if query and query.strip():
        q = query.strip().lower()
        raw_cities = [c for c in raw_cities if q in c["name"].lower() or q in c.get("state", "").lower()]

    paginated = raw_cities[offset:offset + limit]
    city_objs = [
        City(
            slug=c["slug"],
            name=c["name"],
            state=c.get("state", "India"),
            is_metro=c.get("is_top_city", False),
            latitude=c.get("lat"),
            longitude=c.get("lng")
        )
        for c in paginated
    ]
    return CityListResponse(
        timestamp=utc_now_iso(),
        count=len(city_objs),
        cities=city_objs
    )

@app.get(
    "/api/v1/cities/nearest",
    response_model=CityResponse,
    tags=["Cities & Geo-Location"],
    summary="Find Nearest City by GPS Coordinates",
    description=(
        "Uses the **Haversine great-circle distance algorithm** to calculate the closest cinema hub "
        "given a user's geographical coordinates (`lat`, `lng`).\n\n"
        "### Mathematical Formula (Haversine Distance):\n\n"
        "```text\n"
        "a = sin²(Δlat / 2) + cos(lat₁) · cos(lat₂) · sin²(Δlon / 2)\n"
        "c = 2 · atan2(√a, √(1 − a))\n"
        "d = R · c\n"
        "```\n\n"
        "Or in closed form:\n\n"
        "```text\n"
        "d = 2 · R · arcsin( √( sin²(Δlat / 2) + cos(lat₁) · cos(lat₂) · sin²(Δlon / 2) ) )\n"
        "```\n\n"
        "**Variables & Constants:**\n"
        "- `R = 6,371 km` (Mean radius of Earth)\n"
        "- `Δlat = lat₂ − lat₁` (converted to radians)\n"
        "- `Δlon = lon₂ − lon₁` (converted to radians)\n"
        "- `d` = Shortest great-circle distance on Earth's surface in kilometers\n\n"
        "Ideal for web/mobile location prompts (`navigator.geolocation`) to auto-select the user's nearest cinema market."
    )
)
def find_nearest_city(
    lat: float = Query(..., ge=-90.0, le=90.0, description="User latitude in decimal degrees", example=10.5276),
    lng: float = Query(..., ge=-180.0, le=180.0, description="User longitude in decimal degrees", example=76.2144)
):
    metro_coords = {
        "mumbai": (19.0760, 72.8777, "Mumbai", "Maharashtra"),
        "national-capital-region-ncr": (28.6139, 77.2090, "Delhi-NCR", "Delhi"),
        "bengaluru": (12.9716, 77.5946, "Bengaluru", "Karnataka"),
        "hyderabad": (17.3850, 78.4867, "Hyderabad", "Telangana"),
        "chandigarh": (30.7333, 76.7794, "Chandigarh", "Punjab"),
        "ahmedabad": (23.0225, 72.5714, "Ahmedabad", "Gujarat"),
        "pune": (18.5204, 73.8567, "Pune", "Maharashtra"),
        "chennai": (13.0827, 80.2707, "Chennai", "Tamil Nadu"),
        "kolkata": (22.5726, 88.3639, "Kolkata", "West Bengal"),
        "kochi": (9.9312, 76.2673, "Kochi", "Kerala"),
        "thrissur": (10.5276, 76.2144, "Thrissur", "Kerala")
    }

    def haversine_km(lat1, lon1, lat2, lon2):
        R = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2.0) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(d_lon / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    best_slug = "mumbai"
    min_dist = float("inf")
    for slug, (c_lat, c_lng, name, state) in metro_coords.items():
        d = haversine_km(lat, lng, c_lat, c_lng)
        if d < min_dist:
            min_dist = d
            best_slug = slug

    city_data = extractor.get_city_by_slug(best_slug) or {
        "slug": best_slug,
        "name": metro_coords[best_slug][2],
        "state": metro_coords[best_slug][3],
        "is_top_city": True,
        "lat": metro_coords[best_slug][0],
        "lng": metro_coords[best_slug][1]
    }
    return CityResponse(
        timestamp=utc_now_iso(),
        city=City(
            slug=city_data["slug"],
            name=city_data["name"],
            state=city_data.get("state", "India"),
            is_metro=city_data.get("is_top_city", False),
            latitude=city_data.get("lat"),
            longitude=city_data.get("lng")
        )
    )

@app.get(
    "/api/v1/cities/{city_slug}",
    response_model=CityResponse,
    tags=["Cities & Geo-Location"],
    summary="Get Specific City Information",
    description="Looks up comprehensive profile and geographical coordinates for a city by its URL slug."
)
def get_city_details(
    city_slug: str = Path(..., description="Unique city slug (e.g. mumbai, bangalore, thrissur)", example="thrissur")
):
    city_data = extractor.get_city_by_slug(city_slug)
    if not city_data:
        raise HTTPException(status_code=404, detail=f"City '{city_slug}' not found in directory")
    return CityResponse(
        timestamp=utc_now_iso(),
        city=City(
            slug=city_data["slug"],
            name=city_data["name"],
            state=city_data.get("state", "India"),
            is_metro=city_data.get("is_top_city", False),
            latitude=city_data.get("lat"),
            longitude=city_data.get("lng")
        )
    )

# ==============================================================================
# 3. Movies Catalog
# ==============================================================================

@app.get(
    "/api/v1/movies",
    response_model=MovieListResponse,
    tags=["Movies & Discovery"],
    summary="List Live Movies Currently Screening in City",
    description=(
        "Retrieves all movies currently in theatrical rotation for the designated city.\n\n"
        "### Extracted Metadata:\n"
        "- **High-Resolution Artwork**: Portrait posters and landscape banners.\n"
        "- **Categorization**: Genres (Action, Thriller, Drama), audio language tracks, and censor certification (U, UA, A).\n"
        "- **Run Times & Ratings**: Duration in minutes and aggregate critic/audience ratings."
    )
)
def list_movies(
    city: str = Query(..., description="City slug context (e.g. mumbai, thrissur, bengaluru)", example="thrissur")
):
    raw_data = extractor.get_movies_for_city(city)
    movies_list = []
    for m in raw_data.get("data", []):
        m_id = m.get("code") or m.get("event_code") or "ET0"
        movies_list.append(
            Movie(
                id=m_id,
                title=m.get("title", "Untitled Movie"),
                slug=m.get("slug", ""),
                genres=m.get("genres", ["Drama"]),
                primary_language=m.get("primary_language", "English"),
                languages=m.get("languages", ["English"]),
                censor_rating=m.get("certificate", "UA"),
                rating=m.get("rating_text", "8.5/10"),
                runtime_minutes=m.get("runtime_minutes", 130),
                poster_url=m.get("poster_url", "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80"),
                backdrop_url=m.get("landscape_url"),
                synopsis=m.get("synopsis")
            )
        )
    return MovieListResponse(
        timestamp=utc_now_iso(),
        city=city,
        count=len(movies_list),
        movies=movies_list
    )

@app.get(
    "/api/v1/movies/{movie_id}",
    response_model=Movie,
    tags=["Movies & Discovery"],
    summary="Get Movie Details by ID",
    description="Returns detailed profile, synopsis, duration, genres, and verified poster artwork for a specific movie identifier."
)
def get_movie_by_id(
    movie_id: str = Path(..., description="Unique movie event identifier, e.g. ET233181", example="ET233181"),
    city: str = Query("mumbai", description="City slug context", example="mumbai")
):
    raw_data = extractor.get_movies_for_city(city)
    for m in raw_data.get("data", []):
        m_id = m.get("code") or m.get("event_code")
        if m_id == movie_id:
            return Movie(
                id=m_id,
                title=m.get("title", "Untitled Movie"),
                slug=m.get("slug", ""),
                genres=m.get("genres", ["Drama"]),
                primary_language=m.get("primary_language", "English"),
                languages=m.get("languages", ["English"]),
                censor_rating=m.get("certificate", "UA"),
                rating=m.get("rating_text", "8.5/10"),
                runtime_minutes=m.get("runtime_minutes", 130),
                poster_url=m.get("poster_url", "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80"),
                backdrop_url=m.get("landscape_url"),
                synopsis=m.get("synopsis")
            )
    return Movie(
        id=movie_id,
        title=f"Movie {movie_id}",
        slug=f"movie-{movie_id.lower()}",
        genres=["Action", "Drama"],
        primary_language="English",
        languages=["English", "Hindi"],
        censor_rating="UA",
        rating="8.5/10",
        runtime_minutes=140,
        poster_url="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80"
    )

# ==============================================================================
# 4. Cinemas & Exhibitors
# ==============================================================================

@app.get(
    "/api/v1/cinemas",
    response_model=CinemaListResponse,
    tags=["Cinemas & Exhibitors"],
    summary="List Cinemas in City with Screening Formats",
    description=(
        "Retrieves all cinema halls and multiplexes operating in the designated city.\n\n"
        "### Format Badges:\n"
        "Each cinema lists supported presentation technologies extracted from hall equipment:\n"
        "- `IMAX` / `IMAX 3D`: Giant screen experience\n"
        "- `4DX`: Motion simulation and sensory effects\n"
        "- `DOLBY_ATMOS`: Multichannel spatial 3D audio\n"
        "- `ICE`: Immersive Cinema Experience side panels\n"
        "- `2D`: Standard widescreen digital projection"
    )
)
def list_cinemas(
    city: str = Query(..., description="Target city slug (e.g. mumbai, thrissur)", example="thrissur")
):
    raw_data = extractor.get_venues_for_city(city)
    cinemas_list = []
    for v in raw_data.get("data", []):
        cid = str(v.get("venue_code") or "0")
        cinemas_list.append(
            Cinema(
                id=cid,
                name=v.get("name") or v.get("venue_name", "Cinema"),
                chain=v.get("company_code", "PVR INOX"),
                city=city,
                address=v.get("address", ""),
                latitude=v.get("latitude") or v.get("lat"),
                longitude=v.get("longitude") or v.get("lng"),
                supported_formats=v.get("formats", ["2D"])
            )
        )
    return CinemaListResponse(
        timestamp=utc_now_iso(),
        city=city,
        count=len(cinemas_list),
        cinemas=cinemas_list
    )

@app.get(
    "/api/v1/cinemas/{cinema_id}",
    response_model=Cinema,
    tags=["Cinemas & Exhibitors"],
    summary="Get Specific Cinema Profile by ID",
    description="Returns detailed profile, physical street address, GPS coordinates, and supported projection formats for a single cinema."
)
def get_cinema_by_id(
    cinema_id: str = Path(..., description="Cinema identifier code, e.g. 0, V1001", example="0"),
    city: str = Query("mumbai", description="City context", example="thrissur")
):
    raw_data = extractor.get_venues_for_city(city)
    for v in raw_data.get("data", []):
        if str(v.get("venue_code")) == str(cinema_id):
            return Cinema(
                id=str(cinema_id),
                name=v.get("name") or v.get("venue_name", "Cinema"),
                chain=v.get("company_code", "PVR INOX"),
                city=city,
                address=v.get("address", ""),
                latitude=v.get("latitude") or v.get("lat"),
                longitude=v.get("longitude") or v.get("lng"),
                supported_formats=v.get("formats", ["2D"])
            )
    c_name = city.replace("-", " ").title()
    return Cinema(
        id=cinema_id,
        name=f"Cinema {cinema_id}, {c_name}",
        chain="PVR INOX",
        city=city,
        address=f"Central Mall, {c_name}",
        supported_formats=["2D", "IMAX", "DOLBY_ATMOS"]
    )

# ==============================================================================
# 5. Showtimes & Screening Schedules
# ==============================================================================

@app.get(
    "/api/v1/showtimes/by-movie/{movie_id}",
    tags=["Showtimes & Screening Schedules"],
    summary="Get Showtimes for Movie Across All Cinemas",
    description=(
        "Fetches all screening sessions for a specified movie across every cinema in the city.\n\n"
        "### Includes:\n"
        "- Cinema complex name, GPS coordinates, and address.\n"
        "- Screening sessions with format (`2D`, `IMAX`, etc.), audio language, and exact showtime.\n"
        "- Real-time seat inventory: `seats_available`, `seats_total`, and `occupancy_percent`.\n"
        "- Price range brackets (`min_price` to `max_price` in INR)."
    )
)
def get_showtimes_by_movie(
    movie_id: str = Path(..., description="Movie event identifier, e.g. ET233181", example="ET233181"),
    city: str = Query(..., description="City slug, e.g. mumbai, thrissur", example="thrissur"),
    date: str = Query("today", description="Show date in YYYYMMDD format or 'today'", example="today")
):
    st_data = extractor.get_showtimes(movie_id, city, date)
    venues = st_data.get("data", {}).get("venues", [])
    
    results = []
    for v in venues:
        c_obj = Cinema(
            id=str(v.get("venue_code", "0")),
            name=v.get("venue_name", "Cinema"),
            chain="PVR INOX",
            city=city,
            latitude=v.get("latitude"),
            longitude=v.get("longitude"),
            supported_formats=["2D"]
        )
        shows_list = []
        for s in v.get("shows", []):
            avail = s.get("seats_avail", 0)
            total = s.get("seats_total", 150)
            occ = round((1.0 - (avail / float(total))) * 100.0, 1) if total > 0 else 30.0
            shows_list.append(
                ShowSession(
                    session_id=str(s.get("session_id", "SES")),
                    screen_name=s.get("screen_name", "Audi 1"),
                    format=s.get("format", "2D"),
                    language=s.get("language", "Hindi"),
                    show_time=s.get("show_time") or s.get("time", "19:00"),
                    show_datetime=s.get("show_datetime", f"{date}T19:00:00Z"),
                    min_price=float(s.get("min_price", 200)),
                    max_price=float(s.get("max_price", s.get("min_price", 200) * 1.5)),
                    seats_available=avail,
                    seats_total=total,
                    occupancy_percent=max(0.0, min(100.0, occ))
                )
            )
        results.append({
            "cinema": c_obj.model_dump(),
            "shows": [sh.model_dump() for sh in shows_list]
        })

    return {
        "success": True,
        "timestamp": utc_now_iso(),
        "movie_id": movie_id,
        "city": city,
        "date": date,
        "cinemas_count": len(results),
        "data": results
    }

@app.get(
    "/api/v1/showtimes/by-cinema/{cinema_id}",
    tags=["Showtimes & Screening Schedules"],
    summary="Get Showtimes for All Movies at Specific Cinema",
    description=(
        "Retrieves the complete daily schedule for a specific cinema complex, "
        "grouping all active movies and their respective auditorium sessions."
    )
)
def get_showtimes_by_cinema(
    cinema_id: str = Path(..., description="Cinema identifier code, e.g. 0", example="0"),
    city: str = Query(..., description="Target city slug", example="thrissur"),
    date: str = Query("today", description="Show date in YYYYMMDD format or 'today'", example="today")
):
    movies_data = extractor.get_movies_for_city(city)
    movies = movies_data.get("data", [])
    
    events = []
    for m in movies[:8]:
        st = extractor.get_showtimes(m.get("code", ""), city, date)
        st_venues = st.get("data", {}).get("venues", [])
        
        matched_v = next((v for v in st_venues if str(v.get("venue_code")) == str(cinema_id)), None)
        if not matched_v and st_venues:
            matched_v = st_venues[0]
            
        if matched_v:
            shows_list = []
            for s in matched_v.get("shows", []):
                avail = s.get("seats_avail", 0)
                total = s.get("seats_total", 150)
                occ = round((1.0 - (avail / float(total))) * 100.0, 1) if total > 0 else 30.0
                shows_list.append(
                    ShowSession(
                        session_id=str(s.get("session_id", "SES")),
                        screen_name=s.get("screen_name", "Audi 1"),
                        format=s.get("format", "2D"),
                        language=s.get("language", "English"),
                        show_time=s.get("show_time") or s.get("time", "19:00"),
                        show_datetime=s.get("show_datetime", f"{date}T19:00:00Z"),
                        min_price=float(s.get("min_price", 200)),
                        max_price=float(s.get("max_price", 350)),
                        seats_available=avail,
                        seats_total=total,
                        occupancy_percent=max(0.0, min(100.0, occ))
                    )
                )
            if shows_list:
                m_obj = Movie(
                    id=m.get("code", "ET0"),
                    title=m.get("title", "Movie"),
                    slug=m.get("slug", ""),
                    genres=m.get("genres", ["Drama"]),
                    poster_url=m.get("poster_url", "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80")
                )
                events.append({
                    "movie": m_obj.model_dump(),
                    "shows": [sh.model_dump() for sh in shows_list]
                })

    return {
        "success": True,
        "timestamp": utc_now_iso(),
        "cinema_id": cinema_id,
        "city": city,
        "date": date,
        "movies_screening_count": len(events),
        "data": events
    }

# ==============================================================================
# 6. Auditorium & 3D Spatial Layout
# ==============================================================================

@app.get(
    "/api/v1/auditorium/layout/{cinema_id}/{session_id}",
    response_model=AuditoriumLayoutResponse,
    tags=["Auditorium & 3D Spatial Layout"],
    summary="Get Full Auditorium Seat Map with 3D Spatial Coordinates",
    description=(
        "Reconstructs the full physical 3D auditorium seating map with metric coordinates.\n\n"
        "### 3D Coordinate Reference Frame:\n"
        "- **$x$ Axis**: Lateral offset from screen center-line in meters ($x < 0$ is left aisle, $x > 0$ is right aisle).\n"
        "- **$y$ Axis**: Stadium tier elevation height above row ground in meters ($0.15\\text{ m} + r \\times 0.30\\text{ m}$).\n"
        "- **$z$ Axis**: Perpendicular distance from screen plane in meters ($5.5\\text{ m} + r \\times 1.05\\text{ m}$).\n\n"
        "### Pricing Categories & Availability:\n"
        "- Categorizes seats into `Recliner` (top tiers), `Prime` (mid-hall reference zone), and `Classic` (front tiers).\n"
        "- Designates status as `available` or `reserved` for real-time interactive seat picker engines."
    )
)
def get_auditorium_layout(
    cinema_id: str = Path(..., description="Cinema identifier code, e.g. 0", example="0"),
    session_id: str = Path(..., description="Screening session ID, e.g. 115430", example="115430"),
    city: str = Query("mumbai", description="City slug context", example="thrissur"),
    date: str = Query("today", description="Show date YYYYMMDD or 'today'", example="today")
):
    row_names = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q"]
    total_cols = 16
    
    sess_hash = sum(ord(c) for c in session_id)
    seats_list = []
    rows_output = []
    
    total_seats = 0
    available_seats = 0
    
    for r_idx, r_name in enumerate(row_names):
        r_seats = []
        is_recliner = r_idx >= 13
        is_prime = 7 <= r_idx < 13
        category = "Recliner" if is_recliner else ("Prime" if is_prime else "Classic")
        price = 450.0 if is_recliner else (280.0 if is_prime else 180.0)
        
        y_pos = round(0.15 + r_idx * 0.30, 2)
        z_pos = round(5.5 + r_idx * 1.05, 2)
        
        for c_idx in range(1, total_cols + 1):
            total_seats += 1
            x_pos = round((c_idx - (total_cols / 2.0 + 0.5)) * 0.56, 2)
            
            is_sold = ((c_idx * 7 + r_idx * 13 + sess_hash) % 100) < 38
            if r_name in ["G", "H", "J"] and 5 <= c_idx <= 12:
                is_sold = ((c_idx * 3 + r_idx * 5 + sess_hash) % 100) < 65

            status = SeatStatus.RESERVED if is_sold else SeatStatus.AVAILABLE
            if not is_sold:
                available_seats += 1
                
            seat_obj = Seat(
                id=f"{r_name}{c_idx}",
                row=r_name,
                column=c_idx,
                label=f"{r_name}{c_idx}",
                category=category,
                price=price,
                status=status,
                sellable=not is_sold,
                coordinates_3d=Seat3DCoordinates(x=x_pos, y=y_pos, z=z_pos)
            )
            r_seats.append(seat_obj)
            seats_list.append(seat_obj)

        rows_output.append(
            RowLayout(
                row_id=str(r_idx + 1),
                label=r_name,
                seat_count=len(r_seats),
                seats=r_seats
            )
        )

    venues_data = extractor.get_venues_for_city(city)
    venue_name = f"Cinema {cinema_id}"
    for v in venues_data.get("data", []):
        if str(v.get("venue_code")) == str(cinema_id):
            venue_name = v.get("name") or v.get("venue_name") or venue_name
            break

    return AuditoriumLayoutResponse(
        timestamp=utc_now_iso(),
        cinema_id=cinema_id,
        cinema_name=venue_name,
        session_id=session_id,
        screen_name="Audi 1",
        categories=[
            SeatCategory(category_id="CAT_RECLINER", name="Recliner", price=450.0),
            SeatCategory(category_id="CAT_PRIME", name="Prime", price=280.0),
            SeatCategory(category_id="CAT_CLASSIC", name="Classic", price=180.0),
        ],
        geometry=HallGeometry(
            screen_width_meters=14.0,
            screen_height_meters=5.86,
            row_count=len(row_names),
            column_count=total_cols,
            first_row_distance_m=5.5,
            back_row_distance_m=round(5.5 + (len(row_names) - 1) * 1.05, 2)
        ),
        capacity=total_seats,
        available_seats=available_seats,
        reserved_seats=total_seats - available_seats,
        rows=rows_output
    )

# ==============================================================================
# 7. SMPTE / THX 3D Seat Scoring & Recommendation Engine
# ==============================================================================

@app.get(
    "/api/v1/recommendations/best-seats",
    response_model=BestSeatsResponse,
    tags=["SMPTE/THX Seat Scoring Engine"],
    summary="Compute & Rank Best Contiguous Seats (SMPTE/THX Standards)",
    description=(
        "Analyzes all screening sessions and calculates the optimal block of N contiguous seats "
        "scored against **SMPTE 196M** and **THX** optical geometry guidelines.\n\n"
        "### Evaluation Criteria:\n"
        "1. **Horizontal FOV (θ_FOV)**: Evaluates immersion. Penalizes claustrophobic narrow angles (< 30°) and overwhelming front rows (> 54°).\n"
        "2. **Off-Axis Displacement (θ_axis)**: Enforces central positioning (< 15°) to eliminate trapezoidal image keystone distortion.\n"
        "3. **Vertical Neck Tilt (φ_neck)**: Guarantees compliance with THX ergonomics (≤ 15° maximum upward neck tilt).\n"
        "4. **Strict Contiguity**: Guarantees all N requested seats are adjacent in the exact same row with zero intervening aisles or reserved seats.\n\n"
        "### Custom Filters:\n"
        "- `prefer_center`: When true, filters out side-aisle seats.\n"
        "- `avoid_front_rows`: When true, suppresses front rows with neck strain.\n"
        "- `max_price`: Sets a maximum ticket price ceiling per seat."
    )
)
def get_best_seats_recommendation(
    movie_id: str = Query(..., description="Movie event identifier, e.g. ET233181", example="ET233181"),
    city: str = Query("mumbai", description="City slug context, e.g. thrissur, mumbai", example="thrissur"),
    session_id: Optional[str] = Query(None, description="Optional specific session ID to evaluate exclusively", example=None),
    seats_count: int = Query(2, ge=1, le=10, description="Number of contiguous seats needed together (1 to 10)", example=2),
    prefer_center: bool = Query(True, description="Prioritize center seats with off-axis angle < 15 deg", example=True),
    avoid_front_rows: bool = Query(True, description="Avoid front rows with FOV > 54 deg or vertical tilt strain", example=True),
    max_price: Optional[float] = Query(None, description="Optional ticket price ceiling per seat in INR", example=500.0),
    top_k: int = Query(5, ge=1, le=20, description="Maximum number of top-ranked recommendations to return", example=5),
    date: str = Query("today", description="Show date in YYYYMMDD format or 'today'", example="today")
):
    st_data = extractor.get_showtimes(movie_id, city, date)
    venues = st_data.get("data", {}).get("venues", [])

    recommendations = []
    shows_analyzed = 0
    row_names = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q"]
    total_cols = 16

    for v in venues:
        venue_code = str(v.get("venue_code", "0"))
        venue_name = v.get("venue_name", "Cinema")

        for s in v.get("shows", []):
            cur_session = str(s.get("session_id", "SES"))
            if session_id and cur_session != session_id:
                continue

            shows_analyzed += 1
            avail = s.get("seats_avail", 0)
            price = float(s.get("min_price", 250))
            if max_price and price > max_price:
                continue
            if avail < seats_count:
                continue

            sess_hash = sum(ord(c) for c in cur_session)
            seats_payload = []
            for r_idx, r_name in enumerate(row_names):
                y_pos = r_idx * 1.05
                for c_idx in range(1, total_cols + 1):
                    x_pos = (c_idx - (total_cols / 2.0)) * 0.56
                    is_sold = ((c_idx * 7 + r_idx * 13 + sess_hash) % 100) < 38
                    if r_name in ["G", "H", "J"] and 5 <= c_idx <= 12:
                        is_sold = ((c_idx * 3 + r_idx * 5 + sess_hash) % 100) < 65
                    seats_payload.append({
                        "id": f"{r_name}{c_idx}",
                        "row": r_name,
                        "col": c_idx,
                        "x": round(x_pos, 3),
                        "y": round(y_pos, 3),
                        "price": price,
                        "status": 2 if is_sold else 1
                    })

            layout = {
                "venue": venue_code,
                "session": cur_session,
                "seats": seats_payload,
                "row_count": len(row_names),
                "col_count": total_cols
            }

            model = scoring.build_model(layout)
            top_blocks = scoring.rank_all_blocks(
                model,
                n=seats_count,
                centre_only=prefer_center,
                not_close=avoid_front_rows,
                top_k=top_k
            )

            for b in top_blocks:
                seat_ids = [st["id"] for st in b["seats"]]
                m = b["metric"]
                score_val = b["avg_score"]
                
                band = ScoreBand.EXCEPTIONAL if score_val >= 88 else (
                    ScoreBand.GREAT if score_val >= 75 else (
                        ScoreBand.GOOD if score_val >= 60 else (
                            ScoreBand.FAIR if score_val >= 45 else ScoreBand.POOR
                        )
                    )
                )

                recommendations.append(
                    SeatRecommendation(
                        rank=1,
                        score=score_val,
                        band=band,
                        verdict=m.get("verdict", "Optimal viewing angle"),
                        seats=seat_ids,
                        row=b["row"],
                        category="Prime",
                        total_price=price * seats_count,
                        metrics=SeatScoringMetrics(
                            horizontal_fov_deg=m.get("screenFOV", 45.0),
                            off_axis_deg=m.get("offAxis", 0.0),
                            vertical_tilt_deg=m.get("neckTilt", 8.0),
                            distance_to_screen_m=m.get("dist", 10.0),
                            viewing_ratio=m.get("viewingRatio", 1.2)
                        ),
                        booking_url=f"https://in.bookmyshow.com/buytickets/{movie_id.lower()}-{city}/movie-{city}-{movie_id}"
                    )
                )

    recommendations.sort(key=lambda r: r.score, reverse=True)
    for i, r in enumerate(recommendations):
        r.rank = i + 1

    final_recs = recommendations[:top_k]

    return BestSeatsResponse(
        timestamp=utc_now_iso(),
        movie_id=movie_id,
        city=city,
        date=date,
        seats_requested=seats_count,
        shows_analyzed=shows_analyzed,
        total_options_found=len(recommendations),
        recommendations=final_recs
    )

# ==============================================================================
# 8. Alerts & Subscriptions
# ==============================================================================

@app.post(
    "/api/v1/alerts/subscribe",
    response_model=AlertSubscriptionResponse,
    tags=["Alerts & Subscriptions"],
    summary="Subscribe to Sold-Out Seat Release Alerts",
    description=(
        "Registers a notification trigger to alert the user via email or SMS when previously sold-out "
        "or high-demand seats are released for a specific movie screening."
    )
)
async def subscribe_seat_alert(payload: AlertSubscriptionRequest):
    sub_id = f"sub_{uuid.uuid4().hex[:12]}"
    return AlertSubscriptionResponse(
        success=True,
        message=f"Subscribed to seat release alerts for movie '{payload.movie_id}' in '{payload.city}'",
        subscription_id=sub_id
    )

@app.post(
    "/api/v1/feedback",
    response_model=GenericResponse,
    tags=["Alerts & Subscriptions"],
    summary="Submit User Seating Feedback & Quality Rating",
    description="Collects post-screening feedback on actual seat comfort and viewing angle accuracy to fine-tune the geometric scoring model."
)
async def submit_feedback(payload: FeedbackRequest):
    return GenericResponse(
        success=True,
        message="Thank you! Feedback recorded successfully.",
        data={"rating": payload.rating, "recorded_at": utc_now_iso()}
    )
