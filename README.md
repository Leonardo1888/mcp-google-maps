# MCP Google Maps — Job Map Renderer

A remote MCP server that renders job offer locations on a [Google Maps Static](https://developers.google.com/maps/documentation/maps-static/overview) image with numbered markers.

This server is part of the [mcp-job-search](https://github.com/Leonardo1888/mcp-job-search) project, where it acts as the **JOB-MAP-RENDERER** module. It is deployed remotely on Render.com and connected to the main pipeline via the MCP Streamable HTTP transport.

**Public endpoint**: `https://mcp-google-maps.onrender.com/mcp`

---

## Available tools

| Tool | Description |
|---|---|
| `render_jobs_map` | Renders a map using city name strings as marker positions |
| `render_jobs_map_by_coordinates` | Renders a map using exact coordinates when available, city name as fallback |

`render_jobs_map_by_coordinates` is the tool used by the main pipeline. For each job offer it places the marker at the exact `latitude`/`longitude` when present; otherwise it falls back to the `location` string. Offers with no coordinates and no valid city (e.g. country-only locations like "Italy") are excluded from the map but counted in the `skipped` field of the response.

Both tools return a JSON with `map_url` (Google Maps Static image URL), a structured job list and placement statistics.

---

## Project structure

```
mcp-google-maps/
├── Server3-Maps.py   # MCP server — map rendering logic
├── logs/
│   └── server3-maps.log
├── .env              # GOOGLE_MAPS_API_KEY (only on the deployment server)
└── requirements.txt
```

---

## Prerequisites

- Python 3.11+
- A [Google Maps Static API](https://developers.google.com/maps/documentation/maps-static/overview) key

---

## Configuration

The server reads `GOOGLE_MAPS_API_KEY` from the environment. When deploying on Render.com, set it as an environment variable in the Render dashboard — never commit it to the repository.

```env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
PORT=8000
```

---

## Running locally

```bash
pip install -r requirements.txt
python3 Server3-Maps.py
```

The server starts on `http://0.0.0.0:8000` (or the port defined by the `PORT` environment variable).

## Deploying on Render.com

Configure a **Web Service** with:
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `python3 Server3-Maps.py`
- **Environment variable**: `GOOGLE_MAPS_API_KEY=<your_key>`

Render automatically handles TLS and public HTTPS exposure.

---

## Connecting to the main pipeline

In the `config.json` of [mcp-job-search](https://github.com/Leonardo1888/mcp-job-search), the server is registered as a remote Streamable HTTP MCP server:

```json
"job-map-renderer": {
  "type": "streamable-http",
  "url": "https://mcp-google-maps.onrender.com/mcp"
}
```

No mcpo conversion is needed — the MCP client connects directly to the public endpoint.
