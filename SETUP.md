# Setup Guide for ChessMirror

This guide will help you get the ChessMirror Chess Pattern Analyzer up and running locally.

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Docker and Docker Compose
- Git

## Quick Start with Docker

The easiest way to get started is using Docker Compose, which will set up all services automatically.

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd chess_analyzer
```

### 2. Create Environment File

Copy the example environment file and update it with your configuration:

```bash
cp .env.example .env
```

Edit `.env` and add your OAuth credentials (see OAuth Setup section below).

### 3. Start All Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- MongoDB on port 27017
- Redis on port 6379
- Backend API on port 8000
- Frontend on port 3000
- Celery worker for background jobs

### 4. Initialize the Database

The PostgreSQL database will be automatically initialized with the schema from `database/init.sql`.

For MongoDB, indexes will be created automatically when the backend starts.

### 5. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Manual Setup (Without Docker)

If you prefer to run services manually:

### 1. Start Infrastructure Services

You'll need PostgreSQL, MongoDB, and Redis running. You can use Docker for just these services:

```bash
docker-compose up -d postgres mongodb redis
```

Or install them locally following their official documentation.

### 2. Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database (if not using Docker)
psql -U chessmirror -d chessmirror -f ../database/init.sql

# Start the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start Celery Worker

In a new terminal:

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
celery -A tasks.celery_app worker --loglevel=info --concurrency=4
```

### 4. Set Up Frontend

In a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

## OAuth Setup

To enable authentication, you need to register OAuth applications with Chess.com and Lichess.

### Chess.com OAuth

1. Go to https://www.chess.com/clubs/forum/view/developer-community
2. Contact Chess.com developer support to request API access
3. They will provide you with:
   - Client ID
   - Client Secret
   - You'll need to specify your redirect URI: `http://localhost:3000/auth/chess-com/callback`

Add to your `.env` file:
```
CHESS_COM_CLIENT_ID=your-client-id
CHESS_COM_CLIENT_SECRET=your-client-secret
CHESS_COM_REDIRECT_URI=http://localhost:3000/auth/chess-com/callback
```

### Lichess OAuth

1. Go to https://lichess.org/account/oauth/app
2. Click "New OAuth App"
3. Fill in:
   - Name: ChessMirror Local Development
   - Redirect URI: `http://localhost:3000/auth/lichess/callback`
   - Description: Local development instance
4. Copy the Client ID

Add to your `.env` file:
```
LICHESS_CLIENT_ID=your-client-id
LICHESS_REDIRECT_URI=http://localhost:3000/auth/lichess/callback
```

## Stockfish Setup

The backend requires Stockfish for chess analysis.

### Docker

Stockfish is automatically installed in the Docker container.

### Manual Installation

#### Ubuntu/Debian
```bash
sudo apt-get install stockfish
```

#### macOS
```bash
brew install stockfish
```

#### Windows
1. Download from https://stockfishchess.org/download/
2. Extract to a location (e.g., `C:\stockfish\`)
3. Update `.env`:
```
STOCKFISH_PATH=C:\stockfish\stockfish.exe
```

## Troubleshooting

### Database Connection Issues

If you get database connection errors:

1. Make sure PostgreSQL is running:
```bash
docker-compose ps
```

2. Check the DATABASE_URL in `.env` matches your setup

3. Test connection:
```bash
psql -U chessmirror -d chessmirror -h localhost
```

### Frontend Can't Connect to Backend

1. Check that NEXT_PUBLIC_API_URL in `.env` is correct
2. Verify backend is running on port 8000
3. Check CORS settings in `backend/main.py`

### Celery Worker Not Processing Jobs

1. Make sure Redis is running
2. Check Celery worker logs
3. Verify REDIS_URL in `.env` is correct

## Next Steps

1. Import some games from Chess.com or Lichess
2. Wait for analysis to complete
3. View your patterns on the dashboard

For Phase 2 development (Stockfish analysis and pattern detection), see the implementation plan in `ImplementationPlan.md`.

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f worker
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (this will delete all data!)
docker-compose down -v
```

## Production Deployment

For production deployment, see `docker-compose.prod.yml` and update:

1. Change all passwords and secrets
2. Set up proper SSL certificates
3. Configure nginx reverse proxy
4. Set up monitoring and logging
5. Configure backups for databases
