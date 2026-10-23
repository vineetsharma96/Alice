"""Continue a new F5 copy using the existing all-inhabitant scheduler driver."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from underworld.profile_derivation import derive

_driver=derive('scripts._memory_continuity','scripts/mood_continuity.py',[
    ('from underworld import mood_store as store,weather_store as weather',
     'from underworld import memory_store as store,weather_store as weather'),
    ('mood_operations','memory_operations',4),
    ("f'mood-life-{serial}'","f'memory-life-{serial}'"),
    ("origins['personal cue + authored mood/routing' if changed else n['choice']['origin']]",
     "origins['acquired emotional memory + authored routing' if changed else n['choice']['origin']]"),
    ("if changed and r['influence']['prediction']['value']>=-.12:extra_mood_choices+=1",
     "if changed and r['influence']['memory_connected']:extra_mood_choices+=1"),
    ('additional_authored_mood_choices=extra_mood_choices','choices_using_acquired_memory=extra_mood_choices'),
])
run=_driver.run

if __name__=='__main__':_driver.main()
