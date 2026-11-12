# score/stages/motion/inside/

The flag cloth's run (`flag_cloth.py`), in Newton's own Python: the physics stage's `newton_env.sh` builds it once
(`../../physics/inside/newton_env.sh`, every version pinned), and `../cloth.py` runs it on this machine's card. Never
import it from the score venv: one USD library a process, and Newton pins its own Warp. One flag model a run: its
cloth grid pinned on its pole's line, the wind of the library's flag cloth (`data/effects/flag_cloth.json`) pushing
each triangle across it. Its values all come in its job; it types none. The rules are the parent overlay's.
