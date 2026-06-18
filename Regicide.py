#!/usr/bin/env python3

import random
from enum import Enum, auto

class State(Enum):
    PLAYING = auto()
    WON     = auto()
    LOST    = auto()
    QUIT    = auto()

def parse_idxs(raw) -> list:
    ret = []
    for i in raw.replace(',', ' ').split():
        try:
            i = int(i)
        except (ValueError, TypeError) as e:
            continue
        ret.append(i - 1)
    return ret

class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        try:
            self.value = int(rank)
        except ValueError as e:
            if rank == "A":
                self.value = 1
            elif rank == "K":
                self.value = 20
            elif rank == "Q":
                self.value = 15
            elif rank == "J":
                self.value = 10
            else:
                raise e

    def __lt__(self, other):
        suit_order = {'c': 1, 'h': 2, 's': 3, 'd': 4}
        return (suit_order[self.suit], self.value) < (suit_order[other.suit], other.value)
    
    @property
    def name(self) -> str:
        suit_names = {"s": "Spades", "h": "Hearts", "c": "Clubs", "d": "Diamonds"}
        name = self.rank
        if self.rank == "A": name = "Ace"
        if self.rank == "K": name = "King"
        if self.rank == "Q": name = "Queen"
        if self.rank == "J": name = "Jack"
        return f"{name} of {suit_names[self.suit]}"

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

class Enemy(Card):
    def __init__(self, card):
        super().__init__(card.rank, card.suit)
        self.immune_label = {"h": "heal", "d": "draw", "c": "crit", "s": "shield"}
        self.card = card
        self.shield = 0
        self.damage_taken = 0

    @property
    def base_hp(self) -> int:
        return self.value * 2

    @property
    def hp(self) -> int:
        return max(0, self.base_hp - self.damage_taken)

    @property
    def atk(self) -> int:
        return max(0, self.value - self.shield)

    @property
    def defeated(self) -> bool:
        return self.hp <= 0

    @property
    def exact(self) -> bool:
        return self.damage_taken == self.base_hp

    def add_shield(self, n: int):
        self.shield+=n

    def hit(self, n: int):
        self.damage_taken+=n

    def __str__(self) -> str:
        return f"{self.rank}{self.suit} {self.name}\nHP: {self.hp}/{self.base_hp} Attack:{self.atk} Shield:{self.shield} [Immune:{self.immune_label[self.suit]}]"

class Deck:
    def __init__(self, cards=None):
        self.cards = [] if cards is None else cards

    def clear(self):
        self.cards = []
        return self

    def is_empty(self) -> bool:
        return not len(self.cards)

    def __len__(self) -> int:
        return len(self.cards)

    def __getitem__(self, key) -> Card:
        if isinstance(key, slice):
            return Deck(self.cards[key])
        return self.cards[key]

    def __setitem__(self, key, value):
        self.cards[key] = value

    def __delitem__(self, key):
        del self.cards[key]

    def __str__(self) -> str:
        return "  ".join([f"{i+1}.{self.cards[i]}" for i in range(len(self.cards))])

    def valid_idxs(self, idxs: list) -> bool:
        if len(set(idxs)) != len(idxs):
            print("  Duplicated index!")
            return False
        for i in idxs:
            if i < 0 or i >= len(self.cards):
                print(f"  Bad index: {i+1}")
                return False
        return True

    def get_cards(self) -> list[Card]:
        return self.cards[:]

    def add_on_top(self, card: Card):
        self.cards.append(card)
        return self

    def combine_on_top(self, deck):
        self.cards.extend(deck.get_cards())
        deck.clear()
        return self

    def combine_on_bottom(self, deck):
        self.cards = deck.get_cards() + self.cards
        deck.clear()
        return self

    def draw(self) -> Card:
        return self.cards.pop()

    def shuffle(self):
        random.shuffle(self.cards)
        return self

class Game:
    def __init__(self):
        self.hand_limit = 8
        self.tavern = Deck()
        for s in 'hdcs':
            self.tavern.add_on_top(Card('A', s))
            for r in range(2, 11):
                self.tavern.add_on_top(Card(str(r), s))
        self.tavern.shuffle()
        self.castle = Deck()
        for r in 'KQJ':
            grp = Deck()
            for s in 'hdcs':
                grp.add_on_top(Card(r, s))
            self.castle.combine_on_top(grp.shuffle())
        self.discard = Deck()
        self.hand = Deck()
        self.played = Deck()
        self.jokers = 2
        self.draw_card(self.hand_limit)
        self.next_enemy()

    def help(self):
        return print(
            "Regicide solo -- commands:\n"
            "  <n>          Play card n from hand\n"
            "  <n> <m> ...  Combo (same rank, value sum less than 10)\n"
            "  a<n>         Play Ace n alone\n"
            "  a<n> <m>     Pair Ace n with card m\n"
            "  yield        Skip attack and take damage (can not use if enemy atk is 0)\n" 
            "  joker        Refresh hand (You have 2 Jokers at start)\n"
            "  ?            Show this help prompt\n"
            "  q            quit\n"
            "Suits: h: Hearts d: Diamonds c: Clubs s: Spades\n"
            "Powers (blocked if the enemy is the same suit):\n"
            "  h: Heal  d: Draw  c: Crit(double-dmg)  s: Shield\n"
            "Win tiers: 0 jokers used: gold, 1: silver, 2: bronze\n"
            "Learn how-to-play: https://www.regicidegame.com/site_files/33132/upload_files/RegicideRulesA4.pdf"
        )

    def sort_hand(self):
        self.hand = Deck(sorted(self.hand))
        return self

    def draw_card(self, n: int) -> int:
        i = 0
        while i < n:
            if len(self.hand) >= self.hand_limit: break
            if self.tavern.is_empty(): break
            self.hand.add_on_top(self.tavern.draw())
            i+=1
        self.sort_hand()
        print(f"Drew {i} cards! Hand:{len(self.hand)}/{self.hand_limit}")
        return i

    def next_enemy(self):
        if self.castle.is_empty():
            print("All enemies defeated!")
            return self
        self.enemy = Enemy(self.castle.draw())
        print(f"New enemy appeared!\n{self.enemy}\nCastle remaining: {len(self.castle)}")
        return self

    def use_joker(self):
        if not self.jokers: return print("No more jokers left!")
        self.jokers-=1
        print(f"Using a joker. Discarded {len(self.hand)} cards, redrawing {self.hand_limit} cards.\n{self.jokers} Jokers left.")
        self.discard.combine_on_top(self.hand)
        self.draw_card(self.hand_limit)

    def show(self):
        if self.hand.is_empty():
            print("Hand empty!")
        else:
            print(str(self.hand))
        return self

    def run(self) -> State:
        print("Welcome to Regicide. ?=help q=exit.")
        while True:
            print(f"-- tavern: {len(self.tavern)}  Discard: {len(self.discard)}  Jokers: {self.jokers}\n{self.enemy}")
            self.show()
            if self.hand.is_empty() and not self.jokers and self.enemy.atk <= 0:
                print("Secret Ending: Realizing that neither you nor the foe before you can harm the other, you battle with your own thoughts before turning your back on the castle. It's a defeat, but you live to tell the tale. (Enemy ATK is 0 and no valid moves available.)")
                return State.LOST
            state, play = self.step1()
            if state != State.PLAYING: return state
            if not play: continue
            if play == "yield":
                state = self.step4()
                if state != State.PLAYING: return state
                continue
            self.apply_suit_powers(play)
            self.apply_damage(play)
            self.played.combine_on_top(Deck(play))
            if self.enemy.defeated:
                state = self.resolve()
                if state != State.PLAYING: return state
                continue
            state = self.step4()
            if state != State.PLAYING: return state

    def step1(self) -> tuple:
        raw = input("> ").strip().lower()
        if not raw: return State.PLAYING, None
        if raw in ['q', 'quit', 'exit']: return State.QUIT, None
        if raw in ['?', 'help']: return State.PLAYING, self.help()
        if raw == 'yield':
            if self.enemy.atk <= 0: return State.PLAYING, print("  Can't yield -- Enemy ATK is 0 (no damage to absorb)")
            print("  Yield.")
            return State.PLAYING, "yield"
        if raw == 'joker': return State.PLAYING, self.use_joker()
        if raw[0] == 'a': return State.PLAYING, self.parse_animal(raw)
        idxs = parse_idxs(raw)
        if not idxs: return State.PLAYING, print("  type ? for help.")
        if not self.hand.valid_idxs(idxs): return State.PLAYING, print("  type ? for help.")
        cards = [self.hand[i] for i in idxs]
        if len(cards) > 1:
            if 'A' in [card.rank for card in cards]: return State.PLAYING, print("  Aces can't combo -- use 'a<n> <m>' to pair")
            if len({card.rank for card in cards}) > 1: return State.PLAYING, print("  Combo must be the same rank")
            total_value = sum(card.value for card in cards)
            if total_value > 10: return State.PLAYING, print(f"  Combo value {total_value} > 10")
        for i in reversed(sorted(idxs)):
            del self.hand[i]
        return State.PLAYING, cards

    def parse_animal(self, raw: str) -> list:
        parts = raw[1:].replace(',', ' ').split()
        if len(parts) <= 0 or len(parts) > 2: return print("  Usage: a<n>  or  a<n> <m>")
        try:
            ai = int(parts[0]) - 1
        except (ValueError, TypeError) as e:
            return print("  Bad Ace index")
        if ai < 0 or ai >= len(self.hand) or self.hand[ai].rank != 'A': return print(f"  {ai+1} is not an Ace")
        if len(parts) == 1:
            cards = [self.hand[ai]]
            del self.hand[ai]
            return cards
        try:
            bi = int(parts[1]) - 1
        except (ValueError, TypeError) as e:
            return print("  Bad second index")
        if bi == ai: return print("  Same index")
        if bi < 0 or bi >= len(self.hand): return print(f"  index {bi+1} out of range")
        ai, bi = (ai, bi) if ai > bi else (bi, ai)
        cards = [self.hand[ai], self.hand[bi]]
        del self.hand[ai]
        del self.hand[bi]
        return cards

    def apply_suit_powers(self, cards: list):
        e = self.enemy
        total_value = sum(card.value for card in cards)
        suits = {card.suit for card in cards}
        if 'h' in suits:
            if e.suit == 'h':
                print("  Heal suppressed! (Immune)")
            elif self.discard.is_empty():
                print("  Discard empty! Nothing to heal!")
            else:
                self.discard.shuffle()
                moved = self.discard[:total_value]
                self.discard = self.discard[total_value:]
                print(f"  Heal: moved {len(moved)} cards to the bottom of tavern")
                self.tavern.combine_on_bottom(moved)
        if 'd' in suits:
            if e.suit == 'd':
                print("  Draw suppressed! (Immune)")
            else:
                print(f"  Draw: draw {total_value} cards")
                self.draw_card(total_value)
        if 's' in suits:
            if e.suit == 's':
                print("  Shield suppressed! (Immune)")
            else:
                e.add_shield(total_value)
                print(f"  Shield: shield +{total_value} -> Enemy atk is now {e.atk}")

    def apply_damage(self, cards: list):
        e = self.enemy
        total_value = sum(card.value for card in cards)
        suits = {card.suit for card in cards}
        if 'c' in suits:
            if e.suit == 'c':
                print("  Crit suppressed! (Immune)")
            else:
                print(f"  Crit: deal double damage -> {total_value}x2={total_value*2}")
                total_value*=2
        e.hit(total_value)
        print(f"  Hit {total_value}!  Enemy HP: {e.hp}/{e.base_hp}")

    def resolve(self) -> State:
        e = self.enemy
        defeated_card = e.card
        if e.exact:
            self.tavern.add_on_top(defeated_card)
            print(f"  Exact kill! {defeated_card} moved to top of tavern!")
        else:
            self.discard.add_on_top(defeated_card)
            print(f"  Moved {defeated_card} to discard.")
        self.discard.combine_on_top(self.played)
        print(f"  Defeated {e.name}!")
        if self.castle.is_empty():
            print("All enemies defeated! You won!")
            return State.WON
        self.next_enemy()
        return State.PLAYING

    def step4(self) -> State:
        dmg = self.enemy.atk
        if dmg == 0:
            print("  Enemy attack fully shielded!")
            return State.PLAYING
        remaining = dmg
        while remaining > 0:
            if self.hand.is_empty() and not self.jokers:
                print("  Can't cover damage. You lost!")
                return State.LOST
            self.show()
            print(f'  Need to discard {remaining} more value{" (or 'joker')" if self.jokers else ""}.')
            raw = input('> ').strip().lower()
            if raw == 'joker':
                if not self.jokers:
                    print("  No jokers left!")
                    continue
                self.use_joker()
                continue
            if self.hand.is_empty():
                print("  Hand empty! type 'joker'!")
                continue
            try:
                idx = int(raw) - 1
            except (TypeError, ValueError) as e:
                continue
            if not self.hand.valid_idxs([idx]): continue
            chosen = self.hand[idx]
            del self.hand[idx]
            remaining-=chosen.value
            self.discard.add_on_top(chosen)
            print(f"  Discarded {chosen}, worth {chosen.value}, still need to discard {max(0, remaining)}")
        return State.PLAYING

def main():
    while True:
        game = Game()
        state = game.run()
        if state == State.WON:
            print(f"{['Bronze', 'Silver', 'Gold'][game.jokers]} victory! You defeated all bosses and saved the country!")
        elif state == State.LOST:
            print("Game over.")
        if input("Start a new game? (y/N) ").strip().lower() != 'y': break

if __name__ == '__main__':
    main()