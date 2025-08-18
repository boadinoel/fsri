# Argentis FSRI-Lite Pro

Food-System Risk Index (FSRI) API - Physical risk assessment for agricultural commodities.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.sample .env
   # Edit .env with your credentials
   ```

3. **Run the API:**
   ```bash
   uvicorn app:app --reload
   ```

4. **Run Streamlit UI (optional):**
   ```bash
   streamlit run streamlit_app/Home.py
   ```

## API Endpoints

- `GET /status` - Health check
- `GET /fsri` - Get FSRI score and risk breakdown
- `POST /log-decision` - Log decision (requires API key)
- `GET /export` - Export historical data as CSV

## Deployment

### Railway/Render
1. Connect your GitHub repo
2. Set environment variables from `.env.sample`
3. Deploy with `Procfile` configuration

### Manual
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Database Setup

Run the SQL in `supabase_schema.sql` in your Supabase SQL Editor.

## Testing

See curl examples below for API testing.
