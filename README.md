# satisfying-studio

Générateur de vidéos « satisfying » verticales (1080×1920, 30 i/s, son synthétisé libre de droits)
et procédure de publication hebdomadaire sur TikTok via vidIQ.

```
pip install -r requirements.txt --break-system-packages
python3 make_video.py --concept ring_escape --seed 4242 --out videos/a.mp4
python3 make_video.py --concept rings_countdown --seed 777 --out videos/b.mp4
python3 make_video.py --concept random --seed 99 --out videos/c.mp4
```

- `concepts/ring_escape` : boule avec gravité qui doit s'échapper d'anneaux tournants (ouvertures en spirale),
  une note par rebond, compteur + chrono.
- `concepts/rings_countdown` : anneaux néon détruits sur le beat, compte à rebours, visualiseur audio final.
- `RUNBOOK.md` : ce que fait la tâche planifiée chaque dimanche.
- `data/` : historique des publications et bilans.

Polices : Poppins (SIL Open Font License).
