"""One finite E production world, with fresh-process in-flight continuation."""
from living_continuity import main

if __name__=='__main__':
    raise SystemExit(main('living-world-e.toml',
        note='One human, no animals; assigned authored water-provision chain in 8 m. All regeneration/growth zero. Finite stock; no resets/refills.',
        task={'agent':'agent-1','goal':'provide_water'},
        config_overrides={'world':{'population':1,'width_m':8,'height_m':8},'ecology':{'enabled':False}}))
