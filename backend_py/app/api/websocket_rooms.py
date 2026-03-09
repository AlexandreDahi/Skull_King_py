from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.managers import manager
from app.managers import roomManager
import json
from datetime import datetime
import asyncio


router = APIRouter()

@router.websocket("/ws/rooms/{room_uuid}")

async def websocket_endpoint(
    websocket: WebSocket,
    room_uuid: str,
    player_token: str = Query(...),
):
    # Vérifie que la room existe
    room = roomManager.get_room(room_uuid)
    if not room:
        await websocket.close(code=1008)
        return
    player= room.get_player_by_token(player_token)
    if not player:
        await websocket.close(code=1008)
        return

    await manager.join_room_ws(websocket, room_uuid, player)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
        
            if message.get('type') == 'lobby':
                core_message = message.get("data", {})
                if core_message.get('type') == 'start_game':
                # Vérifier que c'est l'admin qui lance la partie
                    if player.is_admin:
                        print(f"🎮 {player.name} a lancé la partie dans {room_uuid}")
                        roomManager.start_game(room_uuid)

                        ## Création de la boucle temporel du jeu
                        asyncio.create_task(roomManager.game_loop(room_uuid))

                        # Notifier tous les joueurs du démarrage
                        await manager.broadcast_to_lobby(room_uuid, {
                                "type": "GAME_START_EVENT",
                                "message": "La partie a commencé !",
                                "room_uuid": room_uuid
                        })
            
            ## ICI on gère les messages liés à la partie en cours (ex: jouer une carte, faire une annonce, etc.)
            elif message.get('type') == 'game':
                print(f"📢 Message public reçu: {message}")
                # recupération du message
                core_message = message.get('data', {})

                if core_message.get('type') == 'game_info':
                    print(f"le joueur {player.name} ({player.uuid}) veut recevoir ses infos de partie")
                  
                    await manager.send_private_message(room_uuid, str(player.uuid), {
                        "type": "GAME_INFO_EVENT",
                        "cards": player.cards,
                        "players": room.get_players_info(),
                        "current_round": room.game.current_round,
                        "current_turn": room.game.current_turn,
                        "turn_cards": room.game.get_turn_cards(),
                        "current_players_order": room.game.get_current_players_order(),
                        "current_player" : str(room.game.current_player.uuid), # if room.game.current_player else None,
                        "time" : room.game.time_duration_in_seconde,
                  
                    })
                if core_message.get('type') == 'place_bet':
                    player.bet = core_message.get('bet')
                    await manager.broadcast_to_room(room_uuid, {"type": "BET_PLACED_EVENT", "message": f"Le joueur {player.name} a misé"})
                    if room.game.all_bets_placed() != []: 
                        print("Toutes les mises sont placées, début de la manche !")
                        await manager.broadcast_to_room(room_uuid, {
                            "type": "ROUND_START_EVENT",
                            "message": "Début de la manche !",
                            "turn_bet":room.game.all_bets_placed(),
                            "player_timer" : str(room.game.next_time_stamp.isoformat()),
                            "time" : room.game.time_duration_in_seconde,
                        })
                if core_message.get('type') == 'card_played':
                    print(f"le joueur {player.name} à jouer la carte {core_message.get('cardId')} ")
                    message = room.game.card_played_event(player.uuid, core_message.get('cardId'))
                    if message.get("type") == "CARD_PLAYED_ERROR":
                        await manager.send_private_message(room_uuid, str(player.uuid), message)
                    elif message.get("type") == "CARD_PLAYED_SUCCESS":
                        await manager.broadcast_to_room(room_uuid, message)
                    elif message.get("type") == "TURN_END":
                        # inner_message = message.get("message", "")
                        # if inner_message.get("type") == "GAME_ENDED":


                        await manager.broadcast_to_room(room_uuid, message)
                        
                if core_message.get('type') == 'ask_card':
                    print(f"le joueur {player.name} demande ses cartes en main ")
                    await manager.send_private_message(room_uuid, str(player.uuid), {
                        "type": "SEND_CARDS",
                        "cards": player.cards
                    })



            ## ICI on gère les messages privés lier à un joueur (ex: main du joueur, messages d'erreur spécifiques, etc.)
            elif message.get('type') == 'private':
                # Envoyer un message privé
                core_message = message.get("data", {})

                


    except WebSocketDisconnect:
        manager.disconnect(room_uuid, player.uuid)

