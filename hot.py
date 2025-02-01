from threading import Thread
from queue import Queue
import httpx
import sqlite3

result_queue = Queue()

key_list = [
    "aid",
    "bvid",
    "cid",
    "title",
    "desc",
    "dynamic",
    "ctime",
    "mid",
    "owner",
    "tid",
    "tname",
    "tidv2",
    "tnamev2",
    "pic",
    "duration",
    "reason",
    "pub_location",
    "pubdate",
]

headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

client = httpx.Client(
    base_url=r"https://api.bilibili.com", headers=headers)


def get_hot(pn: int, ps: int = 50):
    url_hot = r"/x/web-interface/popular"
    param_hot = {
        "ps": ps,
        "pn": pn,
    }
    result = client.get(url=url_hot, params=param_hot)
    if result.status_code == httpx.codes.OK:
        list_hot = result.json()["data"]["list"]
        for hot in list_hot:
            data = {key: hot[key] if key in hot else None for key in key_list}
            data["mid"] = hot["owner"]["mid"]
            data["owner"] = hot["owner"]["name"]
            data["reason"] = hot["rcmd_reason"]["content"]
            result_queue.put(data)


threads = [Thread(target=get_hot, args=(i+1,)) for i in range(20)]

for thread in threads:
    thread.start()
for thread in threads:
    thread.join()

sql_insert = """
INSERT INTO "new" (aid, bvid, cid, title, "desc", "dynamic", ctime, mid, owner, tid, tname, tidv2, tnamev2, pic, duration, reason, pub_location, pubdate, first_date, last_date) 
VALUES (:aid, :bvid, :cid, :title, :desc, :dynamic, :ctime, :mid, :owner, :tid, :tname, :tidv2, :tnamev2, :pic, :duration, :reason, :pub_location, :pubdate, unixepoch(), unixepoch());
"""

sql_update = """
UPDATE video SET last_date = unixepoch() WHERE aid IN (SELECT aid FROM "new");
DELETE FROM "new" WHERE aid IN (SELECT aid FROM video);
INSERT INTO video SELECT * FROM "new";
"""

with sqlite3.connect("hot.db") as conn:
    cur = conn.cursor()
    cur.execute("""DELETE FROM "new";""")
    cur.executemany(sql_insert, result_queue.queue)
    cur.executescript(sql_update)
    conn.commit()
