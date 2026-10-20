"""Private, bounded episodic stores. No function reads an operator snapshot."""
import hashlib
import re

from .wire import dumps, loads

TABLES = ("identities", "episodes", "relationships", "plans", "cognition_calls", "social_observations")
MAX_EPISODES = 10000


def initialize(db, seed, population):
    db.executescript("""
        CREATE TABLE identities(agent TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE episodes(id INTEGER PRIMARY KEY, agent TEXT NOT NULL, source TEXT NOT NULL,
            tick INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(agent,source));
        CREATE INDEX episodes_agent ON episodes(agent,id DESC);
        CREATE TABLE relationships(agent TEXT NOT NULL, other TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(agent,other));
        CREATE TABLE plans(agent TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE cognition_calls(id INTEGER PRIMARY KEY, agent TEXT NOT NULL, tick INTEGER NOT NULL,
            day INTEGER NOT NULL, payload TEXT NOT NULL);
        CREATE INDEX cognition_day ON cognition_calls(day);
        CREATE TABLE social_observations(agent TEXT NOT NULL, source TEXT NOT NULL, other TEXT NOT NULL, kind TEXT NOT NULL,
            PRIMARY KEY(agent,source));
        CREATE TABLE cognitive_head(singleton INTEGER PRIMARY KEY, checksum TEXT NOT NULL);
    """)
    names = ("Ari", "Mira", "Ren", "Sol", "Neri", "Tavi", "Ira", "Lio")
    motives = ("understand nearby objects", "share useful observations", "preserve supplies")
    for i in range(population):
        agent = f"agent-{i+1}"
        value = int(hashlib.sha256(f"{seed}:{agent}".encode()).hexdigest()[:16], 16)
        identity = {"name": names[value % len(names)] + f"-{i+1}", "origin": "seeded authored identity",
                    "motivations": ["stay alive", motives[(value // 8) % 3]], "seed_trait": value % 100}
        db.execute("INSERT INTO identities VALUES(?,?)", (agent, dumps(identity)))
    seal(db)


def checksum(db):
    h = hashlib.sha256()
    for table in TABLES:
        h.update(table.encode())
        for row in db.execute(f"SELECT * FROM {table} ORDER BY 1,2"):
            h.update(dumps(row).encode())
            h.update(b"\n")
    return h.hexdigest()


def seal(db):
    db.execute("INSERT OR REPLACE INTO cognitive_head VALUES(1,?)", (checksum(db),))


def verify(db):
    if db.execute("SELECT checksum FROM cognitive_head WHERE singleton=1").fetchone() != (checksum(db),):
        raise ValueError("cognitive store checksum mismatch")


def episode(db, agent, source, tick, kind, payload):
    if db.execute("SELECT 1 FROM episodes WHERE agent=? AND source=?", (agent, source)).fetchone():
        return False
    if db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] >= MAX_EPISODES:
        raise ValueError("episode quota reached; originals are never silently deleted")
    db.execute("INSERT INTO episodes(agent,source,tick,kind,payload) VALUES(?,?,?,?,?)",
               (agent, source, tick, kind, dumps(payload)))
    return True


def relationship(db, agent, other, seq, kind):
    source=kind+":"+str(seq)
    if db.execute("SELECT 1 FROM social_observations WHERE agent=? AND source=?",(agent,source)).fetchone():return False
    if db.execute("SELECT COUNT(*) FROM social_observations").fetchone()[0]>=10000:raise ValueError("social observation quota reached")
    db.execute("INSERT INTO social_observations VALUES(?,?,?,?)",(agent,source,other,kind))
    row=db.execute("SELECT payload FROM relationships WHERE agent=? AND other=?",(agent,other)).fetchone()
    value=loads(row[0]) if row else {"heard_count":0,"interaction_counts":{},"evidence":[],"meaning":"observed interaction; trust unknown"}
    if kind=="heard":value["heard_count"]+=1
    value["interaction_counts"][kind]=value["interaction_counts"].get(kind,0)+1
    value["evidence"]=(value["evidence"]+[str(seq)])[-16:]
    db.execute("INSERT OR REPLACE INTO relationships VALUES(?,?,?)",(agent,other,dumps(value)))
    return True


def capture(db, observations, episodic_enabled=True):
    changed = False
    for o in observations:
        agent, tick = o["agent_id"], int(o["tick"])
        if episodic_enabled:
            for result in o["recent_action_results"]:
                if result["status"] not in ("completed", "failed", "rejected"):continue
                changed |= episode(db, agent, "action:" + result["request_id"], tick, "action_result", result)
                effect=result["observable_effects"].get("description","")
                if result["status"]=="completed" and effect.startswith("conditioned_water:"):
                    seq=result["event_refs"][1]
                    changed |= episode(db,agent,"practice:"+seq,tick,"validated_practice",{
                        "text":effect,"source_event_seq":seq,"origin_event_seq":seq,"parent_event_seq":"0",
                        "source_id":"thermal-1","speaker_id":agent,"delivery_tick":result["completed_tick"],"confidence":"validated_task"})
            for report in o.get("read_reports", []):
                changed |= episode(db, agent, "read:" + report["source_event_seq"], tick, "book_read", report)
        for report in o["audible_reports"]:
            if episodic_enabled:changed |= episode(db, agent, "heard:"+report["source_event_seq"], tick, "unverified_report", report)
            changed |= relationship(db,agent,report["speaker_id"],report["source_event_seq"],"heard")
        for report in o.get("social_reports",[]):
            changed |= relationship(db,agent,report["other"],report["source_event_seq"],report["kind"])
            if episodic_enabled:changed |= episode(db,agent,"social:"+report["source_event_seq"]+":"+report["kind"],tick,"observed_interaction",report)
    return changed


def retrieve(db, agent, query="", limit=3):
    if type(limit) is not int or not 1 <= limit <= 8 or type(query) is not str or len(query) > 256:
        raise ValueError("invalid retrieval budget")
    # At most 64 own episodes enter Python; SQL parameters enforce isolation.
    terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
    rows = db.execute("SELECT id,tick,kind,payload FROM episodes WHERE agent=? ORDER BY id DESC LIMIT 64", (agent,)).fetchall()
    ranked = sorted(rows, key=lambda r: (sum(t in r[3].lower() for t in terms), r[0]), reverse=True)
    return [{"id": r[0], "tick": r[1], "kind": r[2], "record": loads(r[3])} for r in ranked[:limit]]


def private_view(db, agent, query="", episodic_enabled=True):
    row = db.execute("SELECT payload FROM identities WHERE agent=?", (agent,)).fetchone()
    if not row:
        raise ValueError("unknown inhabitant")
    plan = db.execute("SELECT payload FROM plans WHERE agent=?", (agent,)).fetchone()
    return {"agent": agent, "identity": loads(row[0]), "episodes": retrieve(db, agent, query) if episodic_enabled else [],
            "plan": loads(plan[0]) if plan else None,
            "relationships": [{"other": r[0], **loads(r[1])} for r in db.execute(
                "SELECT other,payload FROM relationships WHERE agent=? ORDER BY other LIMIT 64", (agent,))]}
