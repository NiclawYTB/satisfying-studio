# satisfying-studio

Générateur de vidéos « satisfying » verticales (1080×1920, 30 i/s, son synthétisé libre de droits)
et procédure de publication hebdomadaire sur TikTok via vidIQ.

```
pip install -r requirements.txt --break-system-packages
python3 make_video.py --concept ring_escape --seed 4242 --out videos/a.mp4
python3 make_video.py --concept barrier_drop --seed 777 --out videos/b.mp4
python3 make_video.py --concept galton_board --seed 99 --out videos/c.mp4
```

- `concepts/ring_escape` : le cercle — boule avec gravité qui s'échappe d'anneaux tournants, compteur + chrono,
  ralenti sur le dernier anneau.
- `concepts/barrier_drop` : boule qui tombe et casse des barrières de verre (points de vie, fissures, éclats),
  caméra qui suit, arrivée dorée.
- `concepts/galton_board` : planche de Galton — des centaines de billes, strates de couleurs, courbe en cloche.
- `lib/calm.py` : sons apaisants synthétisés (aucune musique, libres de droits) ; `lib/gfx.py` : dessin ;
  `lib/timewarp.py` : ralentis.
- `RUNBOOK.md` : ce que fait la tâche planifiée chaque dimanche.
- `data/` : historique des publications et bilans.

Polices : Poppins (SIL Open Font License).
