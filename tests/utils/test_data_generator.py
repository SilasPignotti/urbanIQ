"""
Test data generation utilities for realistic Berlin geodata testing.

Provides utilities to generate realistic Berlin district boundaries, building data,
transport stops, and other geodata for comprehensive testing scenarios.
"""

import random
from datetime import timedelta
from typing import Any

import geopandas as gpd
from faker import Faker
from shapely.geometry import Point, Polygon

# Initialize Faker with German locale for realistic data
fake = Faker("de_DE")


class BerlinGeodataGenerator:
    """Generator for realistic Berlin geodata test scenarios."""

    # Berlin district coordinates and characteristics
    BERLIN_DISTRICTS = {
        "Charlottenburg-Wilmersdorf": {
            "center": (13.2846, 52.5057),
            "bounds": (13.2500, 52.4800, 13.3200, 52.5300),
            "characteristics": {"density": "high", "type": "mixed"},
        },
        "Friedrichshain-Kreuzberg": {
            "center": (13.4203, 52.5027),
            "bounds": (13.3800, 52.4800, 13.4600, 52.5300),
            "characteristics": {"density": "very_high", "type": "urban"},
        },
        "Lichtenberg": {
            "center": (13.4986, 52.5450),
            "bounds": (13.4500, 52.5200, 13.5500, 52.5700),
            "characteristics": {"density": "medium", "type": "residential"},
        },
        "Marzahn-Hellersdorf": {
            "center": (13.5916, 52.5450),
            "bounds": (13.5500, 52.5200, 13.6300, 52.5700),
            "characteristics": {"density": "medium", "type": "residential"},
        },
        "Mitte": {
            "center": (13.4050, 52.5200),
            "bounds": (13.3600, 52.5000, 13.4500, 52.5400),
            "characteristics": {"density": "very_high", "type": "central"},
        },
        "Neukölln": {
            "center": (13.4372, 52.4816),
            "bounds": (13.4000, 52.4600, 13.4700, 52.5000),
            "characteristics": {"density": "high", "type": "mixed"},
        },
        "Pankow": {
            "center": (13.4014, 52.5691),
            "bounds": (13.3500, 52.5400, 13.4500, 52.6000),
            "characteristics": {"density": "medium", "type": "residential"},
        },
        "Reinickendorf": {
            "center": (13.3280, 52.5770),
            "bounds": (13.2800, 52.5500, 13.3800, 52.6000),
            "characteristics": {"density": "low", "type": "suburban"},
        },
        "Spandau": {
            "center": (13.2004, 52.5370),
            "bounds": (13.1400, 52.5100, 13.2600, 52.5600),
            "characteristics": {"density": "low", "type": "suburban"},
        },
        "Steglitz-Zehlendorf": {
            "center": (13.2440, 52.4570),
            "bounds": (13.2000, 52.4300, 13.2900, 52.4800),
            "characteristics": {"density": "low", "type": "residential"},
        },
        "Tempelhof-Schöneberg": {
            "center": (13.3763, 52.4675),
            "bounds": (13.3400, 52.4400, 13.4100, 52.4900),
            "characteristics": {"density": "medium", "type": "mixed"},
        },
        "Treptow-Köpenick": {
            "center": (13.5764, 52.4575),
            "bounds": (13.5200, 52.4300, 13.6300, 52.4800),
            "characteristics": {"density": "low", "type": "green"},
        },
    }

    # Building types and characteristics
    BUILDING_TYPES = {
        "residential": {"heights": (8, 25), "frequency": 0.6},
        "commercial": {"heights": (15, 80), "frequency": 0.2},
        "industrial": {"heights": (6, 20), "frequency": 0.1},
        "public": {"heights": (10, 35), "frequency": 0.1},
    }

    # Transport stop types
    TRANSPORT_TYPES = {
        "s_bahn": {"names": ["S Pankow", "S Bornholmer Str", "S Wollankstr"], "frequency": 0.2},
        "u_bahn": {"names": ["U Vinetastr", "U Pankow"], "frequency": 0.2},
        "bus": {"names": ["Pankow Kirche", "Florastr", "Breite Str"], "frequency": 0.4},
        "tram": {"names": ["M1 Pankow", "M50 Hauptstr"], "frequency": 0.2},
    }

    def __init__(self, seed: int | None = None):
        """Initialize generator with optional random seed for reproducibility."""
        if seed:
            random.seed(seed)
            Faker.seed(seed)

    def generate_district_boundary(self, district_name: str) -> gpd.GeoDataFrame:
        """Generate realistic district boundary polygon.

        Args:
            district_name: Name of Berlin district

        Returns:
            GeoDataFrame with district boundary
        """
        if district_name not in self.BERLIN_DISTRICTS:
            raise ValueError(f"Unknown district: {district_name}")

        district_info = self.BERLIN_DISTRICTS[district_name]
        bounds = district_info["bounds"]

        # Create simplified polygon boundary
        coords = [
            (bounds[0], bounds[1]),  # SW
            (bounds[2], bounds[1]),  # SE
            (bounds[2], bounds[3]),  # NE
            (bounds[0], bounds[3]),  # NW
            (bounds[0], bounds[1]),  # Close polygon
        ]

        # Add some irregularity to make it more realistic
        irregular_coords = []
        for i, (lon, lat) in enumerate(coords[:-1]):  # Skip the closing point
            # Add small random offset
            offset_lon = random.uniform(-0.01, 0.01)
            offset_lat = random.uniform(-0.005, 0.005)
            irregular_coords.append((lon + offset_lon, lat + offset_lat))

        # Close the polygon
        irregular_coords.append(irregular_coords[0])

        boundary = Polygon(irregular_coords)

        data = {
            "bezirk_name": [district_name],
            "bezirk_id": [str(list(self.BERLIN_DISTRICTS.keys()).index(district_name) + 1).zfill(2)],
            "area_km2": [round(random.uniform(20, 120), 2)],
            "population": [random.randint(200000, 400000)],
            "density_type": [district_info["characteristics"]["density"]],
            "geometry": [boundary],
        }

        return gpd.GeoDataFrame(data, crs="EPSG:4326")

    def generate_buildings_data(
        self,
        district: str,
        count: int = 100,
        bbox: tuple[float, float, float, float] | None = None
    ) -> gpd.GeoDataFrame:
        """Generate realistic building data for a district.

        Args:
            district: District name
            count: Number of buildings to generate
            bbox: Optional bounding box for spatial filtering

        Returns:
            GeoDataFrame with building data
        """
        if district not in self.BERLIN_DISTRICTS:
            raise ValueError(f"Unknown district: {district}")

        district_info = self.BERLIN_DISTRICTS[district]
        district_bounds = bbox or district_info["bounds"]

        buildings = []
        for i in range(count):
            # Generate random location within district bounds
            lon = random.uniform(district_bounds[0], district_bounds[2])
            lat = random.uniform(district_bounds[1], district_bounds[3])

            # Choose building type based on frequency
            building_type = random.choices(
                list(self.BUILDING_TYPES.keys()),
                weights=[info["frequency"] for info in self.BUILDING_TYPES.values()]
            )[0]

            type_info = self.BUILDING_TYPES[building_type]
            height = random.uniform(*type_info["heights"])

            # Generate realistic attributes
            year_built = random.randint(1880, 2023)
            floors = max(1, int(height / 3.5))  # Approximate floors based on height

            building = {
                "feature_id": f"building_{district.lower()}_{i:04d}",
                "dataset_type": "gebaeude",
                "source_system": "berlin_geoportal",
                "bezirk": district,
                "geometry": Point(lon, lat),
                "original_attributes": {
                    "height": round(height, 1),
                    "type": building_type,
                    "year_built": year_built,
                    "floors": floors,
                    "address": fake.street_address(),
                    "roof_type": random.choice(["flat", "pitched", "mansard"]),
                }
            }
            buildings.append(building)

        return gpd.GeoDataFrame(buildings, crs="EPSG:4326")

    def generate_transport_stops_data(
        self,
        district: str,
        count: int = 50,
        bbox: tuple[float, float, float, float] | None = None
    ) -> gpd.GeoDataFrame:
        """Generate realistic transport stop data for a district.

        Args:
            district: District name
            count: Number of stops to generate
            bbox: Optional bounding box for spatial filtering

        Returns:
            GeoDataFrame with transport stop data
        """
        if district not in self.BERLIN_DISTRICTS:
            raise ValueError(f"Unknown district: {district}")

        district_info = self.BERLIN_DISTRICTS[district]
        district_bounds = bbox or district_info["bounds"]

        stops = []
        for i in range(count):
            # Generate random location within district bounds
            lon = random.uniform(district_bounds[0], district_bounds[2])
            lat = random.uniform(district_bounds[1], district_bounds[3])

            # Choose transport type based on frequency
            transport_type = random.choices(
                list(self.TRANSPORT_TYPES.keys()),
                weights=[info["frequency"] for info in self.TRANSPORT_TYPES.values()]
            )[0]

            type_info = self.TRANSPORT_TYPES[transport_type]
            stop_name = random.choice(type_info["names"]) + f" {i:02d}"

            stop = {
                "feature_id": f"stop_{district.lower()}_{transport_type}_{i:03d}",
                "dataset_type": "oepnv_haltestellen",
                "source_system": "openstreetmap",
                "bezirk": district,
                "geometry": Point(lon, lat),
                "original_attributes": {
                    "name": stop_name,
                    "transport_type": transport_type,
                    "platform": random.choice(["yes", "no"]),
                    "shelter": random.choice(["yes", "no"]),
                    "wheelchair": random.choice(["yes", "limited", "no"]),
                    "operator": self._get_transport_operator(transport_type),
                }
            }
            stops.append(stop)

        return gpd.GeoDataFrame(stops, crs="EPSG:4326")

    def generate_job_records(self, count: int = 10) -> list[dict[str, Any]]:
        """Generate realistic job records for testing.

        Args:
            count: Number of job records to generate

        Returns:
            List of job record dictionaries
        """
        jobs = []
        statuses = ["PENDING", "PROCESSING", "COMPLETED", "FAILED"]
        districts = list(self.BERLIN_DISTRICTS.keys())

        for i in range(count):
            created_at = fake.date_time_between(start_date="-30d", end_date="now")
            status = random.choice(statuses)

            # Adjust completion time based on status
            if status == "COMPLETED":
                completed_at = created_at + timedelta(minutes=random.randint(5, 60))
                progress = 100
            elif status == "PROCESSING":
                completed_at = None
                progress = random.randint(25, 90)
            elif status == "FAILED":
                completed_at = created_at + timedelta(minutes=random.randint(1, 30))
                progress = random.randint(10, 75)
            else:  # PENDING
                completed_at = None
                progress = 0

            # Generate realistic German requests
            district = random.choice(districts)
            datasets = random.sample(["gebaeude", "oepnv_haltestellen"], k=random.randint(1, 2))
            user_request = self._generate_german_request(district, datasets)

            job = {
                "id": f"job_{i:04d}_{fake.uuid4()[:8]}",
                "user_request": user_request,
                "bezirk": district,
                "datasets": datasets,
                "status": status,
                "progress": progress,
                "created_at": created_at,
                "completed_at": completed_at,
                "error_message": fake.sentence() if status == "FAILED" else None,
                "runtime_stats": self._generate_runtime_stats() if status == "COMPLETED" else None,
            }
            jobs.append(job)

        return jobs

    def generate_package_records(self, job_count: int = 5) -> list[dict[str, Any]]:
        """Generate realistic package records for testing.

        Args:
            job_count: Number of packages to generate

        Returns:
            List of package record dictionaries
        """
        packages = []

        for i in range(job_count):
            created_at = fake.date_time_between(start_date="-30d", end_date="now")
            file_size = random.randint(1024, 50 * 1024 * 1024)  # 1KB to 50MB

            package = {
                "id": f"package_{i:04d}_{fake.uuid4()[:8]}",
                "job_id": f"job_{i:04d}_{fake.uuid4()[:8]}",
                "file_path": f"/tmp/exports/geodata_package_{i:04d}.zip",
                "file_size": file_size,
                "download_count": random.randint(0, 50),
                "metadata_report": self._generate_metadata_report(),
                "created_at": created_at,
                "expires_at": created_at + timedelta(hours=24),
            }
            packages.append(package)

        return packages

    def _get_transport_operator(self, transport_type: str) -> str:
        """Get realistic transport operator based on type."""
        operators = {
            "s_bahn": "S-Bahn Berlin GmbH",
            "u_bahn": "BVG",
            "bus": "BVG",
            "tram": "BVG",
        }
        return operators.get(transport_type, "BVG")

    def _generate_german_request(self, district: str, datasets: list[str]) -> str:
        """Generate realistic German language requests."""
        templates = [
            f"{district} {{datasets}} für Stadtplanung",
            f"{{datasets}} in {district} für Mobilitätsanalyse",
            f"{district} {{datasets}} und Infrastrukturdaten",
            f"Geodaten {district}: {{datasets}}",
            f"{{datasets}} {district} für Verkehrsplanung",
        ]

        dataset_german = {
            "gebaeude": "Gebäude",
            "oepnv_haltestellen": "ÖPNV-Haltestellen",
        }

        datasets_german = " und ".join(dataset_german.get(d, d) for d in datasets)
        template = random.choice(templates)

        return template.format(datasets=datasets_german)

    def _generate_runtime_stats(self) -> dict[str, Any]:
        """Generate realistic runtime statistics."""
        return {
            "processing_time_seconds": random.randint(30, 300),
            "datasets_processed": random.randint(1, 3),
            "total_features": random.randint(100, 5000),
            "data_quality_score": round(random.uniform(0.7, 1.0), 3),
            "spatial_coverage_percent": round(random.uniform(85, 100), 1),
            "memory_usage_mb": round(random.uniform(50, 500), 1),
        }

    def _generate_metadata_report(self) -> str:
        """Generate realistic metadata report content."""
        return f"""# Geodatenpaket Metadaten-Bericht

## Übersicht
- **Erstellungsdatum**: {fake.date()}
- **Bezirk**: {random.choice(list(self.BERLIN_DISTRICTS.keys()))}
- **Datensätze**: {random.randint(1, 3)}
- **Gesamtfeatures**: {random.randint(100, 5000)}

## Datenqualität
- **Qualitätsbewertung**: {random.choice(['Sehr hoch', 'Hoch', 'Gut'])}
- **Vollständigkeit**: {random.randint(85, 100)}%
- **Räumliche Abdeckung**: {random.randint(90, 100)}%

## Verwendungshinweise
{fake.paragraph()}

## Technische Details
- **Koordinatensystem**: EPSG:25833
- **Format**: GeoJSON, Shapefile
- **Lizenz**: {random.choice(['CC BY 3.0 DE', 'ODbL'])}
"""
