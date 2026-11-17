from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime

class ScoreBand(str, Enum):
    EXCEPTIONAL = "Exceptional"
    GREAT = "Great"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"

class SeatStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"

# 1. City Models
class City(BaseModel):
    slug: str = Field(..., description="Unique URL slug, e.g. mumbai, thrissur")
    name: str = Field(..., description="Display name of the city")
    state: str = Field(..., description="Indian state or union territory")
    is_metro: bool = Field(False, description="Whether this city is a tier-1 metro")
    latitude: Optional[float] = Field(None, description="GPS latitude")
    longitude: Optional[float] = Field(None, description="GPS longitude")

class CityListResponse(BaseModel):
    success: bool = True
    timestamp: str
    count: int
    cities: List[City]

class CityResponse(BaseModel):
    success: bool = True
    timestamp: str
    city: City

# 2. Movie Models
class Movie(BaseModel):
    id: str = Field(..., description="Unique movie identifier, e.g. ET233181")
    title: str = Field(..., description="Movie title")
    slug: str = Field(..., description="URL slug")
    genres: List[str] = Field(default_factory=list, description="Movie genres")
    primary_language: str = Field("English", description="Primary spoken language")
    languages: List[str] = Field(default_factory=list, description="Available audio tracks")
    censor_rating: str = Field("UA", description="Film certification (U, UA, A)")
    rating: Optional[str] = Field("8.5/10", description="Audience/critic rating")
    runtime_minutes: Optional[int] = Field(120, description="Duration in minutes")
    poster_url: str = Field(..., description="High-resolution portrait poster")
    backdrop_url: Optional[str] = Field(None, description="Landscape banner/backdrop")
    synopsis: Optional[str] = Field(None, description="Movie synopsis")

class MovieListResponse(BaseModel):
    success: bool = True
    timestamp: str
    city: str
    count: int
    movies: List[Movie]

# 3. Cinema Models
class Cinema(BaseModel):
    id: str = Field(..., description="Cinema hall identifier, e.g. V1001")
    name: str = Field(..., description="Full cinema name")
    chain: str = Field("PVR INOX", description="Theatre chain / exhibitor")
    city: str = Field(..., description="City slug")
    address: str = Field("", description="Street address and location")
    latitude: Optional[float] = Field(None, description="GPS latitude")
    longitude: Optional[float] = Field(None, description="GPS longitude")
    supported_formats: List[str] = Field(default_factory=lambda: ["2D"], description="Available screening formats")

class CinemaListResponse(BaseModel):
    success: bool = True
    timestamp: str
    city: str
    count: int
    cinemas: List[Cinema]

# 4. Showtime Models
class ShowSession(BaseModel):
    session_id: str = Field(..., description="Unique screening session ID")
    screen_name: str = Field("Audi 1", description="Screen/auditorium label")
    format: str = Field("2D", description="Presentation format (2D, 3D, IMAX, 4DX, etc.)")
    language: str = Field("Hindi", description="Audio language")
    show_time: str = Field(..., description="Local showtime, e.g. 19:30")
    show_datetime: str = Field(..., description="ISO 8601 show datetime")
    min_price: float = Field(..., description="Lowest available ticket price in INR")
    max_price: float = Field(..., description="Highest available ticket price in INR")
    seats_available: int = Field(..., description="Count of remaining open seats")
    seats_total: int = Field(..., description="Total seating capacity")
    occupancy_percent: float = Field(..., description="Percentage of seats sold (0-100)")

class MovieShowtimesGroup(BaseModel):
    cinema: Cinema
    shows: List[ShowSession]

class CinemaShowtimesGroup(BaseModel):
    movie: Movie
    shows: List[ShowSession]

class ShowtimesResponse(BaseModel):
    success: bool = True
    timestamp: str
    city: str
    date: str
    count: int
    groups: List[Any]

# 5. Auditorium & Seat Layout Models
class Seat3DCoordinates(BaseModel):
    x: float = Field(..., description="Distance from hall center-line in meters (negative = left, positive = right)")
    y: float = Field(..., description="Height off auditorium floor in meters")
    z: float = Field(..., description="Distance from cinema screen in meters")

class Seat(BaseModel):
    id: str = Field(..., description="Seat ID e.g. G12")
    row: str = Field(..., description="Row letter e.g. G")
    column: int = Field(..., description="Column number e.g. 12")
    label: str = Field(..., description="Display label e.g. G12")
    category: str = Field("Prime", description="Seat pricing category (Recliner, Prime, Classic)")
    price: float = Field(..., description="Ticket price in INR")
    status: SeatStatus = Field(SeatStatus.AVAILABLE, description="Status: available or reserved")
    sellable: bool = Field(True, description="Whether this seat can be booked")
    coordinates_3d: Seat3DCoordinates = Field(..., description="Spatial 3D auditorium coordinates")

class RowLayout(BaseModel):
    row_id: str
    label: str
    seat_count: int
    seats: List[Seat]

class SeatCategory(BaseModel):
    category_id: str
    name: str
    price: float

class HallGeometry(BaseModel):
    screen_width_meters: float = Field(12.0, description="Calculated cinema screen width")
    screen_height_meters: float = Field(5.1, description="Calculated cinema screen height")
    row_count: int = Field(..., description="Number of seating rows")
    column_count: int = Field(..., description="Number of seating columns")
    first_row_distance_m: float = Field(..., description="Distance from screen to front row in meters")
    back_row_distance_m: float = Field(..., description="Distance from screen to back row in meters")

class AuditoriumLayoutResponse(BaseModel):
    success: bool = True
    timestamp: str
    cinema_id: str
    cinema_name: str
    session_id: str
    screen_name: str
    categories: List[SeatCategory]
    geometry: HallGeometry
    capacity: int
    available_seats: int
    reserved_seats: int
    rows: List[RowLayout]

# 6. SMPTE / THX 3D Seat Scoring Models
class SeatScoringMetrics(BaseModel):
    horizontal_fov_deg: float = Field(..., description="Viewing field-of-view angle (SMPTE standard: >= 30 deg, optimal 45 deg)")
    off_axis_deg: float = Field(..., description="Horizontal displacement off center screen axis (optimal: < 15 deg)")
    vertical_tilt_deg: float = Field(..., description="Vertical neck tilt to screen center (THX maximum: <= 15 deg)")
    distance_to_screen_m: float = Field(..., description="Direct line-of-sight distance in meters")
    viewing_ratio: float = Field(..., description="Distance-to-screen-width ratio (D/W)")

class SeatRecommendation(BaseModel):
    rank: int = Field(..., description="Recommendation ranking (1 = best in auditorium)")
    score: int = Field(..., description="Overall seating quality score from 0 to 100")
    band: ScoreBand = Field(..., description="Quality band: Exceptional, Great, Good, Fair, Poor")
    verdict: str = Field(..., description="Human-readable assessment e.g. Best in hall, Great eye-level view")
    seats: List[str] = Field(..., description="Contiguous seat labels e.g. ['P11', 'P12']")
    row: str = Field(..., description="Auditorium row")
    category: str = Field(..., description="Pricing tier e.g. Prime")
    total_price: float = Field(..., description="Total combined price for all seats in block")
    metrics: SeatScoringMetrics = Field(..., description="Detailed SMPTE/THX geometric calculations")
    booking_url: Optional[str] = Field(None, description="Direct ticketing link")

class BestSeatsResponse(BaseModel):
    success: bool = True
    timestamp: str
    movie_id: str
    city: str
    date: str
    seats_requested: int
    shows_analyzed: int
    total_options_found: int
    recommendations: List[SeatRecommendation]

# 7. Ancillary & Subscriptions
class AlertSubscriptionRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    movie_id: str
    city: str
    cinema_id: Optional[str] = None
    date: str

class AlertSubscriptionResponse(BaseModel):
    success: bool = True
    message: str
    subscription_id: str

class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    seat_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class GenericResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
