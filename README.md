# FruitFlow — Google Drive vers Buffer/TikTok

FruitFlow récupère automatiquement les vidéos d’un dossier Google Drive public et maintient jusqu’à 10 publications dans Buffer. Le rythme recommandé est de 4 TikTok par jour : 13h45, 16h45, 18h45 et 20h45.

## Avant de commencer

1. Révoque l’ancienne clé exposée dans la conversation.
2. Connecte TikTok à Buffer et active **Automatic Publishing**.
3. Le dossier et les vidéos Google Drive doivent être accessibles à **Toute personne disposant du lien**, car Buffer doit télécharger chaque vidéo.
4. Dans Google Cloud Console, crée un projet, active **Google Drive API**, puis crée une **clé API**. Ajoute-la dans `.env` sous `GOOGLE_DRIVE_API_KEY`. Cette clé sert uniquement à lister le dossier public : OAuth n’est pas nécessaire.

## Installation sur Linux Mint

```bash
cd ~/fruitflow
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Si ton `.env` existe déjà, ne lance pas la dernière commande. Il doit contenir ta nouvelle clé, jamais l’ancienne.

## Trouver le canal TikTok Buffer

```bash
python fruitflow.py discover
```

Copie l’identifiant TikTok affiché dans `.env` après `BUFFER_CHANNEL_ID=`.

## Test sans publication

```bash
python fruitflow.py plan
```

Le programme liste automatiquement le dossier Drive, ignore les vidéos déjà utilisées et affiche seulement les places manquantes pour atteindre 10 dans la file. Vérifie les horaires, puis lance réellement :

```bash
python fruitflow.py run
```

## Automatisation quotidienne

Après un premier test réussi, ouvre :

```bash
crontab -e
```

Ajoute :

```cron
0 9 * * * cd /home/TON_UTILISATEUR/fruitflow && .venv/bin/python fruitflow.py run >> fruitflow.log 2>&1
```

Remplace `TON_UTILISATEUR`. Le fichier `.env` et `fruitflow-state.json` ne doivent jamais être envoyés sur GitHub.

À chaque exécution, les publications futures déjà enregistrées sont comptées. Le programme ajoute uniquement ce qu’il manque pour revenir à 10, sans reprogrammer les vidéos déjà utilisées.

## Mise en ligne gratuite sur GitHub

Le dépôt contient maintenant :

- un site vitrine dans `docs/`, compatible avec GitHub Pages ;
- une automatisation quotidienne dans `.github/workflows/fruitflow.yml` ;
- un déploiement du site dans `.github/workflows/pages.yml` ;
- un état public minimal dans `fruitflow-state.json` (numéros et horaires uniquement, aucune clé).

Crée un dépôt public nommé `fruitflow`, puis ajoute ces secrets dans **Settings → Secrets and variables → Actions** :

- `BUFFER_API_KEY`
- `GOOGLE_DRIVE_API_KEY`

Les identifiants non secrets sont déjà configurés dans le workflow. Dans **Settings → Pages**, choisis **GitHub Actions** comme source. L’onglet **Actions** permet aussi de lancer FruitFlow manuellement.

Avant le premier `git add`, exécute `python scripts/prepare_github.py` pour retirer de l’ancien historique les détails techniques renvoyés par Buffer.
