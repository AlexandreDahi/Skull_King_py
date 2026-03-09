import uuid
from typing import Dict, List, Optional, Tuple
import random as rnd
import json
from datetime import datetime, timedelta
import os


# chemin absolu basé sur ce script
filename = os.path.join(os.path.dirname(__file__), "index_carte.json")



from app.entities.player import Player

class Game:
    MAX_ROUND: int = 10
    TOTALE_CARDS: int = 74
    TIME_FOR_BETTING = 180
    TIME_TO_PLAY = 60
    TIME_BETWIN_ROUND = 3

    def __init__(self):
        # Liste des joueurs
        self.players: Dict[uuid.UUID, Player] = {}

        # Les nombres de manches
        self.current_round: int = 1
        # Le nombre de tours dans la manche courante
        self.current_turn: int = 1
        #Cartes jouées dans le tour en cours (dictionnaire player_uuid: card_id)
        self.turn_cards: Dict[uuid.UUID, int] = {}
        #Ancien gagnant du tour précédent (None pour le premier tour de la partie)
        self.last_turn_winner: Optional[uuid.UUID] = None

        # Premier joueur à joué, pour l'ordre des manches :
        self.first_player_uuid: Optional[uuid.UUID] = None

        # Ordre des joueurs Pour jouer
        self.current_players_order: List[uuid.UUID] = []
        self.current_player: Optional[Player] = None
        
        # Json contenant les cartes
        with open(filename, "r") as f:
            self.cards = json.load(f)

        # Le timer  en time stamp:
        self.next_time_stamp = Optional[datetime]
        self.time_duration_in_seconde = int

        self.state =""

        self.butin_coople=[]

    
    # -------------------
    # Gestion des joueurs
    # -------------------

    def get_current_players_order(self) -> List[str]:
        return [str(p) for p in self.current_players_order]
    
    # permet de récupérer les cartes jouées dans le tour en cours
    def get_turn_cards(self) -> List[int]:
        return list(self.turn_cards.values()) 

    # Permet d'ajouter un joueur à la partie
    def add_player(self, player: Player) -> None:
        self.players[player.uuid] = player

    ##### permet de lancer la partie : initialise l'ordre de jeu, distribue les cartes aux joueurs, etc.
    def start_game(self) -> None:
        self.current_players_order = list(self.players.keys()) # ordre initial des joueurs (ordre d'arrivée dans la partie)
        self.first_player_uuid = rnd.choice(self.current_players_order) # désigne le joueur qui commence la première manche de manière aléatoire
        self.player_round_order() # réordonne les joueurs pour que le joueur qui commence soit en premier dans l'ordre de jeu
        self.give_players_cards(list(self.players.values())) # distribue les cartes aux joueurs en fonction du numéro de la manche courante
        self.next_time_stamp= datetime.utcnow() + timedelta(seconds= self.TIME_FOR_BETTING)
        self.time_duration_in_seconde = self.TIME_FOR_BETTING
        self.state = "betting"
    
    ### permet de lancer le tour quand tous les joueurs ont miser
    def all_bets_placed(self):
        if any(p.bet is None for p in self.players.values()):
            return []
        self.next_time_stamp= datetime.utcnow() + timedelta(seconds=self.TIME_TO_PLAY)
        self.time_duration_in_seconde = self.TIME_TO_PLAY
        self.state = "playing"
        return [(str(p.uuid), p.bet) for p in self.players.values()]
    
    #### en cas de time out :
    def end_betting_round(self):
        for player in self.players.values():
            if player.bet is None :
                player.bet = 0
        self.next_time_stamp = datetime.utcnow() + timedelta(seconds=self.TIME_TO_PLAY)
        self.time_duration_in_seconde = self.TIME_TO_PLAY
        self.state = "playing"

    ### Logique de jeu lorsq'un joueur joue une carte 
    def card_played_event(self, player_uuid: uuid.UUID, card_id: int) -> None:
        if player_uuid != self.current_player.uuid:
            print(f"Ce n'est pas le tour du joueur {player_uuid}. C'est le tour du joueur {self.current_player.uuid}.")
            return {"type":"CARD_PLAYED_ERROR","error_message": "Ce n'est pas le tour du joueur."}
        if not self.is_card_legal(player_uuid, card_id, self.get_turn_cards()):
            return {"type":"CARD_PLAYED_ERROR","error_message": "La carte jouée n'est pas légale."}
        
        self.turn_cards[player_uuid] = card_id
        # Supprimer la carte de la main du joueur
        self.players[player_uuid].remove_card(card_id)
        # Passer au joueur suivant
        print(f"{self.current_players_order},{self.current_player.uuid}")
        if self.current_player.uuid != self.current_players_order[-1]: # Si ce n'est pas le dernier joueur de l'ordre
            self.current_player = self.players[self.current_players_order[self.current_players_order.index(self.current_player.uuid) + 1]]
            self.next_time_stamp= datetime.utcnow() + timedelta(seconds=self.TIME_TO_PLAY)
            self.time_duration_in_seconde = self.TIME_TO_PLAY
            return {"type":"CARD_PLAYED_SUCCESS","current_player": str(self.current_player.uuid),"card_id": card_id,"time": self.time_duration_in_seconde}
        else:
            print("fin du tour, d'une manche ou de la partie")
            message = self.end_turn(card_id)
            return {"type":"TURN_END", "message": message}
    
    ##### Fonction de fin de tour/round :

    def end_turn(self, card_id: int) -> Tuple[Optional[uuid.UUID], Dict[str, int]]:
        self.last_turn_winner = self.turn_winner()
        
        if self.current_turn < self.current_round:
            self.current_turn += 1
            self.turn_cards = {}
            self.next_time_stamp= datetime.utcnow() + timedelta(seconds=self.TIME_TO_PLAY)
            self.time_duration_in_seconde = self.TIME_TO_PLAY

            return {"type": "TURN_ENDED","card_id": card_id, "current_player":str(self.last_turn_winner),"number_of_wins": self.players[self.last_turn_winner].number_of_wins,"turn_number":self.current_turn, "message": f"Fin du tour {self.current_turn-1} de la manche {self.current_round}","time": self.time_duration_in_seconde}
        elif self.current_turn == self.current_round and self.current_round < self.MAX_ROUND:
            self.add_bet_points() # Ajoute les points des paris aux joueurs à la fin de la manche
            self.current_round += 1
            self.current_turn = 1
            self.player_round_order()
            self.turn_cards = {}
            self.butin_rule(self.butin_coople)
            
            for player in self.players.values():
                player.bet = None # Réinitialise les paris des joueurs pour la nouvelle manche
                player.number_of_wins = 0 # Réinitialise le nombre de plis gagnés par les joueurs pour la nouvelle manche
                player.cards = []
            self.give_players_cards(list(self.players.values()))
            self.next_time_stamp= datetime.utcnow() + timedelta(seconds=self.TIME_FOR_BETTING)
            self.time_duration_in_seconde = self.TIME_FOR_BETTING
            self.state = "betting"
            return {"type": "ROUND_ENDED", "current_player":str(self.current_player.uuid),"List_score": {str(p.uuid): p.score for p in self.players.values()},"round_number":self.current_round, "message": f"Fin de la manche {self.current_round-1}, début de la manche {self.current_round}","time": self.time_duration_in_seconde}
        else :
            self.add_bet_points() # Ajoute les points des paris aux joueurs à la fin de la manche
            for player in self.players.values():
                player.bet = None
                player.number_of_wins = 0 
                player.cards = []
            winner = self.score_winner()
            self.state = "game_end"
            return {"type": "GAME_ENDED", "message": f"Fin de la partie !, le gagant est {winner.name} avec {winner.score} points !","List_score": {str(p.uuid): p.score for p in self.players.values()},"round_number":self.current_round,}

    #### en cas de time-out pour un joueur qui ne joue pas
    def auto_playing (self):
        card_id = self.current_player.cards[0]
        self.turn_cards[self.current_player.uuid] = card_id
        # Supprimer la carte de la main du joueur
        self.current_player.remove_card(card_id)
        if self.current_player.uuid != self.current_players_order[-1]: # Si ce n'est pas le dernier joueur de l'ordre
            self.current_player = self.players[self.current_players_order[self.current_players_order.index(self.current_player.uuid) + 1]]
            self.next_time_stamp= datetime.utcnow() + timedelta(seconds=self.TIME_TO_PLAY)
            self.time_duration_in_seconde = self.TIME_TO_PLAY
            return {"type":"CARD_PLAYED_SUCCESS","current_player": str(self.current_player.uuid),"card_id": card_id,"time": self.time_duration_in_seconde}
        else :
            print("fin du tour, d'une manche ou de la partie")
            message = self.end_turn(card_id)
            return {"type":"TURN_END", "message": message}



    ## Fonction pour ajouter les points des paris :
    def add_bet_points(self) -> None:
        for player in self.players.values():
            if player.bet == 0 :
                if player.get_number_of_wins() == 0:
                    player.increase_score(10*self.current_round)
                else:
                    player.increase_score(-10*self.current_round)
            else:
                if player.get_number_of_wins() == player.bet:
                    player.increase_score(20*player.bet)
                else:
                    player.increase_score(-10*abs(player.bet - player.get_number_of_wins()))
        
    
    def player_round_order(self) -> None:
        beginer_index = self.current_players_order.index(self.first_player_uuid)
        self.current_players_order = self.current_players_order[beginer_index:] + self.current_players_order[:beginer_index]
        new_beginer_index = (self.current_round - 1) % len(self.current_players_order)
        new_beginer_uuid = self.current_players_order[new_beginer_index]
        self.current_player = self.players[new_beginer_uuid]
        self.current_players_order = self.current_players_order[new_beginer_index:] + self.current_players_order[:new_beginer_index]
    
    def give_players_cards(self, players_list: List[Player]) -> None:
        for player in players_list:
            player.cards = []  # Réinitialise les cartes du joueur avant de distribuer les nouvelles
        # Création d'un deck complet
        deck = list(range(1, self.TOTALE_CARDS + 1))
        rnd.shuffle(deck)  # Mélanger le deck
        for turn in range(1, self.current_round + 1):
            for player in players_list:
                if deck:  # Vérifie qu'il reste des cartes
                    card = deck.pop()  # Retire la dernière carte du deck
                    player.give_cards([card])
                else:
                    print("Plus de cartes disponibles !")
                    return
    
    def set_bet_for_player(self, Bet: dict) -> None:
        # Bet : dictionnaire {player_uuid: bet, ...}

        for player_uuid, bet in Bet.items():  # itère sur le dict
            if player_uuid in self.players:
                self.players[player_uuid].set_bet(bet, self.current_round)
            else:
                print(f"Joueur {player_uuid} non trouvé.")


    def get_card_by_id(self, card_id: int) -> dict:
        return self.cards.get(str(card_id))
    
    def is_card_legal(self, player_uuid: uuid.UUID, card: int, turn_cards: List[int]) -> bool:
        # Vérifie si la carte appartient au joueur
        if player_uuid not in self.players:
            print(f"Joueur {player_uuid} non trouvé.")
            return False
        player = self.players[player_uuid]
        if card not in player.get_cards():
            print(f"La carte {card} n'appartient pas au joueur {player_uuid}.")
            return False
        if len(turn_cards) == 0:
            return True  # Première carte jouée, aucune restriction
        turn_cards = [self.get_card_by_id(c) for c in turn_cards]
        card_to_play = self.get_card_by_id(card)
        # Vérifie la légalité de la carte jouée

        for played_card in turn_cards:
            if played_card['type'] == 'fuite':
                continue  # Ignore les cartes de fuite
            if played_card['type'] == 'special' or played_card['type'] == 'autre':
                return True  # Toute carte peut être jouée après une carte spéciale
            if played_card['type'] == 'color':
                if played_card['specification'] == card_to_play['specification']:
                    return True  # Carte de la même couleur
                elif card_to_play['type'] == 'special' or card_to_play['type'] == 'fuite' or card_to_play['type'] == 'autre':
                    return True  # Carte spéciale peut être jouée
                elif  all(self.get_card_by_id(c)['specification'] != played_card['specification'] for c in player.get_cards()):
                    return True  # Le joueur n'a pas de carte de la couleur demandée
                else:
                    print(f"Le joueur {player_uuid} doit jouer une carte de la couleur {played_card['specification']}.")
                    return False
        return True  # Si aucune règle n'est violée, la carte est légale


    def change_turn_player_order(self,turn_winner_uuid: uuid.UUID) -> None:
        if turn_winner_uuid not in self.players:
            print(f"Joueur {turn_winner_uuid} non trouvé.")
            return
        winner_index = self.current_players_order.index(turn_winner_uuid)
        self.current_players_order = self.current_players_order[winner_index:] + self.current_players_order[:winner_index]
        self.current_player = self.players[turn_winner_uuid]
    
    def score_winner(self) -> Player:
        winner = self.players.values()[0]
        for player in self.players.values():
            if player.score > winner.score:
                winner = player
        return(winner)
    
    def turn_winner(self) -> uuid.UUID:

        turn_card_ids = list(self.turn_cards.values())
        turn_player_uuids = list(self.turn_cards.keys())
        turn_cards = [self.get_card_by_id(card_id) for card_id in turn_card_ids]

        winner_index = None
        counter = {'pirate': 0, 'sirene': 0, 'skull_king': 0, '14_classique': 0, '14_noir': 0,'butin': []}  # compteur de carte spéciale : pirate, sirène, skull_king

        for i in range(len(turn_cards)):

            if turn_cards[i]['specification'] == 'butin':
                counter['butin'].append([turn_player_uuids[i]])

            if turn_cards[i]['type'] == 'color':
                if turn_cards[i]['value'] == 14:
                    if turn_cards[i]['specification'] == 'noir':
                        counter['14_noir'] += 1
                    else:
                        counter['14_classique'] += 1

            if turn_cards[i]['type'] == 'fuite':
                continue

            if turn_cards[i]['type'] == 'autre':

                ## Cas de la baleine
                if turn_cards[i]['specification'] == 'baleine':
                    for card in range(i, len(turn_cards)):
                        if turn_cards[card]['specification'] == 'kraken':
                            return self.kraken_effect()
                    return self.baleine_effect()
                    
                ## Cas du kraken
                if turn_cards[i]['specification'] == 'kraken':
                    for card in range(i, len(turn_cards)):
                        if turn_cards[card]['specification'] == 'baleine':
                            return self.baleine_effect()
                    return self.kraken_effect()

            if winner_index is None:
                ## Premier joueur non fuite devient le gagnant provisoire
                winner_index = i

            else :
                if turn_cards[winner_index]['type'] == 'color':
                    if turn_cards[i]['type'] == 'color':
                        if turn_cards[winner_index]['specification'] == turn_cards[i]['specification']:
                            if turn_cards[winner_index]['value'] < turn_cards[i]['value']:
                                winner_index = i
                        elif turn_cards[i]['specification'] == 'noir' and turn_cards[winner_index]['specification'] != 'noir':
                            winner_index = i
                    if turn_cards[i]['type'] == 'special':
                        winner_index = i
                        counter[turn_cards[i]['specification']] += 1

                if turn_cards[winner_index]['type'] == 'special' and turn_cards[i]['type'] == 'special':

                    if turn_cards[i]['specification'] == 'pirate':
                        counter['pirate'] += 1
                        if turn_cards[winner_index]['specification'] == 'sirene' and counter['skull_king'] == 0:
                            winner_index = i
                    if turn_cards[i]['specification'] == 'skull_king':
                        counter['skull_king'] += 1
                        if turn_cards[winner_index]['specification'] == 'pirate' and counter['sirene'] == 0:
                            winner_index = i
                        elif turn_cards[winner_index]['specification'] == 'pirate' and counter['sirene'] == 1:
                            for j in range(len(turn_cards)):
                                if turn_cards[j]['specification'] == 'sirene':
                                    winner_index = j
                    if turn_cards[i]['specification'] == 'sirene':
                        counter['sirene'] += 1
                        if turn_cards[winner_index]['specification'] == 'skull_king' :
                            winner_index = i

        if winner_index is not None:
            bonus = self.end_turn_point(counter)
            self.last_turn_winner = turn_player_uuids[winner_index]
            self.players[self.last_turn_winner].increase_score(bonus)
            self.players[self.last_turn_winner].increase_number_of_wins()
            self.change_turn_player_order(self.last_turn_winner)
            if counter['butin'] != []:
                for player_b in counter['butin'] :
                    player_b.append(turn_player_uuids[winner_index])
                self.butin_coople.append(counter['butin'])
            return turn_player_uuids[winner_index]
        else :
            self.last_turn_winner = turn_player_uuids[0]
            self.change_turn_player_order(self.last_turn_winner)
            self.butin_coople=[]
            return turn_player_uuids[0]


    def kraken_effect(self) -> uuid.UUID:
        turn_card_ids = list(self.turn_cards.values())
        turn_player_uuids = list(self.turn_cards.keys())
        turn_cards = [self.get_card_by_id(card_id) for card_id in turn_card_ids]
        winner_index = None
        counter = {'pirate': 0, 'sirene': 0, 'skull_king': 0}

        for i in range(len(turn_cards)):

            if turn_cards[i]['type'] == 'fuite' or turn_cards[i]['type'] == 'autre':
                continue

            if winner_index is None:
                ## Premier joueur non fuite devient le gagnant provisoire
                winner_index = i

            else :
                if turn_cards[winner_index]['type'] == 'color':
                    if turn_cards[i]['type'] == 'color':
                        if turn_cards[winner_index]['specification'] == turn_cards[i]['specification']:
                            if turn_cards[winner_index]['value'] < turn_cards[i]['value']:
                                winner_index = i
                        elif turn_cards[i]['specification'] == 'noir' and turn_cards[winner_index]['specification'] != 'noir':
                            winner_index = i
                    if turn_cards[i]['type'] == 'special':
                        winner_index = i
                        counter[turn_cards[i]['specification']] += 1

                if turn_cards[winner_index]['type'] == 'special' and turn_cards[i]['type'] == 'special':

                    if turn_cards[i]['specification'] == 'pirate':
                        counter['pirate'] += 1
                        if turn_cards[winner_index]['specification'] == 'sirene' and counter['skull_king'] == 0:
                            winner_index = i
                    if turn_cards[i]['specification'] == 'skull_king':
                        counter['skull_king'] += 1
                        if turn_cards[winner_index]['specification'] == 'pirate' and counter['sirene'] == 0:
                            winner_index = i
                        elif turn_cards[winner_index]['specification'] == 'pirate' and counter['sirene'] == 1:
                            for j in range(len(turn_cards)):
                                if turn_cards[j]['specification'] == 'sirene':
                                    winner_index = j
                    if turn_cards[i]['specification'] == 'sirene':
                        counter['sirene'] += 1
                        if turn_cards[winner_index]['specification'] == 'skull_king' :
                            winner_index = i

        if winner_index is not None:
            self.last_turn_winner = turn_player_uuids[winner_index]
            self.change_turn_player_order(self.last_turn_winner)
            return turn_player_uuids[winner_index]
        else :
            self.last_turn_winner = turn_player_uuids[0]
            self.change_turn_player_order(self.last_turn_winner)
            return turn_player_uuids[0]
        
    def baleine_effect(self) -> uuid.UUID:
        turn_card_ids = list(self.turn_cards.values())
        turn_player_uuids = list(self.turn_cards.keys())
        turn_cards = [self.get_card_by_id(card_id) for card_id in turn_card_ids]
        counter = {'14_classique': 0, '14_noir': 0,'butin':[]}
        for i in range(len(turn_cards)):
            if turn_cards[i]['type'] == 'color':
                    if turn_cards[i]['value'] == 14:
                        if turn_cards[i]['specification'] == 'noir':
                            counter['14_noir'] += 1
                        else:
                            counter['14_classique'] += 1
                
            if turn_cards[i]['specification'] == 'butin':
                counter['butin'].append([turn_player_uuids[i]])

        bonus = 20*(counter.get('14_noir'))+10*(counter.get('14_classique'))

        
    
        winner_index = max(
            (j for j in range(len(turn_cards)) if turn_cards[j]['type'] == 'color'),
            key=lambda j: turn_cards[j]['value'],
            default=None
        )
        if winner_index is not None:
            self.last_turn_winner = turn_player_uuids[winner_index]
            self.players[self.last_turn_winner].increase_number_of_wins()
            self.players[self.last_turn_winner].increase_score(bonus)
            self.change_turn_player_order(self.last_turn_winner)
            if counter['butin'] != []:
                for player_b in counter['butin'] :
                    player_b.append(turn_player_uuids[winner_index])
                self.butin_coople.append(counter['butin'])
            
            return turn_player_uuids[winner_index]
        else:
            self.last_turn_winner = turn_player_uuids[i]
            self.change_turn_player_order(self.last_turn_winner)
            self.butin_coople = []
            return self.last_turn_winner
    
    def end_turn_point(self,counter):
        bonus = 20*(counter.get('14_noir'))+10*(counter.get('14_classique'))
        if counter.get('pirate') > 0 and counter.get('skull_king') == 0:
            bonus += 20*counter.get('sirene')
        if counter.get('skull_king') > 0 and counter.get('sirene') == 0:
            bonus += 30*counter.get('pirate')
        if counter.get('sirene') > 0 and counter.get('skull_king') > 0:
            bonus += 40*counter.get('skull_king')
        return bonus
        
    def butin_rule(self,butin_cooples):
        for allies in butin_cooples :
            if self.players[allies[0]].bet == self.players[allies[0]].number_of_wins and self.players[allies[1]].bet == self.players[allies[1]].number_of_wins :
                self.players[allies[0]].score+=20
                self.players[allies[1]].score+=20
            else:
                None
        self.butin_coople=[]