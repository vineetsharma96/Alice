"""Bounded recall of authored procedure syntax from this inhabitant's accessed reports."""
import re
from . import storage, memory
from .wire import loads, dumps
from .config import episodic_enabled

TASK="condition-water-v1"


def parse_procedure(text):
    if type(text) is not str or not text.startswith("PROCEDURE "):return None
    try:value=loads(text.removeprefix("PROCEDURE "),512)
    except ValueError:return None
    if type(value) is not dict or set(value)!={"task","station","dial","temperature_k"}:return None
    if value["task"]!=TASK or value["station"]!="thermal-1":return None
    if type(value["dial"]) is not str or not re.fullmatch(r"dial-[0-3]-[0-9a-f]{1,8}",value["dial"]):return None
    if type(value["temperature_k"]) not in (int,float) or not 300<=value["temperature_k"]<=370 or value["temperature_k"]%5:return None
    return value


def procedure_text(dial,temperature_k):
    value={"task":TASK,"station":"thermal-1","dial":dial,"temperature_k":temperature_k}
    text="PROCEDURE "+dumps(value)
    if parse_procedure(text) is None:raise ValueError("invalid authored procedure format")
    return text


def recall(path,agent):
    db=storage._connect(path,readonly=True)
    try:
        db.execute("BEGIN");_,config,_,_=storage._head(db);memory.private_view(db,agent)
        return recall_projection(db,agent,config)
    finally:db.close()


def recall_projection(db,agent,config):
    enabled=episodic_enabled(config)
    claims=[]
    if enabled:
        for row in db.execute("SELECT id,payload FROM episodes WHERE agent=? AND kind IN ('book_read','unverified_report','external_initialization','operator_injection') ORDER BY id DESC LIMIT 64",(agent,)):
            report=loads(row[1]);value=parse_procedure(report.get("text",""))
            if value:
                claims.append({"procedure":value,"episode_id":row[0],"observer_id":agent,
                    **{key:report[key] for key in ("source_id","speaker_id","source_event_seq","origin_event_seq","parent_event_seq","delivery_tick") if key in report},
                    "source_type":report.get("source_type","embodied_access"), "confidence":"unverified procedure report"})
            if len(claims)==8:break
    unique={dumps(c["procedure"]) for c in claims}
    return {"agent":agent,"task":TASK,"status":"conflicting" if len(unique)>1 else "reported" if claims else "unknown",
            "episodic_memory":enabled,"claims":claims,"engine_fact":False,"instrument":"authored-format own-report recall; no neural training"}


def willing_to_share(identity):
    """Explicit authored policy choice; the native engine never forces cooperation."""
    return "preserve supplies" not in identity["motivations"]
