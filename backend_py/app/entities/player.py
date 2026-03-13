import uuid
import secrets
from typing import List,Optional


class Player:
    def __init__(self, name: str = "",is_admin: bool = False):
        self.uuid: uuid.UUID = uuid.uuid4()
        self.token: str = self._generate_random_token()
        self.name: str = name
        self.is_admin: bool = is_admin
        
        self.cards: List[int] = []
        self.bet: Optional[int] = None
        self.number_of_wins: int = 0


        self.score: int = 0
        self.list_score_by_round: List[int] = []
        

    @staticmethod
    def _generate_random_token() -> str:
        # équivalent SecureRandom + Base64
        return secrets.token_urlsafe(32)

    # Logique des cartes
    def give_cards(self, cards: List[int]) -> None:
        self.cards.extend(cards)
    
    def remove_card(self, card: int) -> None:
        if card in self.cards:
            self.cards.remove(card)

    def get_cards(self) -> List[int]:
        return self.cards
    
    # Logique des scores
    def increase_score(self, points: int) -> None:
        self.score += points
        
    def get_score(self) -> int:
        return self.score

    # Logique du gagnt du tour (pour savoir qui commence)
    def is_turn_winner(self):
        return self.is_turn_winner == True

    
    # Logique des paris
    def set_bet(self, bet: int, turn : int) -> None:
        if bet<0 or bet> turn:
            raise ValueError("Bet must be between 0 and the turn number")
        self.bet = bet
    def get_bet(self) -> int:
        return self.bet
    
    def increase_number_of_wins(self) -> None:
        self.number_of_wins += 1

    def get_number_of_wins(self) -> int:
        return self.number_of_wins
    
    ### Logique pour des bots :

    def estimate_hand_win_rate(self,cards):
        win_prob=0
        for card in cards :
            proba = card["force"]
            win_prob+=proba

        return win_prob
    
    def sort_hand_by_force(self):
        self.cards.sort(key=lambda card: card["force"], reverse=True)
        

    
