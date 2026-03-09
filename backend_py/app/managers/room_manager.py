from app.managers import manager
from typing import Dict
from app.entities import Room
from app.entities import Player
from datetime import datetime
from app.entities import Game
import asyncio




class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
    
    def create_room(self, room_name: str, host_name: str) -> Room :
        hosting_player = Player(name=host_name, is_admin=True)
        new_room = Room(name=room_name, host=hosting_player)
        self.rooms[str(new_room.uuid)] = new_room
        return new_room
    
    def delete_room(self, room_id):
        room = self.rooms[room_id]
        room.destroy_game()
        del self.rooms[room_id]
    
    
    def get_room(self, room_uuid: str) -> Room:
        return self.rooms.get(room_uuid)
    
    def add_guest(self, room_uuid: str, player_name: str) -> Player:
        """Ajoute un guest à une room et retourne le joueur créé"""
        room = self.get_room(room_uuid)
        if not room:
            return None
        guest = Player(name=player_name, is_admin=False)
        room.add_guest(guest)
        return guest
    
    
    def list_rooms(self) -> Dict[str, Room]:
        return list(self.rooms.values())
    
    def start_game(self, room_uuid: str) -> None:
        room = self.get_room(room_uuid)
        # Création de la game
        room.start_game()
    
    async def game_loop(self, room_uuid: str) -> None:

        while True:
            room = self.get_room(room_uuid)
            

            if room is None:
                print("Room introuvable")
                return

            game = room.game
            now = datetime.utcnow()

            sleep_time = (game.next_time_stamp - now).total_seconds()
            sleep_time = max(sleep_time, 0)
          
            if game.state == "betting":
                
                if now >= game.next_time_stamp:
                    print("📢❌ un ou plusieurs joueur n'ont pas misé !!!")
                    game.end_betting_round()
                    await manager.broadcast_to_room(room_uuid, {
                            "type": "ROUND_START_EVENT",
                            "message": "Début de la manche !",
                            "turn_bet":room.game.all_bets_placed(),
                            "player_timer" : str(room.game.next_time_stamp.isoformat()),
                            "time" : room.game.time_duration_in_seconde,
                        })
                    print("les paries ont bien été envoyé au front ! ")
                    

            elif game.state == "playing":
                
                if now >= game.next_time_stamp:
                    print("📢❌ Le joueur n'a pas joué de carte !!!")
                    message = game.auto_playing()
                    if message.get("type") == "CARD_PLAYED_SUCCESS":
                        await manager.broadcast_to_room(room_uuid, message)
                        print("la partie peut continuer ! ")
                    elif message.get("type") == "TURN_END":
                        # inner_message = message.get("message", "")
                        await manager.broadcast_to_room(room_uuid, message)
                        print("prochain tour ou round! ")
            
            elif game.state == "game_end":

                if now >= game.next_time_stamp:
                    message = {"type":"GAME_FINISHED"}
                    await manager.broadcast_to_room(room_uuid, message)

                    for player_uuid in game.players :
                        await manager.disconnect(room_uuid, player_uuid)

                    return self.delete_room(room_uuid)


                    

            await asyncio.sleep(sleep_time)




### Création de l'instance roomManager globale
roomManager = RoomManager()