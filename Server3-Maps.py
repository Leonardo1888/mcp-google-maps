"""
MCP Server 3 - Job Map Renderer (REMOTE)
Renders job offer locations on a Google Maps Static image with numbered markers.
Deployed remotely (e.g. Render.com) and connected via streamable-http.
Docs: https://developers.google.com/maps/documentation/maps-static/overview

Tools:
    render_jobs_map  — returns map URL + structured job list for the LLM to display
"""

import os, json, logging
from fastmcp import FastMCP
from pathlib import Path
from typing import List
from dotenv import load_dotenv

#  Absolute paths — file and .env are in the same directory
ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "server3-maps.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

#  Config
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

mcp3 = FastMCP("job-map-renderer")


#  Helpers

def _marker_label(index: int) -> str:
    """Returns a single-character label for a map marker (1-9, then A, B, C...)."""
    return str(index) if index <= 9 else chr(64 + index)

def _encode_location(location: str) -> str:
    """URL-encodes a location string for use in a Google Maps Static API URL."""
    return location.strip().replace(" ", "+").replace(",", "%2C")

def _build_map_url(jobs: List[dict]) -> str:
    """Builds a Google Maps Static API URL with one numbered red marker per job."""
    markers_parts = []
    for i, job in enumerate(jobs, 1):
        location = job.get("location", "").strip()
        if not location:
            continue
        label   = _marker_label(i)
        encoded = _encode_location(location)
        markers_parts.append(f"markers=color:red%7Clabel:{label}%7C{encoded}")

    markers_str = "&".join(markers_parts)
    return (
        f"https://maps.googleapis.com/maps/api/staticmap"
        f"?size=700x420"
        f"&maptype=roadmap"
        f"&{markers_str}"
        f"&key={GOOGLE_MAPS_API_KEY}"
    )


#  Tools

@mcp3.tool()
def render_jobs_map(jobs: List[dict]) -> str:
    """
    Generate a Google Maps image URL and structured job list to display after a job search.

    Call this AFTER search_jobs_by_skills or search_jobs_by_title returns results.
    Pass the jobOffers list directly from the job search response.

    IMPORTANT — after calling this tool, YOU must format the response like this:
    1. Show the map image using Markdown: ![Job Map](<map_url>)
    2. Show a numbered Markdown table with columns: #, Job Title, Company, Location
       - Use the "number" field as the row label (matches the marker on the map)
       - If a job has a "url", make the title a clickable Markdown link: [Title](url)
    Do not skip the image. Do not skip the table. Do not add extra commentary.

    Args:
        jobs: List of job offer dicts from search_jobs_by_skills or search_jobs_by_title.
              Each dict must have:
              - "title"    (str): job title
              - "company"  (str): company name
              - "location" (str): city/region, e.g. "Milano, Italy"
              - "url"      (str, optional): link to the job offer

    Returns:
        JSON with:
          - map_url (str): Google Maps Static image URL — embed as ![Job Map](<map_url>)
          - total   (int): number of jobs on the map
          - jobs    (list): [{number, title, company, location, url}]
        On error: JSON with {status: "error", error: "<message>"}
    """
    if not GOOGLE_MAPS_API_KEY:
        logging.error("render_jobs_map: GOOGLE_MAPS_API_KEY not set")
        return json.dumps({"status": "error", "error": "GOOGLE_MAPS_API_KEY not configured on the server."})

    if not jobs:
        logging.warning("render_jobs_map: called with empty jobs list")
        return json.dumps({"status": "error", "error": "No jobs provided."})

    valid_jobs = [j for j in jobs if j.get("location", "").strip()]
    if not valid_jobs:
        return json.dumps({"status": "error", "error": "No valid locations found in the job list."})

    logging.info(f"render_jobs_map: rendering {len(valid_jobs)} job(s)")

    map_url = _build_map_url(valid_jobs)

    structured_jobs = [
        {
            "number":   _marker_label(i + 1),
            "title":    j.get("title",    "N/A"),
            "company":  j.get("company",  "N/A"),
            "location": j.get("location", "N/A"),
            "url":      j.get("url", ""),
        }
        for i, j in enumerate(valid_jobs)
    ]

    logging.info("render_jobs_map: JSON response generated successfully")
    return json.dumps({
        "map_url": map_url,
        "total":   len(valid_jobs),
        "jobs":    structured_jobs,
    }, ensure_ascii=False)


@mcp3.tool()
def render_jobs_map_by_coordinates(jobs: List[dict]) -> str:
    """
    Generate a Google Maps image URL using coordinates when available, city name as fallback.

    For each job:
    - If "latitude" and "longitude" are valid floats → uses exact coordinates (precise)
    - If coordinates are missing or invalid → falls back to the "location" city string

    Call this AFTER search_jobs_by_skills returns results.
    Pass the full jobOffers list directly — no need to filter beforehand.

    IMPORTANT — after calling this tool, YOU must format the response like this:
    1. Show the map image using Markdown: ![Job Map](<map_url>)
    2. Show a numbered Markdown table with columns: #, Job Title, Company, Location
       - Use the "number" field as the row label (matches the marker on the map)
       - If a job has a "url", make the title a clickable Markdown link: [Title](url)
    Do not skip the image. Do not skip the table.

    Args:
        jobs: List of job offer dicts from search_jobs_by_skills.
              Each dict should have:
              - "title"     (str)  : job title
              - "company"   (str)  : company name
              - "location"  (str)  : city/region fallback string
              - "latitude"  (float): precise latitude  (optional)
              - "longitude" (float): precise longitude (optional)
              - "url"       (str)  : link to the job offer (optional)

    Returns:
        JSON with:
          - map_url          (str):  Google Maps Static image URL
          - total            (int):  total jobs on the map
          - by_coordinates   (int):  jobs placed using exact coordinates
          - by_location      (int):  jobs placed using city name fallback
          - skipped          (int):  jobs excluded (no coordinates AND no location)
          - jobs             (list): [{number, title, company, location, url}]
        On error: JSON with {status: "error", error: "<message>"}
    """
    if not GOOGLE_MAPS_API_KEY:
        logging.error("render_jobs_map_by_coordinates: GOOGLE_MAPS_API_KEY not set")
        return json.dumps({"status": "error", "error": "GOOGLE_MAPS_API_KEY not configured on the server."})

    if not jobs:
        logging.warning("render_jobs_map_by_coordinates: called with empty jobs list")
        return json.dumps({"status": "error", "error": "No jobs provided."})

    markers_parts = []
    valid_jobs = []
    by_coordinates = 0
    by_location = 0
    skipped = 0

    for i, job in enumerate(jobs, 1):
        label = _marker_label(i)
        lat = job.get("latitude")
        lng = job.get("longitude")
        location = job.get("location", "").strip()

        if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            # Precise coordinates available
            markers_parts.append(f"markers=color:red%7Clabel:{label}%7C{lat},{lng}")
            by_coordinates += 1
            valid_jobs.append(job)
            logging.info(f"render_jobs_map_by_coordinates: '{job.get('title')}' → coords ({lat},{lng})")
        elif location:
            # Fallback to city name
            encoded = _encode_location(location)
            markers_parts.append(f"markers=color:red%7Clabel:{label}%7C{encoded}")
            by_location += 1
            valid_jobs.append(job)
            logging.info(f"render_jobs_map_by_coordinates: '{job.get('title')}' → city fallback '{location}'")
        else:
            skipped += 1
            logging.info(f"render_jobs_map_by_coordinates: skipping '{job.get('title')}' — no coords or location")

    if not valid_jobs:
        return json.dumps({"status": "error", "skipped": skipped, "error": "No jobs could be placed on the map."})

    map_url = (
        f"https://maps.googleapis.com/maps/api/staticmap"
        f"?size=700x420"
        f"&maptype=roadmap"
        f"&{'&'.join(markers_parts)}"
        f"&key={GOOGLE_MAPS_API_KEY}"
    )

    structured_jobs = [
        {
            "number":   _marker_label(i + 1),
            "title":    j.get("title",    "N/A"),
            "company":  j.get("company",  "N/A"),
            "location": j.get("location", "N/A"),
            "url":      j.get("url", ""),
        }
        for i, j in enumerate(valid_jobs)
    ]

    logging.info(f"render_jobs_map_by_coordinates: done — {by_coordinates} coords, {by_location} city, {skipped} skipped")
    return json.dumps({
        "map_url":        map_url,
        "total":          len(valid_jobs),
        "by_coordinates": by_coordinates,
        "by_location":    by_location,
        "skipped":        skipped,
        "jobs":           structured_jobs,
    }, ensure_ascii=False)


#  Entrypoint

if __name__ == "__main__":
    mcp3.run(transport="http", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))