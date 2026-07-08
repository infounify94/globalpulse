"""
etl_run.py — GlobalPulse ETL Entrypoint

Usage:
    python etl_run.py --download   Downloads Cricsheet historical data
    python etl_run.py --import     Parses JSON files and inserts into database
    python etl_run.py --features   Generates statistical + astronomy features for all matches
    python etl_run.py --all        Runs the full pipeline (download + import + features)
    python etl_run.py --status     Shows current database row counts

Example (first-time setup):
    python etl_run.py --all
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from tqdm import tqdm
from sqlalchemy.orm import Session

from core.memory.schema import (
    get_engine, create_tables, DBEvent, DBFeatureStatistics, DBFeatureAstronomy
)
from etl.collectors.cricsheet_collector import CricsheetCollector
from etl.parsers.cricsheet_parser import CricsheetParser
from etl.loaders.postgres_loader import PostgresLoader
from plugins.cricket.cricket_event import CricketEvent
from plugins.cricket.cricket_stats_generator import CricketStatsGenerator
from core.generators.astronomy_generator import AstronomyGenerator
from core.etl.data_quality import DataQualityGateway

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("etl.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

DB_URL = os.environ.get("GLOBALPULSE_DB_URL", "sqlite:///globalpulse_dev.db")
RAW_DATA_DIR = "data/raw/cricsheet"


def get_db_engine():
    engine = get_engine(DB_URL)
    create_tables(engine)
    return engine


def cmd_download():
    """Step 1: Download Cricsheet historical data (incremental, ETag-based)."""
    logging.info("=== STEP 1: Downloading Cricsheet Historical Data ===")
    collector = CricsheetCollector(data_dir=RAW_DATA_DIR)
    files = collector.collect()
    logging.info(f"Available JSON files: {len(files)}")
    return files


def cmd_import(engine):
    """Step 2: Parse all JSON files and upsert into the database."""
    logging.info("=== STEP 2: Importing Matches into Database ===")
    parser = CricsheetParser()
    loader = PostgresLoader(engine)

    json_files = []
    if os.path.exists(RAW_DATA_DIR):
        json_files = [
            os.path.join(RAW_DATA_DIR, f)
            for f in os.listdir(RAW_DATA_DIR)
            if f.endswith(".json")
        ]

    if not json_files:
        logging.warning("No JSON files found. Run --download first.")
        return 0

    # Check which match IDs are already in the database (idempotency)
    with Session(engine) as session:
        existing_ids = {row[0] for row in session.execute(
            __import__("sqlalchemy").text("SELECT id FROM events")
        ).fetchall()}

    logging.info(f"Found {len(json_files)} JSON files. Already in DB: {len(existing_ids)}")

    errors = []
    imported = 0
    skipped = 0

    for filepath in tqdm(json_files, desc="Importing matches", unit="match"):
        match_id = os.path.basename(filepath).replace(".json", "")

        # Skip already-imported matches (idempotency)
        if match_id in existing_ids:
            skipped += 1
            continue

        try:
            event, metadata, teams, venue, innings, deliveries, players = parser.parse(filepath)
            loader.load_match(event, metadata, teams, venue, innings, deliveries, players)
            imported += 1
        except Exception as e:
            errors.append({"file": filepath, "error": str(e)})
            logging.warning(f"Failed to parse {filepath}: {e}")

    logging.info(
        f"Import complete. Imported: {imported} | Skipped: {skipped} | Errors: {len(errors)}"
    )

    if errors:
        error_log = "etl_errors.json"
        with open(error_log, "w") as f:
            json.dump(errors, f, indent=2)
        logging.warning(f"Error details saved to {error_log}")

    return imported


def cmd_features(engine):
    """Step 3: Generate statistical + astronomy features for all matches without features."""
    logging.info("=== STEP 3: Generating Features ===")
    stats_generator = CricketStatsGenerator(engine)
    astro_generator = AstronomyGenerator()

    with Session(engine) as session:
        # Find all cricket events that do NOT yet have statistical features
        events_with_stats = {
            row[0] for row in session.execute(
                __import__("sqlalchemy").text("SELECT event_id FROM features_statistics")
            ).fetchall()
        }

        all_events = session.execute(
            __import__("sqlalchemy").text(
                "SELECT e.id, e.date, e.venue_id, m.team_a_id, m.team_b_id, m.match_type "
                "FROM events e JOIN cricket_match_metadata m ON e.id = m.event_id "
                "ORDER BY e.date ASC"
            )
        ).fetchall()

    pending = [row for row in all_events if row[0] not in events_with_stats]
    logging.info(f"Events pending feature generation: {len(pending)} / {len(all_events)}")

    stats_done = 0
    astro_done = 0

    for row in tqdm(pending, desc="Generating features", unit="match"):
        event_id, date, venue_id, team_a_id, team_b_id, match_type = row

        # Build CricketEvent domain object
        cricket_event = CricketEvent(
            id=event_id,
            date=date,
            location=venue_id or "unknown",
            participants=[team_a_id, team_b_id],
            match_type=match_type or "ODI",
            venue_name=venue_id or "unknown",
            team_a=team_a_id,
            team_b=team_b_id
        )

        try:
            # 1. Generate Statistical Features
            stat_features = stats_generator.generate(cricket_event)
            with Session(engine) as session:
                existing = session.query(DBFeatureStatistics).filter_by(event_id=event_id).first()
                if not existing:
                    session.add(DBFeatureStatistics(
                        event_id=event_id,
                        features=stat_features
                    ))
                    session.commit()
            stats_done += 1
        except Exception as e:
            logging.warning(f"Stats generation failed for {event_id}: {e}")

        try:
            # 2. Generate Astronomy Features
            astro_features = astro_generator.generate(cricket_event)
            if astro_features:
                with Session(engine) as session:
                    existing = session.query(DBFeatureAstronomy).filter_by(event_id=event_id).first()
                    if not existing:
                        session.add(DBFeatureAstronomy(
                            event_id=event_id,
                            features=astro_features
                        ))
                        session.commit()
                astro_done += 1
        except Exception as e:
            logging.warning(f"Astronomy generation failed for {event_id}: {e}")

    logging.info(f"Features complete. Stats: {stats_done} | Astronomy: {astro_done}")


def cmd_status(engine):
    """Show current database health stats."""
    import sqlalchemy as sa
    with engine.connect() as conn:

        tables = ["events", "cricket_match_metadata", "innings", "teams", "venues",
                  "features_statistics", "features_astronomy", "features_environment",
                  "model_registry", "experiment_registry", "prediction_store",
                  "prediction_lineage"]
        print("\n  DATABASE STATUS")
        print("  " + "-" * 55)
        for table in tables:
            try:
                count = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()
                status = "[OK]" if count > 0 else "[ 0]"
                print(f"  {status}  {table:<35} {count:>8} rows")
            except Exception:
                print(f"  [!!]  {table:<35}    (table missing)")
        print("  " + "-" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(description="GlobalPulse ETL Runner")
    parser.add_argument("--download", action="store_true", help="Download Cricsheet data")
    parser.add_argument("--import", dest="import_data", action="store_true", help="Parse + insert into DB")
    parser.add_argument("--features", action="store_true", help="Generate features for all matches")
    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    parser.add_argument("--status", action="store_true", help="Show DB row counts")
    args = parser.parse_args()

    engine = get_db_engine()

    if args.status:
        cmd_status(engine)
        return

    if args.all or args.download:
        cmd_download()

    if args.all or args.import_data:
        cmd_import(engine)

    if args.all or args.features:
        cmd_features(engine)

    if not any([args.all, args.download, args.import_data, args.features, args.status]):
        parser.print_help()


if __name__ == "__main__":
    main()
