# Machine Learning GP

Scrapes new posts and comments from a subreddit, extracts trade details
(ticker, strike, expiry, option type) with a fine-tuned BERT NER model, and
scores each comment with a second BERT sequence classifier.

## Architecture

```
scraper (Go) ──> Redis (dedup) ──> RabbitMQ (comments_raw) ──> comment-processor (Python)
                                                                  ├─ NER model  (ner-output-V5)
                                                                  ├─ binary model (classifier-bert-V4)
                                                                  └─ date normalizer
```

- **scraper/** — Go service that polls Reddit, dedupes posts/comments in Redis,
  and publishes them to RabbitMQ as JSON.
- **comment-processor/** — Python service that consumes comments in batches,
  runs both models, normalizes extracted dates to `YYYY-MM-DD`, and logs the results.
- **training/** — scripts to (re)train both models from
  `training/data/regression_model_training_data.csv`.
- **training_models/** — trained model weights (gitignored, mounted into the
  processor container at `/models`).

## Running

1. Copy `.env.example` to `.env` and fill in your Reddit credentials.
2. Make sure `training_models/ner-output-V5` and `training_models/classifier-bert-V4`
   exist (train them below, or copy them in).
3. Start everything:

```sh
docker compose up --build
```

Processed comments are stored in a SQLite database at `data/comments.db`
(one row per comment with the extracted entities, scores, and model versions)
and also written to the comment-processor logs
(`docker compose logs -f comment-processor`).

Query the database from the host with any SQLite tool, or through the container:

```sh
docker compose exec comment-processor python -c \
  "import sqlite3; [print(r) for r in sqlite3.connect('/data/comments.db').execute('SELECT id, stock, price, formatted_date, prediction FROM comments ORDER BY processed_at DESC LIMIT 10')]"
```

## Training

```sh
pip install -r training/requirements.txt
python training/train_ner.py      # trains the NER model -> training_models/ner-output-V5
python training/train_binary.py   # trains the classifier -> training_models/classifier-bert-V4
```

A CUDA GPU is used automatically when available.
