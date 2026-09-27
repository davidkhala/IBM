import json
from pathlib import Path

from davidkhala.data.base.sqlite import SQLite

db_path = Path.home() / ".bob" / "db" / "bob.db"  # for both bob shell and IDE


def get_tasks(db: SQLite) -> list[dict]:
    tasks = SQLite.rows_to_dicts(
        db.query(
            """
        SELECT id, title, status, task_type, env, costs, parent_id,
               datetime(created_at/1000, "unixepoch", "localtime") as created,
               datetime(updated_at/1000, "unixepoch", "localtime") as updated,
               first_message, is_pinned
        FROM tasks
        WHERE CAST(JSON_EXTRACT(costs, '$.cost') AS REAL) > 0
    """
        )
    )

    result = []
    for t in tasks:
        env = json.loads(t["env"]) if t["env"] else {}
        costs = json.loads(t["costs"]) if t["costs"] else {}

        result.append(
            {
                "id": t["id"],
                "title": t["title"],
                "first_message": t["first_message"],
                "status": t["status"],
                "task_type": t["task_type"],
                "workspace": env.get("workspace"),
                "mode": env.get("modeId"),
                "created": t["created"],
                "updated": t["updated"],
                "cost": costs.get("cost"),
                "tokens_in": costs.get("input"),
                "tokens_out": costs.get("output"),
                "is_pinned": bool(t["is_pinned"]),
                "parent_id": t["parent_id"],
            }
        )

    return result


def messages(db: SQLite) -> list[dict]:
    return SQLite.rows_to_dicts(db.query("SELECT * FROM messages"))
