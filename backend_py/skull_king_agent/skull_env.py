import uuid
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import List, Optional
import sys
import os

# Adapte ce chemin selon ta structure de projet
from app.entities import Game, Player


# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------

TOTAL_CARDS = 74        # IDs de carte : 1..74
MAX_PLAYERS = 8
MAX_ROUNDS = 10         # manches 1..10
MAX_BET = MAX_ROUNDS            # annonce max = numéro de manche (10 au maximum)

# Taille du vecteur d'observation
# - ma_main                : 74  (one-hot)
# - cartes_jouees_ce_tour  : 74  (one-hot)
# - cartes_vues_partie     : 74  (one-hot, mémoire globale)
# - mon_annonce            : 1   (normalisé 0..1)
# - mes_plis               : 1   (normalisé 0..1)
# - annonces_autres        : 7   (normalisé, 0 si slot vide)
# - plis_autres            : 7   (normalisé, 0 si slot vide)
# - manche                 : 1   (normalisé 0..1)
# - tour                   : 1   (normalisé 0..1)
# - ma_position_dans_tour  : 1   (normalisé 0..1, 0=premier, 1=dernier)
# - game_state             : 1   (0=betting, 1=playing)
# TOTAL                    : 244

OBS_SIZE = 74 + 74 + 74 + 1 + 1 + 7 + 7 + 1 + 1 + 1 + 1  # = 244

# Taille de l'espace d'action :
# - Pendant "betting"  : 0..10 → 11 actions
# - Pendant "playing"  : 0..73 → 74 actions (index = card_id - 1)
# On utilise un espace discret de taille max(11, 74) = 74
# Le masque filtre les actions illégales à chaque step3
ACTION_SIZE = 74


# ---------------------------------------------------------------------------
# ENVIRONNEMENT
# ---------------------------------------------------------------------------

class SkullKingEnv(gym.Env):
    """
    Environnement Gymnasium pour Skull King.

    L'agent contrôle UN joueur (index 0 dans l'ordre de jeu).
    Les autres joueurs sont des agents aléatoires (à remplacer par
    d'autres instances de l'agent pour le self-play).

    Espaces :
        observation_space : Box(0, 1, shape=(238,), float32)
        action_space      : Discrete(74)  — masqué selon le contexte

    Usage :
        env = SkullKingEnv(num_players=4)
        obs, info = env.start_game()
        action_mask = info["action_mask"]          # np.ndarray bool (74,)
        obs, reward, terminated, truncated, info = env.agent_playing_in_game(action)
    """

    metadata = {"render_modes": []}

    def __init__(self, num_players: int , game=None, players=None):
        super().__init__()

        assert 2 <= num_players <= MAX_PLAYERS, "num_players doit être entre 2 et 8"
        self.num_players = num_players

        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_SIZE,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(ACTION_SIZE)

        self.game: Optional[object] = None
        self.agent_uuid: Optional[uuid.UUID] = None   # UUID du joueur contrôlé
        self.player_uuids: List[uuid.UUID] = []       # ordre des joueurs
        self.players: List[Player]

        # Mémoire des cartes vues depuis le début de la partie
        self._seen_cards = np.zeros(TOTAL_CARDS, dtype=np.float32)
        self.observation = np.zeros(OBS_SIZE, dtype=np.float32)

    # -----------------------------------------------------------------------
    # RESET
    # -----------------------------------------------------------------------

    def start_game(self, seed=None, options=None):
        super().start_game(seed=seed)

        # Crée une nouvelle partie
        self.game = Game()
        self._seen_cards = np.zeros(TOTAL_CARDS, dtype=np.float32)

        # Crée les joueurs
        self.players = [Player(name=f"player_{i}") for i in range(self.num_players)]
        for p in self.players:
            self.game.add_player(p)
            self.player_uuids.append(p.uuid)

        # L'agent contrôle toujours le joueur 0
        self.agent_uuid = self.players[0].uuid

        # Lance la partie → state = "betting"
        self.game.start_game()

        # Joue les annonces des autres joueurs (aléatoire)
        self._random_bets()

        obs = self._get_observation()
        info = {"action_mask": self._get_action_mask()}
        return obs, info
    
    # -----------------------------------------------------------------------
    # Création de la boucle de jeu avec un agent et des joueurs aléatoires :
    # -----------------------------------------------------------------------

    def game_played(slef):
        return 

    # -----------------------------------------------------------------------
    # low intelligent bot
    # -----------------------------------------------------------------------

    def estimate_card_to_play(self,player_uuid,game):
        hand = game.players[player_uuid].cards
        bet = game.players[player_uuid].bet
        obtained = game.players[player_uuid].number_of_wins
        ### definition de la stratégie :
        if bet > obtained:
            if hand[0] is legal 
            




    # -----------------------------------------------------------------------
    # Action realsied by the agent
    # -----------------------------------------------------------------------

    def agent_playing_in_game(self, action: int):
        assert self.game is not None, "Appelle start_game() d'abord."

        reward = 0.0
        terminated = False
        truncated = False

        if self.game.state == "betting":
            # --- Phase d'annonce ---
            bet = int(action)  # action = 0..current_round
            bet = np.clip(bet, 0, self.game.current_round)
            self.game.set_bet_for_player({self.agent_uuid: bet})
            self.game.all_bets_placed()
            # Si le state est encore "betting" c'est que tous n'ont pas parié
            # (ne devrait pas arriver car on fait les autres en random avant)

        elif self.game.state == "playing":
            # --- Phase de jeu ---
            card_id = int(action) + 1  # action index 0..73 → card_id 1..74

            # Vérifie légalité (sécurité, le masque devrait l'empêcher)
            if not self.game.is_card_legal(
                self.agent_uuid, card_id, self.game.get_turn_cards()
            ):
                # Action illégale → pénalité et on joue une carte random légale
                reward -= 5.0
                card_id = self._get_random_legal_card(self.agent_uuid)

            # Mémorise la carte jouée
            self._seen_cards[card_id - 1] = 1.0

            score_before = self.game.players[self.agent_uuid].score
            result = self.game.card_played_event(self.agent_uuid, card_id)
            score_after = self.game.players[self.agent_uuid].score

            # Reward intermédiaire = delta de score
            reward += float(score_after - score_before)

            # Joue les autres joueurs jusqu'au prochain tour de l'agent
            if result.get("type") in ("CARD_PLAYED_SUCCESS", "TURN_END"):
                r, terminated = self._play_others_until_agent_turn()
                reward += r

        # Fin de partie
        if self.game.state == "game_end":
            terminated = True
            # Reward final = score relatif (score agent - moyenne des autres)
            agent_score = self.game.players[self.agent_uuid].score
            other_scores = [
                p.score for uid, p in self.game.players.items()
                if uid != self.agent_uuid
            ]
            reward += float(agent_score - np.mean(other_scores))

        obs = self._get_observation()
        info = {"action_mask": self._get_action_mask()}
        return obs, reward, terminated, truncated, info

    # -----------------------------------------------------------------------
    # OBSERVATION
    # -----------------------------------------------------------------------

    def _get_observation(self) -> np.ndarray:
        game = self.game
        agent = game.players[self.agent_uuid]
        n = self.num_players

        # 1. Ma main (one-hot, taille 74)
        ma_main = np.zeros(TOTAL_CARDS, dtype=np.float32)
        for card_id in agent.get_cards():
            ma_main[card_id - 1] = 1.0

        # 2. Cartes jouées ce tour (one-hot, taille 74)
        cartes_tour = np.zeros(TOTAL_CARDS, dtype=np.float32)
        for card_id in game.get_turn_cards():
            cartes_tour[card_id - 1] = 1.0

        # 3. Mémoire des cartes vues depuis le début de la partie (taille 74)
        cartes_vues = self._seen_cards.copy()

        # 4. Mon annonce normalisée (1)
        bet = agent.bet if agent.bet is not None else 0
        mon_annonce = np.array([bet / MAX_BET], dtype=np.float32)

        # 5. Mes plis gagnés normalisés (1)
        mes_plis = np.array([agent.get_number_of_wins() / MAX_ROUNDS], dtype=np.float32)

        # 6. Annonces et plis des autres joueurs (5 slots, 0 si absent)
        annonces_autres = np.zeros(MAX_PLAYERS - 1, dtype=np.float32)
        plis_autres = np.zeros(MAX_PLAYERS - 1, dtype=np.float32)
        other_players = [
            p for uid, p in game.players.items() if uid != self.agent_uuid
        ]
        for i, p in enumerate(other_players[:MAX_PLAYERS - 1]):
            b = p.bet if p.bet is not None else 0
            annonces_autres[i] = b / MAX_BET
            plis_autres[i] = p.get_number_of_wins() / MAX_ROUNDS

        # 7. Manche normalisée (1)
        manche = np.array([game.current_round / MAX_ROUNDS], dtype=np.float32)

        # 8. Tour normalisé (1)
        tour = np.array([game.current_turn / MAX_ROUNDS], dtype=np.float32)

        # 9. Ma position dans le tour (1) : 0=premier, 1=dernier
        try:
            pos = game.current_players_order.index(self.agent_uuid)
            ma_position = np.array([pos / max(n - 1, 1)], dtype=np.float32)
        except ValueError:
            ma_position = np.array([0.0], dtype=np.float32)

        # 10. Game state (1) : 0=betting, 1=playing
        state_val = 1.0 if game.state == "playing" else 0.0
        game_state = np.array([state_val], dtype=np.float32)

        obs = np.concatenate([
            ma_main,          # 74
            cartes_tour,      # 74
            cartes_vues,      # 74
            mon_annonce,      # 1
            mes_plis,         # 1
            annonces_autres,  # 5
            plis_autres,      # 5
            manche,           # 1
            tour,             # 1
            ma_position,      # 1
            game_state,       # 1
        ])                    # = 238

        assert obs.shape == (OBS_SIZE,), f"Mauvaise taille d'obs: {obs.shape}"
        return obs

    # -----------------------------------------------------------------------
    # MASQUE D'ACTIONS
    # -----------------------------------------------------------------------

    def _get_action_mask(self) -> np.ndarray:
        """
        Retourne un vecteur booléen de taille ACTION_SIZE (74).
        True = action légale, False = action illégale.
        """
        mask = np.zeros(ACTION_SIZE, dtype=bool)

        if self.game.state == "betting":
            # Actions valides : 0..current_round (indices 0..current_round)
            for i in range(self.game.current_round ):
                if i < ACTION_SIZE:
                    mask[i] = True

        elif self.game.state == "playing":
            agent = self.game.players[self.agent_uuid]
            turn_cards = self.game.get_turn_cards()
            for card_id in agent.get_cards():
                if self.game.is_card_legal(self.agent_uuid, card_id, turn_cards):
                    mask[card_id - 1] = True

        return mask

    # -----------------------------------------------------------------------
    # AGENTS ALÉATOIRES (adversaires)
    # -----------------------------------------------------------------------

    def _random_bets(self):
        """Fait parier aléatoirement tous les joueurs sauf l'agent."""
        for uid, player in self.game.players.items():
            if uid != self.agent_uuid:
                bet = int(np.random.randint(0, self.game.current_round))
                self.game.set_bet_for_player({uid: bet})
        # Ne déclenche PAS all_bets_placed ici : l'agent n'a pas encore parié

    def _play_others_until_agent_turn(self):
        """
        Joue les autres joueurs de manière aléatoire jusqu'à ce que ce soit
        le tour de l'agent (ou fin de partie).
        Retourne (reward_cumulé, terminated).
        """
        reward = 0.0
        terminated = False

        while (
            self.game.state not in ("game_end",)
            and self.game.current_player is not None
            and self.game.current_player.uuid != self.agent_uuid
        ):
            current_uid = self.game.current_player.uuid

            if self.game.state == "betting":
                # Annonce aléatoire
                bet = int(np.random.randint(0, self.game.current_round + 1))
                self.game.set_bet_for_player({current_uid: bet})
                self.game.all_bets_placed()

                # Si c'est maintenant le tour de l'agent d'annoncer, on sort
                if self.game.current_player.uuid == self.agent_uuid:
                    break

            elif self.game.state == "playing":
                card_id = self._get_random_legal_card(current_uid)
                if card_id is None:
                    break
                self._seen_cards[card_id - 1] = 1.0
                result = self.game.card_played_event(current_uid, card_id)

                if self.game.state == "game_end":
                    terminated = True
                    break

                # Après fin de manche, les autres joueurs doivent re-annoncer
                if self.game.state == "betting":
                    self._random_bets()
                    # L'agent devra annoncer → on sort de la boucle
                    break

        return reward, terminated

    def _get_random_legal_card(self, player_uuid: uuid.UUID) -> Optional[int]:
        """Retourne un card_id légal aléatoire pour le joueur donné."""
        player = self.game.players[player_uuid]
        turn_cards = self.game.get_turn_cards()
        legal = [
            c for c in player.get_cards()
            if self.game.is_card_legal(player_uuid, c, turn_cards)
        ]
        if not legal:
            return None
        return int(np.random.choice(legal))

    # -----------------------------------------------------------------------
    # RENDER (optionnel)
    # -----------------------------------------------------------------------

    def render(self):
        game = self.game
        agent = game.players[self.agent_uuid]
        print(f"\n=== Manche {game.current_round} | Tour {game.current_turn} | State: {game.state} ===")
        card_names = []
        for cid in agent.get_cards():
            card = game.get_card_by_id(cid)
            card_names.append(card["name"] if card else f"?{cid}")
        print(f"  Main : {card_names}")
        print(f"  Annonce : {agent.bet} | Plis gagnés : {agent.get_number_of_wins()}")
        print(f"  Score : {agent.get_score()}")
        turn = {str(uid)[:8]: game.get_card_by_id(cid)["name"]
                for uid, cid in game.turn_cards.items()
                if game.get_card_by_id(cid)}
        print(f"  Cartes jouées ce tour : {turn}")