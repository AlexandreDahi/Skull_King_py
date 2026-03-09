import { Component, ViewChild, OnInit, OnDestroy, NgZone } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';


import { MatIconModule } from '@angular/material/icon';

import { Subscription, BehaviorSubject, Subject, interval } from 'rxjs';
import { map, takeWhile, tap } from 'rxjs/operators';


import { Hand } from '../../components/hand/hand';
import { DropZone } from '../../components/drop-zone/drop-zone';
import data_cards from '../../components/cards/index_carte.json';


import { HeadUpDisplay } from '../../components/hud/head-up-display/head-up-display';
import { PlayerPanel } from '../../components/hud/player-panel/player-panel';

import { WebSocketService } from '../../service/websocket/websocket.service';

interface Player {
  uuid: string;
  name: string;
  score?: number;
  bet?: number;
  obtained?: number;

}

interface GameState {
  roundNumber: number;
  turnNumber: number;
  currentTurnPlayer: string; // UUID du joueur dont c'est le tour
  currentPlayerOrder: string[]; // Ordre des joueurs pour la manche en cours
}



@Component({
  selector: 'app-game',
  imports: [Hand, CommonModule,  MatIconModule, PlayerPanel, HeadUpDisplay, DropZone],
  templateUrl: './game.html',
  styleUrl: './game.css',
  standalone: true
})
export class Game implements OnInit, OnDestroy {
  // --- GAME DATA ---  //
  handCards: number[] = [];
  dropZoneCards: number[] = [];

  round : number = 1;
  totalRounds: number = 10;

  
  phase: string = "Phase d'attente des joueurs"; // affiché en haut

  timer: number = 45;
  totalTime: number = 45;
  timerProgress: number = 100;
  intervalId: any;
  private timerSub?: Subscription;
  private isRunning = false;

  score: number = 0;
  scorePopped: boolean = false;
  tricksWon: number = 0; // nombre de plis gagnés
  errorMessage: string ='';




  timer$ = new BehaviorSubject<number>(this.timer);
  timerProgress$ = new BehaviorSubject<number>(this.timerProgress);
  


  // Référence à la main du joueur
  @ViewChild(Hand) hand!: Hand;

  /* --- WEBSOCKET DATA (de lobby) --- */
  roomUuid: string = '';
  playerUuid: string = '';
  playerSelf: Player | null = null;  // Notre joueur
  otherPlayers: Player[] = [];         // Les autres joueurs
  gameState: GameState = {
    roundNumber: 1,
    turnNumber: 1,
    currentTurnPlayer: '',
    currentPlayerOrder: [],
  };
  
  // Abonnements WebSocket
  private gameSubscription?: Subscription;
  private publicSubscription?: Subscription;
  private isDestroyed = false;

  /* --- GAME LOGIC DATA (de main) --- */
 

  jsonData_cards = data_cards.index_carte;

  constructor(
    private ngZone: NgZone,
    private route: ActivatedRoute,
    private router: Router,
    private wsService: WebSocketService,
  ) {}

  /* --------------------------
      INITIALISATION
  ----------------------------*/
  ngOnInit() {
    // relancé la websocket en cas de crach :
    this.wsService.reconnectIfPossible();
    
    // 1. WebSocket setup (de lobby)
    this.roomUuid = this.route.snapshot.paramMap.get('id') || '';

    if (!this.roomUuid) {
      console.error('❌ Pas de room UUID, retour à l\'accueil');
      this.router.navigate(['/']);
      return;
    }
    // ✅ ATTENDRE que les infos du joueur arrivent AVANT de continuer
    this.wsService.playerInfoReady$.subscribe(() => {

      this.playerUuid = this.wsService.getPlayerUuid();
      console.log('🎮 === GAME INIT ===');
      console.log('Room UUID:', this.roomUuid);
      console.log('playerUuid:', this.playerUuid);

      // 1. S'abonner aux événements de jeu via WebSocket
      this.subscribeToGameEvents();
      this.subscribeToPrivateEvents();

      // 2. Récupérer les infos de la parite en cours (cartes en main, état du jeu, etc.)
      console.log('🚀 Récupéré toutes les infos en cours de la parites depuis le backend');
      this.wsService.sendGameMessage({
        type: 'game_info'
      });
    });
  }


  startTimer() {
    this.resetTimer(); // stop ancien
    this.isRunning = true;

    const startTime = Date.now();
    const startValue = this.timer;

    this.ngZone.runOutsideAngular(() => {
      const tick = () => {

        if (!this.isRunning) return; // 🔥 stop immédiat

        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const newTimer = startValue - elapsed;

        if (newTimer > 0) {
          this.ngZone.run(() => {
            this.timer = newTimer;
            this.timerProgress = (this.timer / this.totalTime) * 100;
            this.timer$.next(this.timer);
            this.timerProgress$.next(this.timerProgress);
          });

          this.intervalId = setTimeout(tick, 1000);
        } else {
          this.ngZone.run(() => {
            this.timer = 0;
            this.resetTimer();
          });
        }
      };

      this.intervalId = setTimeout(tick, 1000);
    });
  }

  resetTimer() {
    this.isRunning = false;  // 🔥 IMPORTANT
    clearTimeout(this.intervalId);
    this.intervalId = null;
  }

  // Getter : isPlayerTurn dépend de currentTurnPlayer
  get isPlayerTurn(): boolean {
    return (
      this.gameState.currentTurnPlayer === this.playerUuid &&
      this.otherPlayers.every(p => p.bet !== undefined) &&
      this.playerSelf?.bet !== undefined
    );
  }

  //
  // S'abonner aux événements de jeu via WebSocket
  //
  private subscribeToGameEvents() {
    console.log('🔌 Abonnement aux événements de jeu chanel publique...');

    this.publicSubscription = this.wsService.getPublicChannel().subscribe({
      next: (message) => {
        if (this.isDestroyed) return;
        
        console.log('📢 Message public reçu:', message);
        this.handleGameMessage(message);
      },
      error: (err) => console.error('❌ Erreur canal public:', err)
    });
  }
  private subscribeToPrivateEvents() {
     console.log('🔌 Abonnement aux événements de jeu chanel perso...');

    this.gameSubscription = this.wsService.getPrivateChannel().subscribe({
      next: (message) => {
        if (this.isDestroyed) return;
        
        console.log('📢 Message privé reçu:', message);
        this.handlePrivateMessage(message);
      },
      error: (err) => console.error('❌ Erreur canal privé:', err)
    });
  }
  private handlePrivateMessage(data: any) {
    if (this.isDestroyed) return;
    console.log('📥 Type de message privé:', data.type);
    switch(data.type) {
      case 'GAME_INFO_EVENT':
        console.log('🃏 Réception des informations du jeu:', data);
        this.handCards = data.cards || [];
        console.log('✅ Cartes en main:', this.handCards);
        this.dropZoneCards = data.turn_cards || [];
        console.log('✅ Cartes sur la table:', this.dropZoneCards);
        this.gameState.roundNumber = data.current_round ;
        this.gameState.turnNumber = data.current_turn  ;
        this.gameState.currentTurnPlayer = data.current_player;
        this.gameState.currentPlayerOrder = data.current_players_order;
        this.totalTime = data.time
        this.timer = data.time

        
        this.startTimer();

        // Récupérer et séparer les joueurs
        if (data.players && Array.isArray(data.players)) {
          const allPlayers: Player[] = data.players.map((p: any) => ({
            uuid: p.uuid || p.get('uuid'),
            name: p.name || p.get('name'),
            score: p.score || 0,
            bet: p.bet ?? undefined,
            obtained: p.obtained || 0
          }));
          this.playerSelf = allPlayers.find((p: Player) => p.uuid === this.playerUuid) || null;
          this.otherPlayers = allPlayers.filter((p: Player) => p.uuid !== this.playerUuid);
        }
        break;
        
      case 'CARD_PLAYED_ERROR':
        console.warn('⚠️ Erreur lors du jeu de la carte:', data.error_message);
        this.onCardPlayedError(data.error_message);
        break;
      case 'SEND_CARDS':
        console.log('🃏 Le serveur envoie les cartes du joueur:', data.cards);
        this.handCards = data.cards;
      break;

      default:
      console.log('⚠️ Message non géré par private message:', data.type);
    }
  }

  private handleGameMessage(data: any) {
    if (this.isDestroyed) return;

    console.log('📥 Type de message:', data.type);

    switch(data.type) {
      case 'BET_PLACED_EVENT':
        console.log('💰 Un joueur a placé une mise:',data.message);
        break;
      case 'ROUND_START_EVENT':
        console.log('🎯 Nouvelle manche commencée !', data.message);
        const turn_bet = data.turn_bet || [];

        const betMap = new Map<string, number>(turn_bet);

        this.otherPlayers = this.otherPlayers.map(p => ({
          ...p,
          bet: betMap.get(p.uuid) ?? p.bet
        }));

        if (this.playerSelf) {
          this.playerSelf = {
            ...this.playerSelf,
            bet: betMap.get(this.playerSelf.uuid) ?? this.playerSelf.bet
          };
        }

        this.resetTimer();
        this.totalTime = data.time;
        this.timer = data.time;
        this.startTimer();

        break;
        case 'CARD_PLAYED_SUCCESS':
          console.log('🃏 Une carte a été jouée avec succès !', data.type);
          if (!this.dropZoneCards.includes(data.card_id)) {
            this.dropZoneCards.push(data.card_id);
          };
          const index = this.handCards.indexOf(data.card_id);
          if (index !== -1) this.handCards.splice(index, 1);

          this.gameState = {
            ...this.gameState,
            currentTurnPlayer: data.current_player
          };
          this.resetTimer();
          this.totalTime = data.time;
          this.timer = data.time;
          this.startTimer();

          break;

        case 'TURN_END':
          console.log('🔄 Changement !');
          const inner_message = data.message;
          switch (inner_message.type) {
            case 'TURN_ENDED':
              console.log('📊 Détails du tour terminé:', inner_message.message);
              this.gameState = {
                ...this.gameState,
                currentTurnPlayer: inner_message.current_player,
                turnNumber: inner_message.turn_number
              };
              //  IL FAUT remettre à zero les compteur de plis gagner, enlever les cartes sur la table, remettre les paris en undifine et player.cards = []
              this.dropZoneCards = [...[]];
              // supprimer la carte si elle y est encore
              if (this.handCards.includes(inner_message.card_id)) {
                const index = this.handCards.indexOf(inner_message.card_id);
                if (index !== -1) {
                  this.handCards.splice(index, 1);
                }
              };

              if (this.playerSelf && this.playerSelf.uuid === inner_message.current_player) {
                this.playerSelf = {
                  ...this.playerSelf,
                  obtained: inner_message.number_of_wins
                };
              } else {
                this.otherPlayers = this.otherPlayers.map(p => {
                  if (p.uuid === inner_message.current_player) {
                    return { ...p, obtained: inner_message.number_of_wins };
                  }
                  return p;
                });
              };
              this.resetTimer();
              this.totalTime = inner_message.time;
              this.timer = inner_message.time;
              this.startTimer();

              break;
            
            case 'ROUND_ENDED':
              console.log('🏁 Manche terminée !', inner_message.message);
              this.gameState = {
                ...this.gameState,
                currentTurnPlayer: inner_message.current_player,
                turnNumber: 1,
                roundNumber: inner_message.round_number

              };
              console.log('mise à jour de, roundNumber:', this.gameState.roundNumber);
              const listScore: Record<string, number> = inner_message.List_score;
              // Mise à jour des autres joueurs
              this.otherPlayers = this.otherPlayers.map(p => ({
                ...p,
                score: listScore[p.uuid] ?? p.score, // mise à jour score
                bet: undefined,
                obtained: 0
              }));

              // Mise à jour de playerSelf
              if (this.playerSelf) {
                this.playerSelf = {
                  ...this.playerSelf,
                  score: listScore[this.playerSelf.uuid] ?? this.playerSelf.score,
                  bet: undefined,
                  obtained: 0
                };
              }
              this.dropZoneCards = [...[]];

              this.wsService.sendGameMessage({
                type: 'ask_card',
              });

              this.resetTimer();
              this.totalTime = inner_message.time;
              this.timer = inner_message.time;
              this.startTimer();

              break;

            case 'GAME_ENDED':
              console.log(inner_message.message)

              this.resetTimer();
              this.totalTime = inner_message.time;
              this.timer = inner_message.time;
              this.startTimer();

              break;

            default:
              console.log('⚠️ Message non géré dans TURN_END:', inner_message.type);
          }
          break;

      default:
        console.log('⚠️ Message non géré:', data.type);
    }
  }

  // --------------------------
  //    Placer un pari
  //----------------------------
  onBetPlaced(betAmount: number) {
    console.log('💰 Pari placé:', betAmount);

    if (this.playerSelf) {
      this.playerSelf.bet = betAmount;
      console.log('✅ Mise mise à jour pour playerSelf:', this.playerSelf.bet);
    }
    this.wsService.sendGameMessage({
      type: 'place_bet',
      bet: betAmount,
    });
  }

  // --------------------------
  //    JOUER UNE CARTE avec le double click
  //----------------------------
  onCardPlayed(cardId: number) {
    console.log('🃏 Tentative de jouer la carte ID:', cardId, 'par le joueur', this.playerSelf?.name);
    // Vérifier que c'est le tour du joueur (WebSocket)
    if (this.gameState.currentTurnPlayer !== this.playerUuid) {
      console.warn('⚠️ Ce n\'est pas votre tour !');
      return;
    }
    // Logique locale
    this.dropZoneCards.push(cardId);
    const index = this.handCards.indexOf(cardId);
    if (index > -1) this.handCards.splice(index, 1);

    // Envoyer au serveur via WebSocket
    this.wsService.sendGameMessage({
      type: 'card_played',
      cardId: cardId
    });
  }



  ngOnDestroy() {
    console.log('🧹 Nettoyage du composant Game');
    this.isDestroyed = true;

    if (this.gameSubscription) {
      this.gameSubscription.unsubscribe();
    }
    if (this.publicSubscription) {
      this.publicSubscription.unsubscribe();
    }


    clearInterval(this.intervalId);
  }

  

 
  // --------------------------
  //    SCORE ANIMATION POP
  //----------------------------
  increaseScore(amount: number) {
    this.score += amount;
    this.scorePopped = true;
    setTimeout(() => (this.scorePopped = false), 400);
  }


  // --------------------------
  //    GAGNER UN PLI
  //----------------------------
  winTrick() {
    this.tricksWon++;
    this.increaseScore(20);
  }
  // --------------------------
  //    Restreint les cartes jouables
  //----------------------------
  

  /* --------------------------
      CARD VALIDATION (de main)
  ----------------------------*/
  getPlayableCards(dropZoneCards: number[]): number[] {

  // Si c'est pas le tour du joueur, les cartes ne sont pas jouables
    if (this.isPlayerTurn === false) {
      return this.handCards;
    }
  // Si la zone de drop est vide, toutes les cartes sont jouables
    if (dropZoneCards.length === 0) {
      return [];
    }
  // Tant que la première carte est de type fuite, toutes les cartes sont jouables
    let i = 0;
    let type = this.jsonData_cards.find(c => c.id === dropZoneCards[i])?.type;
    while (type === 'fuite' && i < dropZoneCards.length - 1) {
      i++;
      type = this.jsonData_cards.find(c => c.id === dropZoneCards[i])?.type;
    }
  // Si la carte n'a pas de type, toutes les cartes sont jouables
    if (!type) return [];
  // Si la première carte est de type spécial, toutes les cartes sont jouables
    if (type === 'special') return [];

  // Filtrer les cartes qui ne correspondent pas au type requis
    if (this.handCards.filter(id => this.jsonData_cards.find(c => c.id === id)?.type === type).length === 0) return [];

    const allowed = new Set([type, 'special', 'fuite']);
    return this.handCards.filter(id => {
      const t = this.jsonData_cards.find(c => c.id === id)?.type;
      return !(t != null && allowed.has(t));
    });
  }

  get nonPlayableCards(): number[] {
    return this.getPlayableCards(this.dropZoneCards);
  }

  onCardPlayedError(errorMessage: string) {
    this.errorMessage = errorMessage;
    setTimeout(() => (this.errorMessage = ''), 3000);
  }

  


}
