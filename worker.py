"""taskq worker: pop one job from the queue and run it."""
import argparse, importlib, sqlite3, sys


def open_store(path="taskq.db"):
    return sqlite3.connect(path)


def pop_job(db, queue):
    row = db.execute(
        "SELECT id, handler FROM jobs WHERE queue=? AND state='pending' ORDER BY id LIMIT 1",
        (queue,),
    ).fetchone()
    if row:
        db.execute("UPDATE jobs SET state='running' WHERE id=?", (row[0],))
        db.commit()
    return row


def run(job):
    module = importlib.import_module(job[1].split(":")[0])
    fn = getattr(module, job[1].split(":")[1])
    return fn()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="default")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    db = open_store()
    while True:
        job = pop_job(db, args.queue)
        if not job:
            if args.once:
                return 0
            import time; time.sleep(1)
            continue
        try:
            run(job)
            db.execute("UPDATE jobs SET state='done' WHERE id=?", (job[0],))
        except Exception as e:
            print(f"job {job[0]} failed: {e}", file=sys.stderr)
            db.execute("UPDATE jobs SET state='failed' WHERE id=?", (job[0],))
        db.commit()


if __name__ == "__main__":
    sys.exit(main())
