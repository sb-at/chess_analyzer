# MongoDB Schema Documentation

## Database: chessmirror

### Collection: games

Stores individual chess games with analysis data.

```javascript
{
  _id: ObjectId,
  user_id: UUID (string), // References PostgreSQL users.id
  platform: "chess.com" | "lichess",
  game_id: String, // Platform-specific game ID
  pgn: String, // Full PGN notation
  date: Date,
  time_control: String, // e.g., "180+0", "600+5"
  white_player: String,
  black_player: String,
  white_rating: Number,
  black_rating: Number,
  result: String, // "1-0", "0-1", "1/2-1/2"
  user_color: "white" | "black",
  opening_name: String,
  opening_eco: String, // ECO code

  // Analysis data (populated after Stockfish analysis)
  moves: [{
    move_number: Number,
    move: String, // UCI notation
    san: String, // Standard algebraic notation
    fen_before: String,
    fen_after: String,
    time_left: Number, // seconds remaining
    evaluation: Number, // in centipawns from player's perspective
    best_move: String, // UCI notation
    is_blunder: Boolean,
    is_mistake: Boolean,
    is_inaccuracy: Boolean,
    centipawn_loss: Number,
    accuracy: Number // 0-100 score
  }],

  analyzed: Boolean,
  analyzed_at: Date,

  // Game statistics
  stats: {
    total_moves: Number,
    avg_accuracy: Number,
    blunders: Number,
    mistakes: Number,
    inaccuracies: Number,
    total_centipawn_loss: Number
  },

  // Metadata
  created_at: Date,
  updated_at: Date
}
```

### Indexes

```javascript
db.games.createIndex({ "user_id": 1, "date": -1 })
db.games.createIndex({ "user_id": 1, "analyzed": 1 })
db.games.createIndex({ "platform": 1, "game_id": 1 }, { unique: true })
db.games.createIndex({ "opening_eco": 1 })
db.games.createIndex({ "time_control": 1 })
```

### Collection: analysis_cache

Caches Stockfish position analysis to avoid redundant computation.

```javascript
{
  _id: ObjectId,
  fen: String, // Position FEN
  depth: Number, // Analysis depth
  evaluation: Number, // Centipawn evaluation
  best_move: String, // UCI notation
  pv: [String], // Principal variation
  analyzed_at: Date,
  expires_at: Date // TTL index
}
```

### Indexes

```javascript
db.analysis_cache.createIndex({ "fen": 1, "depth": 1 }, { unique: true })
db.analysis_cache.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })
```

## Usage Examples

### Insert a new game

```javascript
db.games.insertOne({
  user_id: "550e8400-e29b-41d4-a716-446655440000",
  platform: "chess.com",
  game_id: "12345678",
  pgn: "1. e4 e5 2. Nf3 Nc6...",
  date: new Date("2024-01-15"),
  time_control: "600+0",
  white_player: "player1",
  black_player: "player2",
  white_rating: 1500,
  black_rating: 1520,
  result: "1-0",
  user_color: "white",
  analyzed: false,
  created_at: new Date()
})
```

### Query analyzed games for pattern detection

```javascript
db.games.find({
  user_id: "550e8400-e29b-41d4-a716-446655440000",
  analyzed: true
}).sort({ date: -1 }).limit(500)
```

### Update game with analysis

```javascript
db.games.updateOne(
  { _id: gameId },
  {
    $set: {
      analyzed: true,
      analyzed_at: new Date(),
      moves: movesAnalysis,
      stats: gameStats,
      updated_at: new Date()
    }
  }
)
```
