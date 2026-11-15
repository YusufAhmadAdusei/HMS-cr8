# Deployment: Render API + Vercel dashboard

The repository is configured for one FastAPI web service on Render and one Vite static site on Vercel. Deploy both from the same Git repository.

## 1. Deploy the backend on Render

1. Push the repository to GitHub and create a Render Blueprint from it. Render reads the root render.yaml.
2. Set CORS_ORIGINS to the exact Vercel site origin, for example https://hms-cr8.vercel.app. Do not include a trailing slash. To allow a Vercel preview origin too, add it as another comma-separated origin.
3. The Blueprint pins Python, installs requirements-render.txt, starts Uvicorn on Render's PORT, and checks /health.
4. The Blueprint mounts a persistent disk at /var/data; SQLite uses /var/data/hms.sqlite3 so records survive service restarts and deploys. This configuration uses Render's Starter plan because persistent disks are required for durable SQLite storage.
5. After deployment, save the service URL, for example https://hms-cr8-api.onrender.com. Confirm https://<render-service>/health returns JSON with "status":"ok".

OPENAI_API_KEY is optional and must be configured as a secret in Render if the assistant is to answer questions. Never add it to Vercel or a VITE_* variable. The model artifact is gitignored; if it is not supplied separately, the service runs with model status unavailable.

## 2. Deploy the frontend on Vercel

1. Import the same Git repository into Vercel.
2. Set the Root Directory to frontend. Leave the build command as npm run build and the output directory as dist; frontend/vercel.json contains these settings and an SPA fallback.
3. Add VITE_API_URL in Vercel's Production environment with the Render service URL, for example https://hms-cr8-api.onrender.com (no trailing slash). Add the same variable to Preview if previews should call the API.
4. Deploy and open the generated Vercel URL.
5. If you did not know the Vercel production origin when configuring Render, add it to Render's CORS_ORIGINS now and redeploy the backend.

Vite embeds VITE_API_URL into the frontend at build time, so changing it requires a new Vercel deployment. This URL is public by design; do not put credentials in frontend environment variables.

## 3. Verify the connected deployment

- Open the Vercel dashboard and confirm /health can be reached from the browser without a CORS error.
- Confirm the NASA panel displays historical RR-1 cabin temperature, relative humidity, and CO₂. When the Render database is empty, the panel imports NASA EDA records into SQLite; the bundled NASA reference file remains a display fallback.
- Use Ingest window to check VitalDB replay ingestion.
- Check Render logs if a request fails. The backend's /health response reports whether an anomaly model artifact was loaded.

Render starts with a new SQLite database; the local data/hms.sqlite3 file is not copied during deployment. NASA RR-1 data can be loaded by the dashboard. VitalDB records can be added through the existing ingestion controls or migrated separately if needed.
