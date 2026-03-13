import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap,map } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class RoomService {
  // private apiUrl = 'http://localhost:8000/api/rooms';
  private apiUrl = 'http://15.237.60.236:8000/api/rooms'

  // BehaviorSubject garde le dernier état des rooms
  private rooms = new BehaviorSubject<any[]>([]);
  rooms$ = this.rooms.asObservable();
  
  constructor(private http: HttpClient) {}

  // Création d'une room avec roomName + hostName
  createRoom(roomName: string, hostName: string): Observable<any> {
    return this.http.post(this.apiUrl, { roomName, hostName });
  }

  // récupération du nom de la room via son UUID
  getRoomName(roomUuid: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/${roomUuid}/room_name`);
  }

  // Récupération de la liste des rooms
  getRooms(): void {
    this.http.get<any[]>(this.apiUrl).subscribe(data => this.rooms.next(data));
  }
  
  // Rejoindre une room avec roomId + playerName
  joinRoom(roomId: string, playerName: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/${roomId}/join`, { playerName });
  }

  // Récupération des joueurs d'une room
  getPlayers(roomUuid: string): Observable<any[]> {
    return this.http.get<any>(`${this.apiUrl}/${roomUuid}/players`).pipe(
      map(response => response.players || [])
  ); }

  // Quitter une room
  leaveRoom(roomUuid: string, playerUuid: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${roomUuid}/leave?playerUuid=${playerUuid}`);
  }

  getPlayerCards(roomUuid: string, playerUuid: string, num_round: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/${roomUuid}/players/${playerUuid}/cards`);
  }
}
