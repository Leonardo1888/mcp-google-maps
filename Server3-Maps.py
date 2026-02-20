"""
MCP Server 3 - Job Map Renderer (REMOTE)
Renders job offer locations on a Google Maps Static image with numbered markers.
Deployed remotely (e.g. Render.com) and connected via streamable-http.
Docs: https://developers.google.com/maps/documentation/maps-static/overview

Tools:
    render_jobs_map  — generates a Markdown map image with numbered markers + legend
"""

import os, logging
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
    Render job offer locations on a Google Maps image with numbered markers.

    Call this AFTER search_jobs_by_skills or search_jobs_by_title returns results.
    Pass the jobOffers list directly from the job search response.
    Returns a Markdown string — output it exactly as-is without any modification.

    Args:
        jobs: List of job offer dicts. Each must contain:
              - "title"    (str): job title
              - "company"  (str): company name
              - "location" (str): city/region, e.g. "Milano, Italy"
              - "url"      (str, optional): link to the job offer

    Returns:
        Markdown string with a map image and a legend list.
        Output this EXACTLY as returned — do not reformat or summarize it.
    """
    if not GOOGLE_MAPS_API_KEY:
        logging.error("render_jobs_map: GOOGLE_MAPS_API_KEY not set")
        return "Error: GOOGLE_MAPS_API_KEY not configured on the server."

    if not jobs:
        logging.warning("render_jobs_map: called with empty jobs list")
        return "No jobs provided to render on the map."

    valid_jobs = [j for j in jobs if j.get("location", "").strip()]
    if not valid_jobs:
        return "No valid locations found in the job list."

    logging.info(f"render_jobs_map: rendering {len(valid_jobs)} job(s)")

    map_url = _build_map_url(valid_jobs)

    # Build legend as markdown list
    legend_lines = []
    for i, job in enumerate(valid_jobs, 1):
        label    = _marker_label(i)
        title    = job.get("title", "N/A")
        company  = job.get("company", "N/A")
        location = job.get("location", "N/A")
        url      = job.get("url", "")

        title_part = f"[{title}]({url})" if url else title
        legend_lines.append(f"**#{label}** {title_part} — {company} — {location}")

    legend = "\n".join(legend_lines)

    result = f"### 🗺️ Job Locations — {len(valid_jobs)} offer(s) found\n\n![Job Map]({map_url})\n\n{legend}"

    logging.info("render_jobs_map: markdown generated successfully")
    return result


#  Entrypoint

if __name__ == "__main__":
    mcp3.run(transport="http", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))