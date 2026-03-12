#!/usr/bin/env python3
"""Export analyzed game positions from MongoDB to JSON for InstanceViewer testing.

Only requires MongoDB to be running — no backend, Redis, or Postgres needed.

Usage:
    # All analyzed games in the database
    python export_instances.py

    # Filter by job ID (from a previous analysis run)
    python export_instances.py --job-id <job-id>

    # Filter by username
    python export_instances.py --username lichess_user --platform lichess

    # Tune thresholds
    python export_instances.py --min-eval-loss 150 --limit 30

Output:
    frontend/public/instances.json  — loaded automatically by the test page
"""
import argparse
import json
import os
from datetime import datetime
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/chessmirror")
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "frontend", "public", "instances.json"
)


def is_user_move(move_number: float, user_color: str) -> bool:
    """Return True if this half-move belongs to the user.

    move_number is stored as a float: white's moves are whole numbers (1, 2, 3…),
    black's moves end in .5 (1.5, 2.5, 3.5…).
    """
    if not user_color:
        return True  # Unknown — include everything
    is_white_move = (move_number % 1) == 0
    return (user_color == "white") == is_white_move


def extract_instances(games, min_eval_loss: int, limit: int) -> list:
    instances = []

    for game in games:
        moves = game.get("moves", [])
        user_color = game.get("user_color", "")

        for move in moves:
            if not move.get("analyzed"):
                continue
            if not move.get("fen_before") or not move.get("best_move"):
                continue

            move_num = move.get("move_number", 0)
            if not is_user_move(move_num, user_color):
                continue

            centipawn_loss = move.get("centipawn_loss", 0)
            is_blunder = move.get("is_blunder", False)
            is_mistake = move.get("is_mistake", False)

            if centipawn_loss < min_eval_loss and not is_blunder and not is_mistake:
                continue

            instances.append(
                {
                    "game_id": str(game["_id"]),
                    "fen": move["fen_before"],
                    "move_number": int(move_num),
                    "move_played": move.get("san", ""),
                    "best_move": move.get("best_move", ""),
                    "eval_loss": centipawn_loss,
                    "accuracy": move.get("accuracy"),
                    "is_mistake": is_mistake,
                    "is_blunder": is_blunder,
                    "date": game.get("date"),
                    "opening_name": game.get("opening_name"),
                    "opening_eco": game.get("opening_eco"),
                    "result": game.get("result"),
                    "user_color": user_color or "white",
                    "time_control": game.get("time_control"),
                }
            )

    # Worst mistakes first
    instances.sort(key=lambda x: x["eval_loss"], reverse=True)
    return instances[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--job-id", help="Filter by job ID from a previous analysis run")
    parser.add_argument("--username", help="Filter by player username")
    parser.add_argument("--platform", choices=["lichess", "chess.com"], help="Platform (use with --username)")
    parser.add_argument("--min-eval-loss", type=int, default=100, metavar="CP",
                        help="Minimum centipawn loss to include a position (default: 100)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Maximum number of instances to export (default: 50)")
    parser.add_argument("--mongo-url", default=MONGO_URL,
                        help=f"MongoDB connection URL (default: {MONGO_URL})")
    args = parser.parse_args()

    print(f"Connecting to MongoDB at {args.mongo_url}…")
    client = MongoClient(args.mongo_url, serverSelectionTimeoutMS=3000)

    try:
        client.admin.command("ping")
    except Exception as e:
        print(f"\nERROR: Could not connect to MongoDB — {e}")
        print("Make sure MongoDB is running on localhost:27017 (or pass --mongo-url).")
        raise SystemExit(1)

    db = client["chessmirror"]
    games_col = db.games

    # Build query
    query: dict = {"analyzed": True}

    if args.job_id:
        query["job_id"] = args.job_id
        print(f"Filtering by job_id: {args.job_id}")
    elif args.username:
        name_filter = [{"white_player": args.username}, {"black_player": args.username}]
        if args.platform:
            query["platform"] = args.platform
            print(f"Filtering by username '{args.username}' on {args.platform}")
        else:
            print(f"Filtering by username '{args.username}' (all platforms)")
        query["$or"] = name_filter
    else:
        print("No filter applied — scanning all analyzed games")

    total_games = games_col.count_documents(query)
    print(f"Found {total_games} analyzed game(s) matching query")

    if total_games == 0:
        print("\nNo games found. Tips:")
        print("  - Run an analysis first via the app")
        print("  - Check the job ID with: mongosh chessmirror --eval 'db.jobs.find({}, {_id:1}).limit(5)'")
        raise SystemExit(0)

    # Fetch up to 500 games to mine for instances
    games = list(games_col.find(query).sort("date", -1).limit(500))
    instances = extract_instances(games, args.min_eval_loss, args.limit)

    print(f"Extracted {len(instances)} position(s) with eval_loss >= {args.min_eval_loss}cp")

    if not instances:
        print(f"\nNo positions found above the threshold. Try lowering --min-eval-loss (currently {args.min_eval_loss}).")
        raise SystemExit(0)

    # Serialize — datetime objects need converting
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(instances, f, indent=2, default=default_serializer)

    print(f"\nWrote {len(instances)} instances to:\n  {OUTPUT_PATH}")
    print("\nNow open: http://localhost:3000/test-instance-viewer")


if __name__ == "__main__":
    main()
