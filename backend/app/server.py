import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from contextlib import asynccontextmanager
from .config import get_settings
from .config import Environment
from .routers import report_router, chunk_router, logging_router, message_router, chat_router
from .websockets import chat_ws_router
from .utils.logging import AppLogger

logger = AppLogger().get_logger()


# Context manager that will run before the server starts and after the server stops
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run things before the server starts
    
    # Important to yield after running things before the server starts
    yield

    # Run things before the server stops


# Create the FastAPI app
app = FastAPI()

# Get the settings
app_settings = get_settings()

# Add the CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set production settings
if app_settings.ENVIRONMENT == Environment.PRODUCTION.value:
    app.openapi_url = None
    app.docs_url = None
    app.redoc_url = None
    app.debug = False

# # Set development settings
# elif app_settings.ENVIRONMENT == Environment.DEVELOPMENT.value:
#     app.debug = True


# Route handlers


# Index route
@app.get("/")
async def index():
    return {"message": "Master Server API"}

app.include_router(report_router, prefix="/api")
app.include_router(chunk_router, prefix="/api")
app.include_router(message_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(logging_router, prefix="")
app.include_router(chat_ws_router, prefix="/ws")

# Mount the /static files
static_path = Path("./static")  
if not static_path.exists():  
    static_path.mkdir(parents=True, exist_ok=True)
    
    
app.mount("/static", StaticFiles(directory="static"), name="static") 

APP_LOG_PATH = "/api"

@app.middleware("http")
async def log_requests_and_process_time(request: Request, call_next):
    start_time = time.time()

    # Check if the request URL starts with /api
    if request.url.path.startswith(APP_LOG_PATH):
        # Log the incoming request
        logger.info(f"Received request: {request.method} {request.url.path}")

    # Proceed to handle the request
    response = await call_next(request)

    # Measure the time taken to process the request
    process_time = time.time() - start_time
    formatted_process_time = f"{process_time:.2f}"

    # Log the response details after processing the request
    if request.url.path.startswith(APP_LOG_PATH):
        logger.info(f"Request: {request.method} {request.url.path} completed in {formatted_process_time} seconds with status code {response.status_code}")
    
    return response
