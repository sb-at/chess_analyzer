# ChessMirror - Chess Pattern Analyzer

**Tagline:** See your chess blind spots clearly

## Overview

ChessMirror analyzes patterns across hundreds of your games to reveal habits, blind spots, and recurring mistakes. Unlike traditional single-game analysis tools, ChessMirror provides meta-analysis across your entire game history to identify actionable patterns.

## Features

- **Game Import**: Automatic sync from Chess.com and Lichess
- **Pattern Detection**:
  - Tactical: Missed motifs, complexity analysis
  - Opening: Win rates, repeated mistakes
  - Strategic: Positional errors, piece placement
  - Time Management: Performance under pressure
  - Psychological: Tilt detection, rating differential performance
- **Insights Dashboard**: Visual representation of your top blind spots
- **Recommendations**: Prioritized training suggestions

## Tech Stack

- **Frontend**: React, TypeScript, Next.js, TailwindCSS
- **Backend**: Python, FastAPI
- **Databases**: PostgreSQL (users, patterns), MongoDB (games, analysis)
- **Chess Engine**: Stockfish (python-chess)
- **Message Queue**: Celery + Redis
- **Cache**: Redis

## Project Structure

```
chess_analyzer/
├── backend/          # Python FastAPI backend
│   ├── auth/         # Authentication services
│   ├── chess_import/ # Game import clients
│   ├── analysis/     # Stockfish integration
│   ├── pattern_detection/ # Pattern detection engines
│   └── api/          # API routes
├── frontend/         # React/Next.js frontend
│   ├── components/   # React components
│   ├── pages/        # Next.js pages
│   └── styles/       # CSS/Tailwind styles
├── database/         # Database schemas and migrations
├── docker/           # Docker configuration
└── tests/            # Test suites
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Stockfish chess engine

### Local Development

1. Clone the repository
```bash
git clone <repository-url>
cd chess_analyzer
```

2. Start services with Docker Compose
```bash
docker-compose up -d
```

3. Install backend dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. Install frontend dependencies
```bash
cd frontend
npm install
```

5. Run database migrations
```bash
cd backend
alembic upgrade head
```

6. Start development servers
```bash
# Backend (from backend/)
uvicorn main:app --reload

# Frontend (from frontend/)
npm run dev
```

## Environment Variables

Create a `.env` file in the root directory:

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/chessmirror
MONGODB_URL=mongodb://localhost:27017/chessmirror

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-secret-key-here

# Chess.com OAuth
CHESS_COM_CLIENT_ID=your-client-id
CHESS_COM_CLIENT_SECRET=your-client-secret
CHESS_COM_REDIRECT_URI=http://localhost:3000/auth/chess-com/callback

# Lichess OAuth
LICHESS_CLIENT_ID=your-client-id
LICHESS_REDIRECT_URI=http://localhost:3000/auth/lichess/callback

# Stockfish
STOCKFISH_PATH=/usr/games/stockfish
```

## Development Phases

- [x] Phase 1: Foundation (Setup, Auth, Game Import)
- [ ] Phase 2: Analysis Engine (Stockfish, Pattern Detection)
- [ ] Phase 3: Frontend Dashboard
- [ ] Phase 4: Polish & Testing
- [ ] Phase 5: Beta Launch

## License

MIT License
