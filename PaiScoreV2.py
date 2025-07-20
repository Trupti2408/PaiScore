import datetime
from math import pow

# -----------------------------
# 1. ACTION_WEIGHTS: Defines scoring, decay, targeting, and role permissions for each action type
# -----------------------------
ACTION_WEIGHTS = {
    "LOGIN": {"score": 0.5, "decay": 0.05, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "AD_LIKED": {"score": 1.0, "target_score": 2.0, "decay": 0.03, "allowed_for": ["common"], "affects_target": True},
    "POSITIVE_COMMENT": {"score": 2.0, "target_score": 2.5, "decay": 0.02, "allowed_for": ["common"], "affects_target": True},
    "AD_SHARED": {"score": 4.0, "target_score": 3.0, "decay": 0.01, "allowed_for": ["common", "advertiser"], "affects_target": True},
    "AD_VISITED": {"score": 0.3, "target_score": 1.5, "decay": 0.07, "allowed_for": ["common"], "affects_target": True},
    "GAINED_FOLLOWER": {"score": 5.0, "decay": 0.01, "allowed_for": ["advertiser"], "affects_target": False},
    "FOLLOWED_USER": {"score": 0.7, "target_score": 1.5, "decay": 0.08, "allowed_for": ["common", "advertiser"], "affects_target": True},
    "SENT_MESSAGE": {"score": 1.0, "decay": 0.03, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "RECEIVED_MESSAGE": {"score": 0.5, "decay": 0.03, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "RESPONDED_TO_MESSAGE": {"score": 1.2,"decay": 0.03,"allowed_for": ["advertiser"],"affects_target": False},
    "ADDED_TO_FAVOURITES": {"score": 4.0, "target_score": 1.0, "decay": 0.01, "allowed_for": ["common"], "affects_target": True},
    "VISITED_PROFILE": {"score": 0.4, "target_score": 0.4, "decay": 0.06, "allowed_for": ["common"], "affects_target": True},
    "AD_POSTED_FREE": {"score": 4.0, "decay": 0.02, "allowed_for": ["advertiser"], "affects_target": False},
    "AD_POSTED_PAI": {"score": 8.0, "decay": 0.01, "allowed_for": ["advertiser"], "affects_target": False},
    "AD_POSTED_MONEY": {"score": 15.0, "decay": 0.005, "allowed_for": ["advertiser"], "affects_target": False},
    "RESPONDED_TO_REVIEW": {"score": 1.0, "target_score": 0.5, "decay": 0.02,"allowed_for": ["advertiser"], "affects_target": True},
    "GAVE_RATING": {"score": 1.5, "decay": 0.04, "allowed_for": ["common"], "affects_target": False},
    "RECEIVED_RATING": {"score": 3.5, "decay": 0.02, "allowed_for": ["advertiser"], "affects_target": False},
    "VERIFIED_PROFILE": {"score": 10.0, "decay": 0.0, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "REVIEW_RECEIVED": {"score": 2.0,"decay": 0.02,"allowed_for": ["advertiser"],"affects_target": False},
    "AD_BLOCKED": {"score": -5.0, "decay": 0.0, "allowed_for": ["advertiser"], "affects_target": False},
    "AD_REPORTED": {"score": -6.0, "decay": 0.0, "allowed_for": ["common"], "affects_target": False},
    "REPORTED_ADVERTISER": {"score": -20.0, "decay": 0.0, "allowed_for": ["advertiser"], "affects_target": False},
    "INACTIVITY": {"score": -3.0, "decay": 0.0, "allowed_for": ["common", "advertiser"], "affects_target": False}
}

BADGE_LEVELS = {
    (0, 29): {"name": "New", "perks": "No PAI coin trade, limited ads"},
    (30, 59): {"name": "Explorer", "perks": "Can view all ads, earn coins"},
    (60, 79): {"name": "Trusted", "perks": "Can trade coins, appear higher in feed"},
    (80, 94): {"name": "Elite", "perks": "Premium ads, faster rewards"},
    (95, 100): {"name": "Ambassador", "perks": "First access, spotlight ads, bonus coins"}
}

MAX_AGE_SCORE_CONTRIBUTION = 20

# -----------------------------
# 2. CLASSES: UserAction, User, PaiSystem (with detailed prints/comments)
# -----------------------------

class UserAction:
    """
    Represents a single user event, and computes (with decay) how
    much it currently affects the user's score.
    """
    def __init__(self, action_type, date=None, actor=True):
        if action_type not in ACTION_WEIGHTS:
            raise ValueError(f"Action type '{action_type}' is not defined.")
        self.action_type = action_type
        self.date = date or datetime.date.today()
        self.actor = actor
        self.weights = ACTION_WEIGHTS[action_type]
        print(f"[UserAction] {action_type} recorded for {'actor' if actor else 'target'} on {self.date}")

    def get_effective_score(self, current_date):
        """
        Returns action's effect on score as of current_date (applies decay).
        """
        days_old = (current_date - self.date).days
        score_key = "score" if self.actor else "target_score"
        base_score = self.weights.get(score_key, 0)
        decay = self.weights.get("decay", 0)
        if decay > 0:
            score = base_score * pow(1 - decay, max(days_old, 0))
        else:
            score = base_score
        print(f"    [UserAction] {self.action_type} ({'actor' if self.actor else 'target'}) worth {score:.2f} after {days_old} day(s)")
        return score

    def __repr__(self):
        who = "actor" if self.actor else "target"
        return f"Action({self.action_type}, {self.date}, {who})"

class User:
    """Represents a user/advertiser in the platform's trust system."""
    def __init__(self, name, creation_date, user_type):
        self.name = name
        self.type = user_type
        self.creation_date = creation_date
        self.action_history = []
        self.score = 0
        self.badge = None
        self.age_score_component = 0
        self.last_action_date = None
        print(f"[User] Created: {name} ({user_type}), joined {creation_date}")

    def add_action(self, action_type, date, actor=True):
        """Record an action for this user as actor or target."""
        action = UserAction(action_type, date, actor)
        self.action_history.append(action)
        if not self.last_action_date or date > self.last_action_date:
            self.last_action_date = date
        print(f"    [User] {self.name}: Action '{action_type}' added ({'actor' if actor else 'target'})")

class PaiSystem:
    """
    Central manager: holds users, current date, computes scores, badges, and flows.
    """
    def __init__(self, history_days=30, inactivity_days=7):
        self.users = {}
        self.history_days = history_days
        self.inactivity_days = inactivity_days
        self.current_date = datetime.date.today()
        print("[PaiSystem] Initialized.")

    def get_or_create_user(self, name, user_type, creation_date=None):
        if name not in self.users:
            print(f"[PaiSystem] Creating {user_type} '{name}'")
            self.users[name] = User(name, creation_date or self.current_date, user_type)
        else:
            if user_type and self.users[name].type != user_type:
                raise ValueError(f"[PaiSystem] Type mismatch for {name}: {self.users[name].type} vs {user_type}.")
        return self.users[name]

    def _get_badge_for_score(self, score):
        for (min_score, max_score), badge_info in BADGE_LEVELS.items():
            if min_score <= score <= max_score:
                return badge_info
        return BADGE_LEVELS[(95,100)] if score > 100 else BADGE_LEVELS[(0,29)]

    def _calculate_age_score(self, user):
        # Age boosts trust: older accounts get a passive bonus
        total_months = (self.current_date.year - user.creation_date.year) * 12 + (self.current_date.month - user.creation_date.month)
        account_age_years = total_months / 12.0
        if account_age_years >= 8:
            age_multiplier = 0.5
        elif account_age_years >= 5:
            age_multiplier = 0.4
        elif account_age_years >= 2:
            age_multiplier = 0.3
        else:
            age_multiplier = 0.15
        user.age_score_component = MAX_AGE_SCORE_CONTRIBUTION * age_multiplier
        print(f"    [PaiSystem] {user.name} account age: {account_age_years:.2f}y -> age bonus {user.age_score_component:.2f}")
        return user.age_score_component

    def update_user_score(self, user_name):
        user = self.users[user_name]
        cutoff = self.current_date - datetime.timedelta(days=self.history_days)
        print(f"[PaiSystem] Calculating score for {user.name}. Considering actions since {cutoff}")

        # Remove stale actions (older than history_days)
        user.action_history = [a for a in user.action_history if a.date >= cutoff]
        score = sum(a.get_effective_score(self.current_date) for a in user.action_history)
        age_score = self._calculate_age_score(user)
        final_score = max(0, min(100, score + age_score))
        user.score = final_score
        user.badge = self._get_badge_for_score(user.score)
        print(f"    [PaiSystem] {user.name}: Total score {user.score:.2f}, badge: {user.badge['name']}\n")

    def advance_time(self, days=1):
        # Move system forward N days and recalc all
        self.current_date += datetime.timedelta(days=days)
        print(f"\n=== [PaiSystem] Advancing time by {days} day(s). New date: {self.current_date} ===")
        for uname in self.users:
            self.update_user_score(uname)

    def print_user_status(self, user_name):
        user = self.users[user_name]
        print("="*45)
        print(f"User Status: {user.name} ({user.type}) on {self.current_date}")
        print(f"  Age Score: {user.age_score_component:.2f} / {MAX_AGE_SCORE_CONTRIBUTION}")
        print(f"  Final Score: {user.score:.2f}")
        if user.badge:
            print(f"  Badge: {user.badge['name']} ({user.badge['perks']})")
        else:
            print("  Badge: None")
        print("="*45)

# -----------------------------
# 3. Action Handler: Processes actions and updates users
# -----------------------------
def handle_user_action(
    pai_system, user_name, action_type, user_type=None, action_date=None, creation_date=None,
    target_user_name=None, target_user_type=None, target_creation_date=None
):
    """Registers an action and, if affects_target, processes it for both parties."""
    if not action_date:
        action_date = pai_system.current_date

    info = ACTION_WEIGHTS.get(action_type)
    if not info:
        print(f"[handle_user_action] Unknown action: {action_type}. Skipped.")
        return

    allowed_for = info["allowed_for"]
    actor = pai_system.get_or_create_user(user_name, user_type, creation_date)
    print(f"\n[handle_user_action] '{actor.name}' is performing '{action_type}'.")

    if actor.type not in allowed_for:
        print(f"  [handle_user_action] Action '{action_type}' not allowed for {actor.type}. Skipped.")
        return actor

    actor.add_action(action_type, action_date, actor=True)
    pai_system.update_user_score(actor.name)

    # Register effect for target, if the action has one.
    if info.get("affects_target"):
        if not target_user_name:
            print("  [handle_user_action] Target user missing for action. Skipped.")
            return actor
        target = pai_system.get_or_create_user(target_user_name, target_user_type, target_creation_date)
        print(f"  [handle_user_action] '{target.name}' is the target of '{action_type}'.")
        target.add_action(action_type, action_date, actor=False)
        pai_system.update_user_score(target.name)
    return actor

# -----------------------------
# 4. Demo/Simulation: See flow, prints, and comments in action
# -----------------------------
def main():
    print("[Demo] Starting PaiScore simulation...")
    pai_system = PaiSystem()
    sim_start_date = datetime.date(2025, 7, 18)
    pai_system.current_date = sim_start_date
    print(f"[Demo] System date set to {sim_start_date}")

    # Scenario 1: User and advertiser login, engagement, dual scoring for like
    print("\n[Scenario 1] Trupti logs in and likes Sai's ad.")
    handle_user_action(pai_system, "Trupti", "LOGIN", user_type="common", creation_date=sim_start_date)
    handle_user_action(pai_system, "Sai", "LOGIN", user_type="advertiser", creation_date=sim_start_date)
    handle_user_action(pai_system, "Trupti", "AD_LIKED", user_type="common", target_user_name="Sai", target_user_type="advertiser")
    pai_system.print_user_status("Trupti")
    pai_system.print_user_status("Sai")

    # Scenario 2: Advertiser gets engagement after posting ad
    print("\n[Scenario 2] Kavita (advertiser) posts an ad and gets a like.")
    handle_user_action(pai_system, "Kavita", "AD_POSTED_PAI", user_type="advertiser", creation_date=datetime.date(2015,1,1))
    handle_user_action(pai_system, "Sravan", "AD_LIKED", user_type="common", target_user_name="Kavita", target_user_type="advertiser")
    pai_system.print_user_status("Kavita")
    pai_system.print_user_status("Sravan")

    # Scenario 3: Sravan comments and follows
    print("\n[Scenario 3] Sravan comments and follows Kavita.")
    handle_user_action(pai_system, "Sravan", "POSITIVE_COMMENT", user_type="common", target_user_name="Kavita", target_user_type="advertiser")
    handle_user_action(pai_system, "Sravan", "FOLLOWED_USER", user_type="common", target_user_name="Kavita", target_user_type="advertiser")
    pai_system.print_user_status("Kavita")
    pai_system.print_user_status("Sravan")

    # Simulating passage of time to show decay in score
    print("\n[Scenario 4] Advance 35 days: How do scores decay?")
    pai_system.advance_time(35)
    pai_system.print_user_status("Sravan")
    pai_system.print_user_status("Kavita")

    print("\n[Demo] Simulation complete.")

if __name__ == "__main__":
    main()
