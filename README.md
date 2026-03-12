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

See [SETUP.md](SETUP.md) for installation and setup instructions.

## Development Phases

- [x] Phase 1: Foundation (Setup, Auth, Game Import)
- [x] Phase 2: Analysis Engine (Stockfish, Pattern Detection)
- [x] Phase 3: Frontend Dashboard + InstanceViewer
- [ ] Phase 4: Polish & Testing
- [ ] Phase 5: Beta Launch

## License

MIT License
