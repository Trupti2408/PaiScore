import datetime
from math import pow

# ----------------------------------------------------------------------------
# 1. DEFINING THE SCORING RULES AND BADGES
# ----------------------------------------------------------------------------

# Each action is defined with its base score and daily decay rate.
ACTION_WEIGHTS = {
    # Positive Actions
    "LOGIN": {"score": 0.1, "decay": 0.10},
    "LIKE_AD": {"score": 1, "decay": 0.05},
    "POSITIVE_COMMENT": {"score": 3, "decay": 0.02},
    "SHARED_AD": {"score": 6, "decay": 0.01},
    "VISITED_AD": {"score": 0.5, "decay": 0.10},
    "GAINED_FOLLOWER": {"score": 4, "decay": 0.02},
    "FOLLOWED_USER": {"score": 0.5, "decay": 0.10},
    "SENT_MESSAGE": {"score": 2, "decay": 0.03},
    "RECEIVED_MESSAGE": {"score": 1, "decay": 0.03},
    "ADDED_TO_FAVOURITES": {"score": 5, "decay": 0.01},
    "VISITED_PROFILE": {"score": 0.5, "decay": 0.10},
    "POSTED_FREE_AD": {"score": 3, "decay": 0.02},
    "POSTED_PAI_AD": {"score": 7, "decay": 0.01},
    "POSTED_MONEY_AD": {"score": 12, "decay": 0.005},
    "GAVE_RATING": {"score": 2, "decay": 0.04},
    "RECEIVED_RATING": {"score": 3, "decay": 0.03},
    "VERIFIED_PROFILE": {"score": 10, "decay": 0}, # For Future reference

    # Negative Actions
    "AD_BLOCKED": {"score": -4, "decay": 0},
    "REPORTED_AD": {"score": -5, "decay": 0},
    "REPORTED_ADVERTISER": {"score": -15, "decay": 0},
    "INACTIVITY": {"score": -2, "decay": 0}
}

# User-facing badges are mapped from the internal score.
BADGE_LEVELS = {
    (0, 29): {"name": "New", "perks": "No PAI coin trade, limited ads"},
    (30, 59): {"name": "Explorer", "perks": "Can view all ads, earn coins"},
    (60, 79): {"name": "Trusted", "perks": "Can trade coins, appear higher in feed"},
    (80, 94): {"name": "Elite", "perks": "Premium ads, faster rewards"},
    (95, 100): {"name": "Ambassador", "perks": "First access, spotlight ads, bonus coins"}
}

# NEW: Configuration for the Age Experience Score
# This score is a bonus based on account tenure.
MAX_AGE_SCORE_CONTRIBUTION = 20  # Max points a user can get from age alone.


# ----------------------------------------------------------------------------
# 2. CORE SYSTEM CLASSES
# ----------------------------------------------------------------------------

class UserAction:
    """Represents a single action taken by a user."""

    def __init__(self, action_type, date=None):
        if action_type not in ACTION_WEIGHTS:
            raise ValueError(f"Action type '{action_type}' is not defined.")
        self.action_type = action_type
        self.date = date or datetime.date.today()
        self.base_score = ACTION_WEIGHTS[action_type]["score"]
        self.decay_rate = ACTION_WEIGHTS[action_type]["decay"]

    def get_effective_score(self, current_date):
        """Calculates the action's score after applying decay."""
        days_old = (current_date - self.date).days
        if days_old < 0: days_old = 0
        if self.decay_rate > 0:
            return self.base_score * pow(1 - self.decay_rate, days_old)
        return self.base_score

    def __repr__(self):
        return f"Action({self.action_type}, {self.date}, score={self.base_score})"


class User:
    """Manages a user's state, including their action history and PAI score."""

    def __init__(self, name, creation_date):
        self.name = name
        self.creation_date = creation_date  # NEW: Track when the user was created
        self.action_history = []
        self.score = 0
        self.badge = None
        self.last_action_date = None
        self.age_score_component = 0  # NEW: Store the age score contribution

    def add_action(self, action_type, date):
        """Adds a new action to the user's history."""
        action = UserAction(action_type, date)
        self.action_history.append(action)
        if not self.last_action_date or date > self.last_action_date:
            self.last_action_date = date
        print(f"  -> Action Added: {self.name} performed '{action_type}' on {date}. Base score: {action.base_score}")


class PaiSystem:
    """The main system to manage users and calculate scores."""

    def __init__(self, history_days=30, inactivity_days=7):
        self.users = {}
        self.history_days = history_days
        self.inactivity_days = inactivity_days
        self.current_date = datetime.date.today()

    def get_or_create_user(self, name, creation_date=None):
        """Retrieves a user by name or creates a new one."""
        if name not in self.users:
            # If creation_date isn't specified, default to the system's current date.
            self.users[name] = User(name, creation_date or self.current_date)
        return self.users[name]

    def _get_badge_for_score(self, score):
        """Maps a numerical score to a user-facing badge."""
        for (min_score, max_score), badge_info in BADGE_LEVELS.items():
            if min_score <= score <= max_score:
                return badge_info
        if score > 100: return BADGE_LEVELS[(95, 100)]
        if score < 0: return BADGE_LEVELS[(0, 29)]
        return None

    def _calculate_age_score(self, user):
        """Calculates the Paicoin Experience score based on account age."""
        total_months = (self.current_date.year - user.creation_date.year) * 12 + (
                    self.current_date.month - user.creation_date.month)
        account_age_years = total_months / 12.0

        age_multiplier = 0
        if account_age_years >= 8:
            age_multiplier = 0.5
        elif account_age_years >= 5:
            age_multiplier = 0.4
        elif account_age_years >= 2:
            age_multiplier = 0.3
        else:
            age_multiplier = 0.15

        user.age_score_component = MAX_AGE_SCORE_CONTRIBUTION * age_multiplier
        return user.age_score_component

    def update_user_score(self, user_name):
        """Recalculates a user's score from actions AND their age experience."""
        user = self.get_or_create_user(user_name)

        # 1. Calculate score from recent actions
        cutoff_date = self.current_date - datetime.timedelta(days=self.history_days)
        user.action_history = [action for action in user.action_history if action.date >= cutoff_date]
        action_score = sum(action.get_effective_score(self.current_date) for action in user.action_history)

        # 2. Calculate the age experience score
        age_score = self._calculate_age_score(user)

        # 3. Combine scores and clamp to 0-100
        final_score = action_score + age_score
        user.score = max(0, min(100, final_score))

        # 4. Assign badge
        user.badge = self._get_badge_for_score(user.score)

    def advance_time(self, days=1):
        """Simulates the passage of time and updates all users."""
        self.current_date += datetime.timedelta(days=days)
        print(f"\n--- {days} day(s) later ({self.current_date}) ---")
        for user_name in self.users:
            self.update_user_score(user_name)

    def print_user_status(self, user_name):
        """Displays the current status of a user."""
        user = self.get_or_create_user(user_name)
        print("=" * 40)
        print(f"User Status: {user.name} on {self.current_date}")
        print(f"  Age Score Component: {user.age_score_component:.2f} / {MAX_AGE_SCORE_CONTRIBUTION}")
        print(f"  Final Score: {user.score:.2f}")
        if user.badge:
            print(f"  Badge: {user.badge['name']} ({user.badge['perks']})")
        else:
            print("  Badge: None")
        print("=" * 40)


# ----------------------------------------------------------------------------
# 3. SINGLE CALLABLE FUNCTION TO HANDLE ACTIONS
# ----------------------------------------------------------------------------

def handle_user_action(pai_system, user_name, action_type, action_date=None, creation_date=None):
    """
    This is the main callable function to process a single user action.
    """
    if not action_date:
        action_date = pai_system.current_date

    user = pai_system.get_or_create_user(user_name, creation_date)
    user.add_action(action_type, action_date)
    pai_system.update_user_score(user_name)
    return user


# ----------------------------------------------------------------------------
# 4. MAIN SIMULATION FUNCTION
# ----------------------------------------------------------------------------

def main():
    """
    Main function to run the PAI Score simulation.
    """
    pai_system = PaiSystem()
    sim_start_date = datetime.date(2025, 7, 18)
    pai_system.current_date = sim_start_date
    print(f"--- PAI Score Simulation Start (Today is {sim_start_date}) ---")

    # --- Scenario 1: New User 'Trupti' ---
    print("\n*** SCENARIO 1: A New User 'Trupti' (Joined Today) ***")
    handle_user_action(pai_system, "Trupti", "LOGIN", creation_date=sim_start_date)
    handle_user_action(pai_system, "Trupti", "POSITIVE_COMMENT")
    pai_system.print_user_status("Trupti")

    # --- Scenario 2: Established User 'Sai' ---
    print("\n*** SCENARIO 2: An Established User 'Sai' (Joined 3 years ago) ***")
    sai_creation_date = datetime.date(2022, 6, 1)
    handle_user_action(pai_system, "Sai", "LOGIN", creation_date=sai_creation_date)
    handle_user_action(pai_system, "Sai", "POSTED_MONEY_AD")
    pai_system.print_user_status("Sai")

    # --- Scenario 3: Veteran User 'Kavita' ---
    print("\n*** SCENARIO 3: A Veteran User 'Kavita' (Joined 9 years ago) ***")
    kavita_creation_date = datetime.date(2016, 5, 1)
    handle_user_action(pai_system, "Kavita", "LOGIN", creation_date=kavita_creation_date)
    # Kavita is a long-term user but gets reported
    print("\n -> Kavita is reported for a fake offer...")
    handle_user_action(pai_system, "Kavita", "REPORTED_ADVERTISER")
    pai_system.print_user_status("Kavita")

    # --- Time passes to show decay ---
    pai_system.advance_time(days=365)
    print("Status for Trupti after 1 year:")
    pai_system.print_user_status("Trupti")
    print("Status for Sai after 1 year:")
    pai_system.print_user_status("Sai")
    print("Status for Kavita after 1 year:")
    pai_system.print_user_status("Kavita")

    print("\n--- Simulation End ---")


if __name__ == "__main__":
    main()
