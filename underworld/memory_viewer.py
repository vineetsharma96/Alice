"""Read-only F5 view using the frozen weather/mood observer shell."""
import argparse
from pathlib import Path

from . import emotional_memory
from .profile_derivation import derive

_viewer=derive('underworld._memory_viewer','underworld/mood_viewer.py',[
    ('from . import mood_store as store,weather_viewer','from . import memory_store as store,weather_viewer'),
    ('mood_operations','memory_operations'),
    ("protocol='alice.mood-observer/1'","protocol='alice.memory-observer/1'"),
    ('person=people[agent],timeline=',"retrieval=_retrieve(people[agent],_cue(w.observe_batch([agent])[0])),person=people[agent],timeline="),
    ('<details><summary>Private evidence and provenance',
     '<p id="memory-summary">Emotional memory connecting</p><details><summary>Private evidence and provenance'),
    ("(Path(__file__).parent/'web/mood-panel.js').read_bytes()",
     "(Path(__file__).parent/'web/mood-panel.js').read_bytes()+_memory_js()"),
],dict(_retrieve=emotional_memory.retrieve,_cue=emotional_memory.affect.cue,
       _memory_js=lambda:(Path(__file__).parent/'web/memory-panel.js').read_bytes()))
packet=_viewer.packet
server=_viewer.server


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--port',type=int,default=8780)
    a=p.parse_args();server(a.db,a.port).serve_forever()


if __name__=='__main__':main()
