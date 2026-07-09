# Contributing to GlobalPulse

Thank you for your interest in contributing to GlobalPulse, an open-source cricket prediction engine powered by machine learning, astronomy, and ancient computational logic.

## Developer Setup
1. Clone the repository.
2. Ensure you have Python 3.12 installed.
3. Install dependencies: `pip install -r requirements.txt`.
4. Ask a maintainer for a `.env` file containing the development Supabase keys.

## Database Migrations
We use Alembic for version control. If you change a model in `core/memory/schema.py`:
1. Run `alembic revision --autogenerate -m "Description of change"`
2. Run `alembic upgrade head`
3. Commit the new migration file inside `alembic/versions`.

## Pull Request Process
1. Create a feature branch (`git checkout -b feature/your-feature`).
2. Make your changes and test locally.
3. Push your branch and open a PR against `main`.
4. Ensure the GitHub Actions CI pipeline passes (Tests, Linting, Docker Build).
5. A maintainer will review your PR. Once merged, it will automatically deploy to Cloud Run!
