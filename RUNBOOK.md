# Procédure hebdomadaire (tâche planifiée du dimanche soir)

Objectif : 21 vidéos « satisfying » par semaine sur le compte TikTok du propriétaire
(3 par jour, du lundi au dimanche suivants), publiées via vidIQ, après **un seul OK** de sa part.

Tout ce qui suit se fait depuis une session neuve : rien d'une session précédente n'est disponible
sauf ce dépôt.

## 0. Préparer
1. `add_repo` NiclawYTB/satisfying-studio avec accès `push`, puis cloner dans `/home/claude/satisfying-studio`.
2. `pip install -r requirements.txt --break-system-packages` (souvent déjà présent) ; `ffmpeg` doit exister.
3. Lire `config.json` (compte, réglages TikTok, horaires) et `data/strategy.md`, `data/posted.csv`.
4. Si `config.json` → `tiktok.privacyLevel` vaut `null`, les réglages n'ont pas encore été choisis par le
   propriétaire : faire quand même toute la semaine (étapes 1 à 4), puis lui demander ses réglages dans le
   même message que la demande d'OK. Ne jamais les choisir à sa place.

## 1. Analyser le compte (≈ 10 crédits vidIQ)
1. `vidiq_balance` : s'il reste moins de 15 crédits, sauter l'analyse et garder le mélange de la semaine passée.
2. `vidiq_tiktok_profile_videos` avec le handle de `config.json` (1 à 2 appels, ~10 vidéos par appel).
3. Associer chaque vidéo à une ligne de `data/posted.csv` (par la légende) et remplir `views, likes, comments,
   shares` + `checked_at`.
4. Calculer les vues moyennes par `concept` et par `palette`/`n_rings`. Ajouter un court bilan daté dans
   `data/strategy.md` (ce qui marche, ce qui ne marche pas, décision pour la semaine).

## 2. Choisir les 21 vidéos
- Semaines 1-2 (moins de 15 vidéos mesurées) : moitié `ring_escape`, moitié `rings_countdown`.
- Ensuite : 70 % répartis selon les vues moyennes des concepts, 30 % d'exploration (concept/palette moins testés).
- Ne jamais mettre deux fois de suite le même concept avec la même palette.
- Graine : nombre aléatoire à 5 chiffres jamais utilisé (vérifier `posted.csv`).
- Si l'analyse montre qu'un réglage marche nettement mieux (ex. moins d'anneaux, chrono plus court), le forcer
  avec `--set clé=valeur` (voir `make_video.py`).

## 3. Générer
Par lots de 3 (une commande ≤ 10 min) :
```
python3 make_video.py --concept ring_escape --seed 12345 --out videos/2026-W49/01.mp4
```
Chaque vidéo produit `.mp4` + `.json` (légende proposée, paramètres). Vérifier 1 image d'une vidéo sur 5
(`ffmpeg -ss 6 -i x.mp4 -frames:v 1 x.png` puis la regarder). Durée attendue : 20-30 s.

## 4. Héberger puis préparer les brouillons
1. Les releases GitHub sont refusées depuis ces sessions : héberger sur la branche `media` à la place.
   `git fetch --depth 1 origin media && git worktree add ../media -B media origin/media`, supprimer les
   anciens `.mp4` (`git rm -q *.mp4`), copier les nouveaux, commit, puis pousser **3 vidéos par push**
   (`git push origin media`) pour éviter les refus de taille. Réencoder avant si une vidéo dépasse 40 Mo :
   `ffmpeg -i in.mp4 -c:v libx264 -crf 21 -preset veryfast -c:a copy out.mp4`.
   URL publique : `https://raw.githubusercontent.com/NiclawYTB/satisfying-studio/media/<fichier>.mp4`
2. Pour chaque vidéo : `vidiq_video_upload` avec l'URL publique ci-dessus → `uploadId`
   (vidIQ garde sa propre copie : la branche `media` peut être vidée la semaine suivante).
3. Pour chaque vidéo : `vidiq_social_post_draft_create`, destination TIKTOK avec le `platformAccountId` donné par
   `vidiq_social_account_list` (compte velero7171), `text` = légende, `media` = [{type: video, id: uploadId}], `publishAt` = créneau
   (heure de Paris, voir `config.json` → `slots`, en ajoutant ±10 min au hasard), et les réglages
   `privacyLevel`, `allowComment`, `musicUsageConfirmed` de `config.json`.
   Si vidIQ renvoie une remarque de rythme (pacing), utiliser l'heure qu'il suggère.

## 5. Demander l'OK (obligatoire)
Envoyer au propriétaire (SendUserMessage + notification) un résumé court en français :
lien de la branche `media` (https://github.com/NiclawYTB/satisfying-studio/tree/media) pour voir les vidéos, tableau jour / heure / concept / légende, crédits vidIQ restants,
bilan d'analyse en 2-3 lignes. Finir par : « Réponds OK pour tout programmer. »
**Ne publier qu'après sa réponse OK** dans cette session : alors `vidiq_social_post_publish` pour chaque
brouillon avec sa `revision`. S'il demande des changements, les faire puis redemander.

## 6. Enregistrer
Ajouter les 21 lignes à `data/posted.csv` (date, heure, concept, seed, palette, n_rings, durée, légende,
postId), committer et pousser (`git push`). Supprimer les `.mp4` locaux.
