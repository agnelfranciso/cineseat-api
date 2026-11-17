import unittest
from fastapi.testclient import TestClient
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

class TestCineSeatAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_service_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["service"], "CineSeat Cinema Seating & Showtimes Intelligence API")
        self.assertEqual(data["status"], "operational")
        self.assertIn("documentation", data)

    def test_01b_documentation_uis(self):
        for path in ["/docs", "/scalar", "/openapi.json"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Documentation UI failed for {path}")

    def test_02_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertGreaterEqual(data["database_cities_count"], 10)

    def test_03_list_cities(self):
        response = self.client.get("/api/v1/cities?limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["cities"]), 0)
        self.assertIn("slug", data["cities"][0])
        self.assertIn("name", data["cities"][0])

    def test_04_list_metro_cities(self):
        response = self.client.get("/api/v1/cities?metro_only=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["count"], 10)
        slugs = [c["slug"] for c in data["cities"]]
        self.assertIn("mumbai", slugs)
        self.assertIn("bengaluru", slugs)

    def test_05_get_city_details(self):
        response = self.client.get("/api/v1/cities/mumbai")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["city"]["slug"], "mumbai")
        self.assertEqual(data["city"]["name"], "Mumbai")

    def test_06_find_nearest_city(self):
        response = self.client.get("/api/v1/cities/nearest?lat=9.9312&lng=76.2673")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn(data["city"]["slug"], ["kochi", "thrissur"])

    def test_07_list_movies_by_city(self):
        response = self.client.get("/api/v1/movies?city=thrissur")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["city"], "thrissur")
        self.assertIsInstance(data["movies"], list)

    def test_08_list_cinemas_by_city(self):
        response = self.client.get("/api/v1/cinemas?city=thrissur")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["cinemas"]), 0)
        cinema = data["cinemas"][0]
        self.assertIn("id", cinema)
        self.assertIn("name", cinema)
        self.assertIn("supported_formats", cinema)

    def test_09_showtimes_by_movie(self):
        response = self.client.get("/api/v1/showtimes/by-movie/ET233181?city=thrissur")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["movie_id"], "ET233181")
        self.assertIn("data", data)

    def test_10_auditorium_layout(self):
        response = self.client.get("/api/v1/auditorium/layout/0/115430?city=thrissur")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["cinema_id"], "0")
        self.assertEqual(data["session_id"], "115430")
        self.assertEqual(len(data["rows"]), 15)
        self.assertEqual(len(data["categories"]), 3)
        first_seat = data["rows"][0]["seats"][0]
        self.assertIn("coordinates_3d", first_seat)
        self.assertIn("x", first_seat["coordinates_3d"])
        self.assertIn("y", first_seat["coordinates_3d"])
        self.assertIn("z", first_seat["coordinates_3d"])

    def test_11_best_seats_recommendation(self):
        response = self.client.get(
            "/api/v1/recommendations/best-seats?movie_id=ET233181&city=thrissur&seats_count=2&prefer_center=true&avoid_front_rows=true"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["movie_id"], "ET233181")
        self.assertEqual(data["seats_requested"], 2)
        self.assertGreater(len(data["recommendations"]), 0)
        top_pick = data["recommendations"][0]
        self.assertEqual(top_pick["rank"], 1)
        self.assertGreaterEqual(top_pick["score"], 70)
        self.assertEqual(len(top_pick["seats"]), 2)
        self.assertIn("metrics", top_pick)
        self.assertIn("horizontal_fov_deg", top_pick["metrics"])
        self.assertIn("off_axis_deg", top_pick["metrics"])
        self.assertIn("vertical_tilt_deg", top_pick["metrics"])

    def test_12_alert_subscription(self):
        payload = {
            "email": "test@example.com",
            "movie_id": "ET233181",
            "city": "thrissur",
            "date": "20261118"
        }
        response = self.client.post("/api/v1/alerts/subscribe", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("subscription_id", data)

    def test_13_feedback_submission(self):
        payload = {
            "rating": 5,
            "comment": "Outstanding seat recommendation accuracy!"
        }
        response = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_14_rate_limiting_behavior(self):
        # GitHub and local environments have no rate limits by default
        response = self.client.get("/api/v1/cities?limit=1")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
