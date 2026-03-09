import uuid
from typing import List, Optional

from app.entities.player import Player
from app.entities.game import Game


class Room:
    def __init__(self, name: str, host: Player):
        self.uuid: uuid.UUID = uuid.uuid4()
        self.name: str = name

        self.host: Player = host
        self.guests_list: List[Player] = []

        self.game: Optional[Game] = None

    def add_guest(self, player: Player) -> None:
        if player not in self.guests_list:
            self.guests_list.append(player)

    def delete_guest(self, player_uuid: uuid.UUID) -> None:
        self.guests_list = [
            p for p in self.guests_list if p.uuid != player_uuid
        ]

    def count_players(self) -> int:
        return 1 + len(self.guests_list)
    
    def get_players_info(self) -> List[dict]:
        players_info = []
        for player in self.get_players():
            players_info.append({
                "uuid": str(player.uuid),
                "name": player.name,
                "score": player.score,
                "bet": player.bet,
                "obtained": player.number_of_wins,
            })
        return players_info


    def get_players(self) -> List[Player]:
        # on retourne une COPIE pour éviter les effets de bord
        players = self.guests_list.copy()
        players.append(self.host)
        return players

    def get_player_by_token(self, token: str) -> Player | None:
        if self.host.token == token:
            return self.host
        for guest in self.guests_list:
            if guest.token == token:
                return guest
        return None
    
    def get_player_by_uuid(self, player_uuid: uuid.UUID) -> Player | None:
        if self.host.uuid == player_uuid:
            return self.host
        for guest in self.guests_list:
            if guest.uuid == player_uuid:
                return guest
        return None
    
    def start_game(self) -> None:
        self.game = Game()
        self.game.add_player(self.host)
        for guest in self.guests_list:
            self.game.add_player(guest)
        self.game.start_game()
    
    def destroy_game(self):
        if self.game:
            self.game = None
        




    