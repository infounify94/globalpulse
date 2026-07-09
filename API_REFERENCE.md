# GlobalPulse API Reference

## Public Endpoints

### `GET /api/matches/upcoming`
Fetches the upcoming cricket schedule and autonomously calculates live predictions using the Champion Model.
- **Query Params**: `gender`, `match_type`, `venue`
- **Response**: Array of matches with attached SHAP probabilities and predictions.

### `GET /api/shadow_predictions`
Returns historical predictions that have been frozen in time for auditing and verification.

### `GET /api/shadow_metrics`
Returns rolling metrics like Log Loss, Brier Score, and 100-match rolling Accuracy.

### `GET /api/models`
Returns the leaderboard of all historical models stored in the Model Registry.

## Internal System Endpoints
*These endpoints require the `X-Cron-Token` HTTP header.*

### `POST /internal/predict`
Triggers the background prediction engine to scan for new matches on CricAPI and store forecasts.

### `POST /internal/verify`
Triggers the background verifier to scan completed matches on CricAPI, compare with our predictions, and update live metrics.

### `GET /system/status`
Returns deployment health: Active Model, Commit Hash, Feature Families, Dataset Version.
