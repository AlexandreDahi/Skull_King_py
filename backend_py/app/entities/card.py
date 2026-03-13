import os
import json

# chemin absolu basé sur ce script
filename = os.path.join(os.path.dirname(__file__), "index_carte.json")


class Card:

    def __init__(self, id:int, name:str, type:str, specification:str,force: float, value=None, power=None):
        self.id = id
        self.name = name
        self.type = type
        self.specification = specification
        self.value = value
        self.power = power
        self.force = force

class List_Cards :
    
    
    def __init__(self):
        self.card_deck = []
        with open(filename, "r") as f:
            cards = json.load(f)
            for id, card in cards.items() :
                new_card= Card(int(id),card["name"],card["type"],card["specification"],card["force"],card.get("value"),card.get("power"))
                self.card_deck.append(new_card)
    
    def add_card(self,card: Card):
          self.card_deck.append(card)


list_card = List_Cards()
