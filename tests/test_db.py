import db


def make_comment(comment_id, **overrides):
    comment = {
        "id": comment_id,
        "body": "NVDA 200 calls eow",
        "author_id": "t2_x",
        "author_name": "tester",
        "is_post": False,
        "source": "r/test",
        "created_unix": 1750000000,
        "Stock": "NVDA",
        "Price": "200",
        "OptionType": "calls",
        "FormattedDate": "2026-07-24",
        "Prediction": 1,
        "Confidence": 0.99,
    }
    comment.update(overrides)
    return comment


def fresh_conn(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    return db.connect()


def test_save_and_read_back(tmp_path, monkeypatch):
    conn = fresh_conn(tmp_path, monkeypatch)
    db.save_comments(conn, [make_comment("c1")])
    row = conn.execute("SELECT id, stock, price, prediction FROM comments").fetchone()
    assert row == ("c1", "NVDA", "200", 1)


def test_same_id_does_not_duplicate(tmp_path, monkeypatch):
    conn = fresh_conn(tmp_path, monkeypatch)
    db.save_comments(conn, [make_comment("c1")])
    db.save_comments(conn, [make_comment("c1", Stock="AMD")])
    rows = conn.execute("SELECT COUNT(*), MAX(stock) FROM comments").fetchone()
    assert rows == (1, "AMD")


def test_indexes_created(tmp_path, monkeypatch):
    conn = fresh_conn(tmp_path, monkeypatch)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_comments_processed_at", "idx_comments_stock", "idx_comments_prediction"} <= names
