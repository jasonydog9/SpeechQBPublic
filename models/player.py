class Player:
    """Represents a quiz participant with scoring capabilities."""
    
    def __init__(self, name: str, user_id: int):
        self.name = name
        self.id = user_id
        self.points = 0
        self.powers = 0
        self.tens = 0
        self.negs = 0
    
    def increase_points(self):
        """Award 10 points for a correct answer."""
        self.tens += 1
        self.points += 10
    
    def power(self):
        """Award 15 points for a power (early correct answer)."""
        self.powers += 1
        self.points += 15
    
    def neg(self):
        """Deduct 5 points for an incorrect answer."""
        self.negs += 1
        self.points -= 5
    
    def get_id(self) -> int:
        return self.id
    
    def get_name(self) -> str:
        return self.name
    
    def get_points(self) -> int:
        return self.points
    
    def get_tens(self) -> int:
        return self.tens
    
    def get_powers(self) -> int:
        return self.powers
    
    def get_negs(self) -> int:
        return self.negs
    
    def to_string(self) -> str:
        """Return formatted string showing power/ten/neg counts."""
        return f"({self.get_powers()}/{self.get_tens()}/{self.get_negs()})"
