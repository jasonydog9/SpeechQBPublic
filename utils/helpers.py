import re
from typing import List
from models.player import Player

def player_in_list(user_id: int, player_list: List[Player]) -> bool:
    """Check if a player is already in the player list."""
    return any(player.get_id() == user_id for player in player_list)

def get_category_key(val: str, categories: dict) -> str:
    """Get the full category name from its abbreviation."""
    for key, value in categories.items():
        if val == value:
            return key
    return "key doesn't exist"

def validate_categories(cat_list: List[str], categories: dict) -> bool:
    """Validate that all categories in the list are valid."""
    for category in cat_list:
        if category not in categories.values():
            return False
    return True

def validate_difficulties(diff_list: List[str]) -> bool:
    """Validate that all difficulties are between 1-9."""
    for diff in diff_list:
        if not (diff.isdigit() and 1 <= int(diff) <= 9):
            return False
    return True

def parse_command_args(content: str, command: str) -> tuple:
    """Parse command arguments into categories and difficulties."""
    content = content.replace(',', '')
    args = content.split()
    args.remove(command)
    
    diff_list = []
    cat_list = []
    
    for arg in args:
        if arg.isdigit() and 1 <= int(arg) <= 9:
            diff_list.append(arg)
        else:
            cat_list.append(arg)
    
    return cat_list, diff_list

def update_question(question: str) -> str:
    """Remove parentheses and brackets from question text."""
    return re.sub(r"\(.*?\)|\[.*?\]", "", question)

def format_categories_display(cat_list: List[str]) -> str:
    """Format category list for display."""
    if not cat_list:
        return 'All'
    return ', '.join(cat_list)

def format_difficulties_display(diff_list: List[str]) -> str:
    """Format difficulty list for display."""
    if not diff_list:
        return 'All Diffs'
    return ', '.join(sorted(diff_list))
