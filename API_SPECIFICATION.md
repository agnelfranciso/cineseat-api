# CineSeat API — Complete Specification & Reference Manual

This document provides complete, low-level technical documentation for all endpoints exposed by the **CineSeat API** (`/api/v1/`).

---

## Base URLs & Documentation
- **API Base URL**: `http://127.0.0.1:8000`
- **Scalar Interactive Documentation**: `http://127.0.0.1:8000/docs` (or `/scalar`)
- **OpenAPI 3.1 JSON Specification**: `http://127.0.0.1:8000/openapi.json`

---

## 1. System Endpoints

### 1.1 Root Service Manifest
- **Method**: `GET /`
- **Description**: Returns basic service metadata, operational status, and a directory of available API resource endpoints.
- **Query Parameters**: None
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/"
  ```

### 1.2 Health Check
- **Method**: `GET /health` or `GET /api/v1/health`
- **Description**: Lightweight health status endpoint for load balancers (Kubernetes, AWS ALB, Docker HEALTHCHECK).
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/health"
  ```
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-11-17T08:00:00Z",
    "database_cities_count": 2167,
    "engine": "FastAPI + SMPTE/THX 3D Geometry Evaluator"
  }
  ```

---

## 2. Cities & Geo-Location

### 2.1 List Cities
- **Method**: `GET /api/v1/cities`
- **Description**: Retrieves paginated list of Indian cities and towns from the full 2,167+ city database.
- **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `query` | `string` | No | `null` | Case-insensitive filter on city name or state |
  | `metro_only` | `boolean` | No | `false` | When `true`, returns only tier-1 metropolitan cities |
  | `limit` | `integer` | No | `100` | Pagination page size ($1 \le \text{limit} \le 2500$) |
  | `offset` | `integer` | No | `0` | Number of records to skip |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/cities?query=pune&metro_only=true"
  ```

### 2.2 Nearest City by GPS Coordinates
- **Method**: `GET /api/v1/cities/nearest`
- **Description**: Computes great-circle distance using the Haversine formula to find the nearest cinema hub to the user's GPS coordinates.
- **Query Parameters**:
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `lat` | `float` | Yes | Latitude in degrees ($-90.0 \le \text{lat} \le 90.0$) |
  | `lng` | `float` | Yes | Longitude in degrees ($-180.0 \le \text{lng} \le 180.0$) |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/cities/nearest?lat=12.9716&lng=77.5946"
  ```

---

## 3. Movies Catalog

### 3.1 List Current Movies by City
- **Method**: `GET /api/v1/movies`
- **Description**: Extracts live movies currently screening in theatres within the designated city.
- **Query Parameters**:
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `city` | `string` | Yes | City slug (e.g. `mumbai`, `thrissur`, `bengaluru`) |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/movies?city=thrissur"
  ```

### 3.2 Get Movie Details
- **Method**: `GET /api/v1/movies/{movie_id}`
- **Description**: Returns detailed metadata for a specific movie identifier.
- **Path Parameters**:
  | Parameter | Type | Description |
  | :--- | :--- | :--- |
  | `movie_id` | `string` | Unique movie identifier (e.g. `ET233181`) |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/movies/ET233181?city=thrissur"
  ```

---

## 4. Cinemas & Exhibitors

### 4.1 List Cinemas by City
- **Method**: `GET /api/v1/cinemas`
- **Description**: Retrieves all cinema venues and complexes operating within the target city.
- **Query Parameters**:
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `city` | `string` | Yes | Target city slug |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/cinemas?city=thrissur"
  ```

---

## 5. Showtimes & Screening Schedules

### 5.1 Showtimes Grouped by Movie
- **Method**: `GET /api/v1/showtimes/by-movie/{movie_id}`
- **Description**: Shows all cinemas playing the specified movie on a given date, including screening formats, languages, seat availability, and pricing.
- **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `city` | `string` | Yes | - | City slug |
  | `date` | `string` | No | `today` | Date in `YYYYMMDD` format or `'today'` |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/showtimes/by-movie/ET233181?city=thrissur&date=today"
  ```

### 5.2 Showtimes Grouped by Cinema
- **Method**: `GET /api/v1/showtimes/by-cinema/{cinema_id}`
- **Description**: Shows all movies screening at a specific cinema complex on a given date.
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/showtimes/by-cinema/0?city=thrissur&date=today"
  ```

---

## 6. Auditorium Layout & 3D Geometry

### 6.1 Get Auditorium Seat Layout
- **Method**: `GET /api/v1/auditorium/layout/{cinema_id}/{session_id}`
- **Description**: Generates the complete spatial 3D seating grid for a screening hall with metric coordinates.
- **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `city` | `string` | No | `mumbai` | City context |
  | `date` | `string` | No | `today` | Show date |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/auditorium/layout/0/115430?city=thrissur"
  ```

---

## 7. SMPTE & THX Cinema Seat Scoring

### 7.1 Best Seats Recommendation
- **Method**: `GET /api/v1/recommendations/best-seats`
- **Description**: Computes contiguous seat block quality scores according to SMPTE 196M and THX cinema standards.
- **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `movie_id` | `string` | Yes | - | Movie identifier |
  | `city` | `string` | No | `mumbai` | City slug |
  | `session_id` | `string` | No | `null` | Optional specific session to evaluate |
  | `seats_count` | `integer` | No | `2` | Number of adjacent seats needed ($1 \le N \le 10$) |
  | `prefer_center`| `boolean` | No | `true` | When true, enforces off-axis angle $< 15^\circ$ |
  | `avoid_front_rows` | `boolean` | No | `true` | When true, eliminates rows with FOV $> 54^\circ$ |
  | `max_price` | `float` | No | `null` | Optional ticket price ceiling in INR |
  | `top_k` | `integer` | No | `5` | Number of ranked block options to return ($1 \le K \le 20$) |
- **cURL Example**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/v1/recommendations/best-seats?movie_id=ET233181&city=thrissur&seats_count=2"
  ```

---

## 8. Alerts & Subscriptions

### 8.1 Subscribe to Seat Drop Alerts
- **Method**: `POST /api/v1/alerts/subscribe`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "movie_id": "ET233181",
    "city": "thrissur",
    "cinema_id": "0",
    "date": "20261118"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "message": "Subscribed to seat release alerts for movie 'ET233181' in 'thrissur'",
    "subscription_id": "sub_a9b1c2d3e4f5"
  }
  ```

---

## 9. Error Handling

All client or server errors return appropriate HTTP status codes with structured error payloads:

```json
{
  "detail": "City 'invalid-city' not found in directory"
}
```

Standard HTTP status codes:
- `200 OK`: Request succeeded.
- `400 Bad Request`: Invalid parameter format or range.
- `404 Not Found`: Requested city, movie, cinema, or session not found.
- `422 Unprocessable Entity`: Request body or query validation failed.
- `500 Internal Server Error`: Server encountered an unexpected error.
