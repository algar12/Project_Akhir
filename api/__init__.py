"""
API Module — Unified Network Guard
====================================
REST API berbasis FastAPI — secure, terdokumentasi, production-ready.

Security layers:
  1. API Key auth via header X-API-Key (semua endpoint /api/v1/*)
  2. Rate limiting per IP — built-in (sliding window, tanpa dependency eksternal)
  3. CORS whitelist + regex origin LAN privat — hanya izinkan origin dashboard
  4. Trusted Host middleware — cegah Host header injection
  5. Secure HTTP headers (X-Content-Type-Options, X-Frame-Options, dll.)
  6. Input validation ketat via Pydantic (tipe + range + regex)
  7. Parameterized query via SQLAlchemy (no raw string SQL)
  8. WebSocket auth via query param ?token=<api_key>
"""
