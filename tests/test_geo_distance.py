import unittest
from types import SimpleNamespace

from app.routers.providers import haversine_distance_km, _sort_by_distance


class GeoDistanceTests(unittest.TestCase):
    def test_same_coordinates_are_zero_meters(self):
        distance_m = haversine_distance_km(11.153344, 7.657015, 11.153344, 7.657015) * 1000

        self.assertAlmostEqual(distance_m, 0.0, places=6)

    def test_coordinates_around_fifty_to_one_hundred_meters_apart(self):
        origin = (11.153344, 7.657015)
        fifty_m_north = (11.153794, 7.657015)
        one_hundred_m_north = (11.154244, 7.657015)

        self.assertAlmostEqual(
            haversine_distance_km(*origin, *fifty_m_north) * 1000,
            50.0,
            delta=1.0,
        )
        self.assertAlmostEqual(
            haversine_distance_km(*origin, *one_hundred_m_north) * 1000,
            100.1,
            delta=1.0,
        )

    def test_coordinates_around_one_to_two_kilometers_apart(self):
        distance_m = haversine_distance_km(
            11.153344,
            7.657015,
            11.166844,
            7.657015,
        ) * 1000

        self.assertAlmostEqual(distance_m, 1501.1, delta=5.0)

    def test_distance_sorting_uses_unrounded_raw_distance(self):
        origin = (11.153344, 7.657015)
        providers = [
            SimpleNamespace(id=3, latitude=11.153794, longitude=7.657015, average_rating=5.0),
            SimpleNamespace(id=1, latitude=11.153389, longitude=7.657015, average_rating=1.0),
            SimpleNamespace(id=4, latitude=11.154244, longitude=7.657015, average_rating=5.0),
            SimpleNamespace(id=2, latitude=11.153434, longitude=7.657015, average_rating=1.0),
        ]

        sorted_providers = _sort_by_distance(providers, *origin)

        self.assertEqual([provider.id for provider in sorted_providers], [1, 2, 3, 4])
        self.assertLess(sorted_providers[0].distance_km, sorted_providers[1].distance_km)
        self.assertNotEqual(
            round(sorted_providers[0].distance_km, 2),
            sorted_providers[0].distance_km,
        )


if __name__ == "__main__":
    unittest.main()
