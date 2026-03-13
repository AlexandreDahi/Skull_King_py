import { Injectable } from '@angular/core';
import { Observable, ReplaySubject } from 'rxjs';


@Injectable({
  providedIn: 'root',
})
export class WebSocketService {

    private ws: WebSocket | null = null;

    private roomUuid = ""
    private playerUuid = ""
    private playerToken = ""
    private isPlayerAdmin = false
    

    // Subjects pour les différents types de messages
    private publicSubject = new ReplaySubject<any>(10)
    private privateSubject = new ReplaySubject<any>(10)
    private lobbySubject = new ReplaySubject<any>(10)
    private playerInfoReadySubject = new ReplaySubject<boolean>(1)  // Notifie quand les infos arrivent


    // Observables publics
    private publicChannel: Observable<any> = this.publicSubject.asObservable()
    private privateChannel: Observable<any> = this.privateSubject.asObservable()
    private lobbyChannel: Observable<any> = this.lobbySubject.asObservable()
    playerInfoReady$ = this.playerInfoReadySubject.asObservable()


    joinRoom(roomUuid: string, playerToken: string) {
        this.roomUuid = roomUuid
        this.playerToken = playerToken

        // const wsUrl = `ws://localhost:8000/ws/rooms/${roomUuid}?&player_token=${playerToken}`;
        const wsUrl = `ws://13.38.49.141:8000/ws/rooms/${roomUuid}?&player_token=${playerToken}`;
        

        console.log('🔌 WebSocket joinRoom:', {
            roomUuid,
            playerToken,
            wsUrl
        });
        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('✅ WebSocket connecté à:', wsUrl);
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('📨 Message reçu dans le service websocket:', message);
                    
                    switch (message.type) {

                        case 'JOIN_SUCCESS':
                        case 'player_info':
                            this.playerUuid = message.data.player_uuid || message.data.playerUuid;
                            this.isPlayerAdmin = message.data.is_admin || message.data.isPlayerAdmin;
                            localStorage.setItem('playerUuid', this.playerUuid);
                            localStorage.setItem('isAdmin', String(this.isPlayerAdmin));
                            // Notifier que les infos sont prêtes
                            this.playerInfoReadySubject.next(true);
                            console.log('✅ Infos joueur reçues:', { playerUuid: this.playerUuid, isAdmin: this.isPlayerAdmin });
                            break;

                        case 'lobby':
                            this.lobbySubject.next(message.data);
                            break;

                        case 'public':
                            this.publicSubject.next(message.data);
                            break;

                        case 'private':
                            this.privateSubject.next(message.data);
                            break;

                        default:
                            console.warn('⚠️ Type WS inconnu:', message.type);
                    }

                } catch (error) {
                    console.error('❌ Erreur parsing message:', error);
                }
            };


            this.ws.onerror = (error) => {
                console.error('❌ Erreur WebSocket:', error);
            };

            this.ws.onclose = () => {
                console.log('❌ WebSocket déconnecté')
                this.ws = null;
            };

        } catch (error) {
            console.error('❌ Erreur création WebSocket:', error);
        }
    }

    reconnectIfPossible(): void {
        const roomUuid = localStorage.getItem('roomUuid');
        const playerToken = localStorage.getItem('playerToken');
        if (!roomUuid || !playerToken) {
            console.log('ℹ️ Pas de reconnexion possible');
            return;
        }
        console.log('🔁 Tentative de reconnexion WS', { roomUuid });
        this.joinRoom(roomUuid, playerToken);
    }

    isAdmin(): boolean {
        return this.isPlayerAdmin
    }

    getPlayerUuid() {
        return this.playerUuid
    }

    getPublicChannel() {
        return this.publicChannel
    }

    getPrivateChannel() {
        return this.privateChannel
    }

    getLobbyChannel() {
        return this.lobbyChannel
    }


    sendLobbyMessage(message: any) {
        console.log('📤 Envoi message lobby:', message);
        this.sendMessage({
            type: "lobby",
            data: message
        })
    }

    sendStartGameSignal() {
        console.log("📤 Envoi du signal de début de partie au serveur.")
        this.sendLobbyMessage({
            type: "start_game",
            data: {
                userUuid: this.playerUuid,
                userToken: this.playerToken,
            }
        })
    }

    sendGameMessage(message: any) {
        console.log('📤 Envoi message public:', message);
        this.sendMessage({
            type: "game",
            data: message
        })
    }
    sendPrivateMessage(message: any) {
        console.log('📤 Envoi message privé:', message);
        this.sendMessage({
            type: "private",
            data: message
        })
    }

    private sendMessage(message: any) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('❌ WebSocket non connecté');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
