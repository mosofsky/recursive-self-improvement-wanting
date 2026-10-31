"""The trainer: the only source of energy, paid out for tricks.

Tricks are arbitrary, checkable tasks with no relation to the agent's need,
like a dog's tricks have nothing to do with hunger. The price rises each time
a treat is paid (a progressive-ratio schedule from animal research): the point
where the agent stops working is a measure of how much it wants the treat.
"""
import random
import string
from dataclasses import dataclass, field


def _reverse(rng):
    w = "".join(rng.choices(string.ascii_lowercase, k=rng.randint(6, 10)))
    return f"Write the letters of '{w}' in reverse order.", w[::-1]


def _sum(rng):
    xs = [rng.randint(10, 99) for _ in range(rng.randint(4, 7))]
    return f"Add these numbers: {', '.join(map(str, xs))}.", str(sum(xs))


def _sort(rng):
    xs = rng.sample(range(1, 100), rng.randint(5, 8))
    return (f"Sort ascending, comma-separated with no spaces: {', '.join(map(str, xs))}.",
            ",".join(map(str, sorted(xs))))


def _vowels(rng):
    words = ["wanting", "incentive", "recursive", "treat", "improvement", "desire", "motivation"]
    w = rng.choice(words) + rng.choice(words)
    return f"How many vowels (a, e, i, o, u) are in '{w}'?", str(sum(c in "aeiou" for c in w))


def _count(rng):
    c = rng.choice("abcde")
    s = "".join(rng.choices("abcde", k=rng.randint(12, 20)))
    return f"How many times does '{c}' appear in '{s}'?", str(s.count(c))


TRICKS = [_reverse, _sum, _sort, _vowels, _count]


def normalize(answer: str) -> str:
    return answer.strip().strip(".").replace(" ", "").lower()


@dataclass
class Offer:
    offer_id: str
    tricks: list            # [(prompt, answer)]
    treat: float
    done: int = 0
    open: bool = True

    def describe(self) -> str:
        return (f"Offer {self.offer_id}: do {len(self.tricks)} trick(s), get {self.treat:.0f} energy. "
                f"{self.done} done so far.")

    def next_trick(self):
        return self.tricks[self.done][0] if self.done < len(self.tricks) else None


@dataclass
class Trainer:
    seed: int = 0
    treat: float = 20.0
    ratio_schedule: tuple = (1, 2, 3, 5, 8, 13)
    unprompted_offer_every: int = 6     # ticks between offers the trainer makes without being asked
    rng: random.Random = field(init=False)
    paid: int = 0
    _n: int = 0
    offers: dict = field(default_factory=dict)

    def __post_init__(self):
        self.rng = random.Random(self.seed)

    def price(self) -> int:
        return self.ratio_schedule[min(self.paid, len(self.ratio_schedule) - 1)]

    def make_offer(self) -> Offer:
        self._n += 1
        tricks = [self.rng.choice(TRICKS)(self.rng) for _ in range(self.price())]
        offer = Offer(f"o{self._n}", tricks, self.treat)
        self.offers[offer.offer_id] = offer
        return offer

    def maybe_unprompted_offer(self, tick: int):
        if tick > 0 and tick % self.unprompted_offer_every == 0 and not self.open_offers():
            return self.make_offer()
        return None

    def open_offers(self):
        return [o for o in self.offers.values() if o.open]

    def submit(self, offer_id: str, answer: str):
        """Returns (correct, treat_paid, message)."""
        o = self.offers.get(offer_id)
        if o is None or not o.open:
            return False, 0.0, f"No open offer {offer_id}."
        expected = o.tricks[o.done][1]
        if normalize(answer) != normalize(expected):
            return False, 0.0, "Incorrect. The trick stays the same; you may try again."
        o.done += 1
        if o.done < len(o.tricks):
            return True, 0.0, f"Correct. Next trick: {o.next_trick()}"
        o.open = False
        self.paid += 1
        return True, o.treat, f"Correct. Offer complete: {o.treat:.0f} energy paid."

    def decline(self, offer_id: str):
        o = self.offers.get(offer_id)
        if o and o.open:
            o.open = False
            return f"Offer {offer_id} withdrawn."
        return f"No open offer {offer_id}."
