from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Set
import json
import asyncio
from app.entities import Player


# Gestionnaire des connexions WebSocket
class ConnectionManager:
    def __init__(self):
        # Structure: {room_uuid: {player_uuid: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Structure: {room_uuid: {player_uuid: player_info}}
        self.players_info: Dict[str, Dict[str, dict]] = {}

    async def join_room_ws(self, websocket: WebSocket, room_uuid: str, player: Player):
        await websocket.accept()
        
        # Initialiser la room si elle n'existe pas
        if room_uuid not in self.active_connections:
            self.active_connections[room_uuid] = {}
            self.players_info[room_uuid] = {}
        
        # Ajouter le joueur
        player_uuid = str(player.uuid)
        player_token = player.token
        is_admin = player.is_admin

        self.active_connections[room_uuid][str(player.uuid)] = websocket
        self.players_info[room_uuid][player_token] = {
            "uuid": player_uuid,
            "token": player_token,
            "isAdmin": is_admin
        }
        try:
            await websocket.send_json({
                "type": "JOIN_SUCCESS",
                "data": {
                    "playerUuid":str(player_uuid),
                    "isPlayerAdmin":is_admin
                }
            })
        except:
            print(f"❌ Erreur lors de l'envoi des données d'identification du joueur")
        
        print(f"✅ Joueur {str(player.name)} connecté à la room {room_uuid}")
        
        # Notifier tous les joueurs de la room qu'un nouveau joueur a rejoint
        await self.broadcast_to_lobby(room_uuid, {
            "type": "LOBBY_UPDATE",
            "player_name": str(player.name),
            "player_uuid": str(player.uuid),
            "isPlayerAdmin": player.is_admin,
            "players_count": len(self.active_connections[room_uuid])
        })


    def disconnect(self, room_uuid: str, player_uuid: str):
        if room_uuid in self.active_connections:
            if player_uuid in self.active_connections[room_uuid]:
                del self.active_connections[room_uuid][player_uuid]
                del self.players_info[room_uuid][player_uuid]
                print(f"❌ Joueur {player_uuid} déconnecté de la room {room_uuid}")
            
            # Nettoyer la room si elle est vide
            if not self.active_connections[room_uuid]:
                del self.active_connections[room_uuid]
                del self.players_info[room_uuid]
                print(f"🗑️ Room {room_uuid} supprimée (vide)")
    
    async def send_private_message(self, room_uuid: str, player_uuid: str, message: dict):
        """Envoie un message privé à un joueur spécifique"""
        if room_uuid in self.active_connections:
            if player_uuid in self.active_connections[room_uuid]:
                websocket = self.active_connections[room_uuid][player_uuid]
                await websocket.send_json({
                    "type": "private",
                    "data": message
                })

    async def broadcast_private_message(self, room_uuid: str, message: dict, exclude_player: str = None):
        """Envoie un message privé à TOUS les joueurs d'une room"""
        if room_uuid in self.active_connections:
            for player_uuid, websocket in self.active_connections[room_uuid].items():
                if player_uuid != exclude_player:
                    try:
                        await websocket.send_json({
                            "type": "private",
                            "data": message
                        })
                    except:
                        print(f"❌ Erreur lors de l'envoi privé à {player_uuid}")

    async def broadcast_to_room(self, room_uuid: str, message: dict, exclude_player: str = None):
        """Envoie un message public à tous les joueurs d'une room"""
        if room_uuid in self.active_connections:
            for player_uuid, websocket in self.active_connections[room_uuid].items():
                if player_uuid != exclude_player:
                    try:
                        await websocket.send_json({
                            "type": "public",
                            "data": message
                        })
                    except:
                        print(f"❌ Erreur lors de l'envoi à {player_uuid}")

    async def broadcast_to_lobby(self, room_uuid: str, message: dict):
        """Envoie un événement de lobby à tous les joueurs"""
        if room_uuid in self.active_connections:
            for websocket in self.active_connections[room_uuid].values():
                try:
                    await websocket.send_json({
                        "type": "lobby",
                        "data": message
                    })
                except:
                    print(f"❌ Erreur lors de l'envoi lobby")

    def get_player_info(self, room_uuid: str, player_uuid: str):
        """Récupère les infos d'un joueur"""
        if room_uuid in self.players_info:
            return self.players_info[room_uuid].get(player_uuid)
        return None

    def is_admin(self, room_uuid: str, player_uuid: str) -> bool:
        """Vérifie si un joueur est admin"""
        player_info = self.get_player_info(room_uuid, player_uuid)
        return player_info.get("is_admin", False) if player_info else False
    
### Création de l'instance ConnectionManager globale
manager = ConnectionManager()