from app.entities import Player,Game,Card,List_Cards
import torch
import torch.nn as nn

back/
├── app/
│   ├── entite/          # ← tes règles sont déjà là
│   ├── api/
│   └── ...
│
└── rl/                  # ← tu ajoutes ça
    ├── skull_env.py     # importe depuis app/entite/
    ├── agent.py
    ├── dqn.py
    ├── replay_buffer.py
    └── train.py

etat = [
  # Ma main (74 cartes possibles, one-hot)
  cartes_en_main,          # vecteur taille 74

  # Cartes déjà jouées ce pli
  cartes_pli_en_cours,     # vecteur taille 74

  # Annonces de tout le monde
  annonces,                # vecteur taille 8 (nb joueurs max)

  # Plis remportés par chacun
  plis_remportes,          # vecteur taille 8

  # Manche actuelle (1-10)
  manche,                  # scalaire normalisé

  # Mon annonce
  mon_annonce,             # scalaire
]
# → vecteur total ~ 200 dimensions
```

---

## 2. Les deux têtes de décision
```
État (200d)
    │
    ▼
[Couches partagées]
    │
    ├──→ [Tête ANNONCE]  → 11 sorties (annoncer 0 à 10 plis/ numéro manche)
    │
    └──→ [Tête JEU]      → 74 sorties (jouer quelle carte)
                                  + masque des cartes illégales


def calcul_reward(annonce, plis_gagnes):
    if annonce == 0:
        if plis_gagnes == 0:
            return manche * 10       # Réussi : +10 par manche
        else:
            return -manche * 10      # Raté : pénalité

    if annonce == plis_gagnes:
        return 20 * annonce          # Réussi : +20 par pli annoncé
    else:
        ecart = abs(annonce - plis_gagnes)
        return -10 * ecart           # Raté : -10 par pli d'écart