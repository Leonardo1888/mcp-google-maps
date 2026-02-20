"""
MCP Server 3 - Job Map Renderer (REMOTE)
Renders job offer locations on a Google Maps Static image with numbered markers.
Deployed remotely (e.g. Render.com) and connected via streamable-http.
Docs: https://developers.google.com/maps/documentation/maps-static/overview

Tools:
    render_jobs_map  — generates an HTML map with numbered markers + legend table
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

def _build_legend_rows(jobs: List[dict]) -> str:
    """Builds HTML table rows for the legend below the map."""
    rows = ""
    for i, job in enumerate(jobs, 1):
        label    = _marker_label(i)
        title    = job.get("title",    "N/A")
        company  = job.get("company",  "N/A")
        location = job.get("location", "N/A")
        url      = job.get("url", "")

        title_cell = (
            f'<a href="{url}" target="_blank" style="color:#1a73e8;text-decoration:none;">{title}</a>'
            if url else title
        )
        rows += f"""
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:6px 10px;font-weight:bold;color:#d32f2f;font-size:15px;">#{label}</td>
          <td style="padding:6px 10px;">{title_cell}</td>
          <td style="padding:6px 10px;color:#555;">{company}</td>
          <td style="padding:6px 10px;color:#555;">{location}</td>
        </tr>"""
    return rows


#  Tools

@mcp3.tool()
def render_jobs_map(jobs: List[dict]) -> str:
    """
    Render job offer locations on a Google Maps image with numbered markers.

    Call this AFTER search_jobs_by_skills or search_jobs_by_title returns results.
    Pass the jobOffers list directly from the job search response.
    Each marker is numbered and corresponds to a row in the legend table below the map.

    Args:
        jobs: List of job offer dicts. Each must contain:
              - "title"    (str): job title
              - "company"  (str): company name
              - "location" (str): city/region, e.g. "Milano, Italy"
              - "url"      (str, optional): link to the job offer
              Example:
              [
                {"title": "Python Developer", "company": "Acme", "location": "Milano, Italy", "url": "https://..."},
                {"title": "Data Scientist",   "company": "Beta", "location": "Roma, Italy",   "url": "https://..."}
              ]

    Returns:
        HTML string with:
          - Google Maps Static image with numbered red markers (one per job)
          - Legend table: marker number -> job title (linked), company, location
        On error: plain HTML error message.
    """
    if not GOOGLE_MAPS_API_KEY:
        logging.error("render_jobs_map: GOOGLE_MAPS_API_KEY not set")
        return "<p style='color:red;'>Error: GOOGLE_MAPS_API_KEY not configured on the server.</p>"

    if not jobs:
        logging.warning("render_jobs_map: called with empty jobs list")
        return "<p>No jobs provided to render on the map.</p>"

    valid_jobs = [j for j in jobs if j.get("location", "").strip()]
    if not valid_jobs:
        return "<p>No valid locations found in the job list.</p>"

    logging.info(f"render_jobs_map: rendering {len(valid_jobs)} job(s)")

    map_url     = _build_map_url(valid_jobs)
    legend_rows = _build_legend_rows(valid_jobs)

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:740px;margin:0 auto;">
  <h3 style="margin-bottom:12px;">🗺️ Job Locations — {len(valid_jobs)} offer(s) found</h3>
  <img
    src="{map_url}"
    alt="Job locations map"
    width="100%"
    style="border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.18);display:block;"
  />
  <table style="width:100%;border-collapse:collapse;margin-top:14px;font-size:14px;">
    <thead>
      <tr style="background:#f5f5f5;text-align:left;">
        <th style="padding:8px 10px;">#</th>
        <th style="padding:8px 10px;">Job Title</th>
        <th style="padding:8px 10px;">Company</th>
        <th style="padding:8px 10px;">Location</th>
      </tr>
    </thead>
    <tbody>
      {legend_rows}
    </tbody>
  </table>
</div>
"""
    logging.info("render_jobs_map: HTML generated successfully")
    return html


# Entrypoint 

if __name__ == "__main__":
    mcp3.run(transport="http", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))