import datetime
from math import pow

# 1. ACTION_WEIGHTS holds rules for: scoring, decay, permissions, targets, delay penalties
ACTION_WEIGHTS = {
    "LOGIN": {"score": 0.5, "decay": 0.05, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "AD_LIKED": {"score": 1.0, "target_score": 2.0, "decay": 0.03,
                 "allowed_for": ["common"], "affects_target": True, "delay_factor": 0.97},
    "POSITIVE_COMMENT": {"score": 2.0, "target_score": 2.5, "decay": 0.02,
                         "allowed_for": ["common"], "affects_target": True, "delay_factor": 0.98},
    "AD_SHARED": {"score": 4.0, "target_score": 3.0, "decay": 0.01,
                  "allowed_for": ["common", "advertiser"], "affects_target": True, "delay_factor": 0.98},
    "AD_VISITED": {"score": 0.3, "target_score": 1.5, "decay": 0.07,
                   "allowed_for": ["common"], "affects_target": True, "delay_factor": 0.96},
    "GAINED_FOLLOWER": {"score": 5.0, "decay": 0.01, "allowed_for": ["advertiser"], "affects_target": False},
    "FOLLOWED_USER": {"score": 0.7, "target_score": 1.5, "decay": 0.08,
                      "allowed_for": ["common", "advertiser"], "affects_target": True},
    "SENT_MESSAGE": {"score": 1.0, "decay": 0.03, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "RECEIVED_MESSAGE": {"score": 0.5, "decay": 0.03, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "RESPONDED_TO_MESSAGE": {"score": 1.2,"decay": 0.03,"allowed_for": ["advertiser"],"affects_target": False},
    "ADDED_TO_FAVOURITES": {"score": 4.0, "target_score": 1.0, "decay": 0.01,
                            "allowed_for": ["common"], "affects_target": True, "delay_factor": 0.97},
    "VISITED_PROFILE": {"score": 0.4, "target_score": 0.4, "decay": 0.06,
                        "allowed_for": ["common"], "affects_target": True},
    "AD_POSTED_FREE": {"score": 4.0, "decay": 0.02, "allowed_for": ["advertiser"], "affects_target": False},
    "AD_POSTED_PAI": {"score": 8.0, "decay": 0.01, "allowed_for": ["advertiser"], "affects_target": False},
    "AD_POSTED_MONEY": {"score": 15.0, "decay": 0.005, "allowed_for": ["advertiser"], "affects_target": False},
    "RESPONDED_TO_REVIEW": {"score": 1.0, "target_score": 0.5, "decay": 0.02,
                            "allowed_for": ["advertiser"], "affects_target": True, "delay_factor": 0.99},
    "GAVE_RATING": {"score": 1.5, "decay": 0.04, "allowed_for": ["common"], "affects_target": False},
    "RECEIVED_RATING": {"score": 3.5, "decay": 0.02, "allowed_for": ["advertiser"], "affects_target": False},
    "VERIFIED_PROFILE": {"score": 10.0, "decay": 0.0, "allowed_for": ["common", "advertiser"], "affects_target": False},
    "REVIEW_RECEIVED": {"score": 2.0,"decay": 0.02,"allowed_for": ["advertiser"],"affects_target": False},
    "AD_BLOCKED": {"score": -5.0, "decay": 0.0, "allowed_for": ["advertiser"], "affects_target": False},
    "AD_REPORTED": {"score": -6.0, "decay": 0.0, "allowed_for": ["common"], "affects_target": False},
    "REPORTED_ADVERTISER": {"score": -20.0, "decay": 0.0, "allowed_for": ["advertiser"], "affects_target": False},
    "INACTIVITY": {"score": -3.0, "decay": 0.0, "allowed_for": ["common", "advertiser"], "affects_target": False}
}

# Badge tiers based on PAI score
BADGE_LEVELS = {
    (0, 29): {"name": "New", "perks": "No PAI coin trade, limited ads"},
    (30, 59): {"name": "Explorer", "perks": "Can view all ads, earn coins"},
    (60, 79): {"name": "Trusted", "perks": "Can trade coins, appear higher in feed"},
    (80, 94): {"name": "Elite", "perks": "Premium ads, faster rewards"},
    (95, 100): {"name": "Ambassador", "perks": "First access, spotlight ads, bonus coins"}
}

MAX_AGE_SCORE_CONTRIBUTION = 20

# ----------------------------
# Classes for actions, users, and the PaiSystem.
# ----------------------------
class UserAction:
    """
    Stores an action with metadata for scoring.
    Will use delay_days to further decrease its value if delay_factor is defined for this action type.
    """
    def __init__(self, action_type, date=None, actor=True, delay_days=0):
        if action_type not in ACTION_WEIGHTS:
            raise ValueError(f"Action type '{action_type}' is not defined.")
        self.action_type = action_type
        self.date = date or datetime.date.today()
        self.actor = actor  # actor=True: performed the action; False: recipient/target
        self.weights = ACTION_WEIGHTS[action_type]
        self.delay_days = delay_days

    def get_effective_score(self, current_date):
        """
        Score effective as of now, decayed by days_old and penalized for any delay spesified.
        """
        days_old = (current_date - self.date).days
        # Score type: actor or target impact
        score_key = "score" if self.actor else "target_score"
        base_score = self.weights.get(score_key, 0)
        decay = self.weights.get("decay", 0)
        delay_factor = self.weights.get("delay_factor", 1.0)  # If not set, no delay penalty

        # Temporal decay (older actions fade)
        score = base_score
        if decay > 0:
            score *= pow(1 - decay, max(days_old, 0))
        # Additional score reduction if there was a delay between related actions (e.g., like after ad posted)
        if self.delay_days > 0 and delay_factor < 1.0:
            score *= pow(delay_factor, self.delay_days)
        return score

    def __repr__(self):
        who = "actor" if self.actor else "target"
        return f"Action({self.action_type}, {self.date}, {who}, delay={self.delay_days})"

class User:
    """Tracks the user's profile and all their actions."""
    def __init__(self, name, creation_date, user_type):
        self.name = name
        self.type = user_type  # 'common' or 'advertiser'
        self.creation_date = creation_date
        self.action_history = []
        self.score = 0
        self.badge = None
        self.age_score_component = 0
        self.last_action_date = None

    def add_action(self, action_type, date, actor=True, delay_days=0):
        action = UserAction(action_type, date, actor, delay_days)
        self.action_history.append(action)
        if not self.last_action_date or date > self.last_action_date:
            self.last_action_date = date

class PaiSystem:
    """
    System context: manages current date, all users, and performs
    all scoring logic and reporting.
    """
    def __init__(self, history_days=30, inactivity_days=7):
        self.users = {}
        self.history_days = history_days
        self.inactivity_days = inactivity_days
        self.current_date = datetime.date.today()

    def get_or_create_user(self, name, user_type, creation_date=None):
        if name not in self.users:
            self.users[name] = User(name, creation_date or self.current_date, user_type)
        else:
            # Safe-guard: Don't accidentally change user types
            if user_type and self.users[name].type != user_type:
                raise ValueError(f"User '{name}' type mismatch.")
        return self.users[name]

    def _get_badge_for_score(self, score):
        for (min_score, max_score), badge_info in BADGE_LEVELS.items():
            if min_score <= score <= max_score:
                return badge_info
        if score > 100: return BADGE_LEVELS[(95,100)]
        if score < 0: return BADGE_LEVELS[(0,29)]
        return None

    def _calculate_age_score(self, user):
        # Older accounts get more trust
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
        return user.age_score_component

    def update_user_score(self, user_name):
        user = self.users[user_name]
        # Only recent actions (by history_days) count
        cutoff = self.current_date - datetime.timedelta(days=self.history_days)
        user.action_history = [a for a in user.action_history if a.date >= cutoff]
        # Score sum and apply age bonus
        score = sum(a.get_effective_score(self.current_date) for a in user.action_history)
        age_score = self._calculate_age_score(user)
        final_score = max(0, min(100, score + age_score))
        user.score = final_score
        user.badge = self._get_badge_for_score(user.score)

    def advance_time(self, days=1):
        """
        Move simulated system date N days forward, which will cause existing action
        scores to decay if they are older than before.
        """
        self.current_date += datetime.timedelta(days=days)
        for uname in self.users:
            self.update_user_score(uname)

    def print_user_status(self, user_name):
        # Outputs a summary report for the user for the current system date
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

def handle_user_action(
    pai_system, user_name, action_type, user_type=None, action_date=None, creation_date=None,
    target_user_name=None, target_user_type=None, target_creation_date=None,
    delay_days=0, target_delay_days=0
):
    """
    This is the entry point to register an action:
      - actor: user who performs the action
      - target: (optional) user who benefits (eg: advertiser whose ad is liked)
      - delay_days: how long after original (eg: ad post) did the action occur?
    """
    if not action_date:
        action_date = pai_system.current_date

    info = ACTION_WEIGHTS.get(action_type)
    if not info:
        return

    allowed_for = info["allowed_for"]
    actor = pai_system.get_or_create_user(user_name, user_type, creation_date)
    if actor.type not in allowed_for:
        return actor

    actor.add_action(action_type, action_date, actor=True, delay_days=delay_days)
    pai_system.update_user_score(actor.name)

    if info.get("affects_target"):
        if not target_user_name:
            return actor
        target = pai_system.get_or_create_user(target_user_name, target_user_type, target_creation_date)
        target.add_action(action_type, action_date, actor=False, delay_days=target_delay_days if target_delay_days else delay_days)
        pai_system.update_user_score(target.name)
    return actor

def main():
    pai_system = PaiSystem()
    sim_start_date = datetime.date(2025, 7, 18)
    pai_system.current_date = sim_start_date

    # ----------------------------
    # Scenario 1: Dual login & cross-like (see instant and delayed scoring)
    # ----------------------------
    print("\n[Scenario 1] Trupti logs in and likes Sai's ad.")
    handle_user_action(pai_system, "Trupti", "LOGIN", user_type="common", creation_date=sim_start_date)
    handle_user_action(pai_system, "Sai", "LOGIN", user_type="advertiser", creation_date=sim_start_date)
    handle_user_action(pai_system, "Trupti", "AD_LIKED", user_type="common",
                       target_user_name="Sai", target_user_type="advertiser")
    pai_system.print_user_status("Trupti")
    pai_system.print_user_status("Sai")

    # ----------------------------
    # Scenario 2: Advertiser posts an ad, another user likes ad instantly
    # ----------------------------
    print("\n[Scenario 2] Kavita (advertiser) posts an ad and gets a like.")
    handle_user_action(pai_system, "Kavita", "AD_POSTED_PAI", user_type="advertiser", creation_date=datetime.date(2015,1,1))
    handle_user_action(pai_system, "Sravan", "AD_LIKED", user_type="common",
                       target_user_name="Kavita", target_user_type="advertiser")
    pai_system.print_user_status("Kavita")
    pai_system.print_user_status("Sravan")

    # ----------------------------
    # Scenario 3: Sravan leaves a comment and follows Kavita; both have a positive effect
    # ----------------------------
    print("\n[Scenario 3] Sravan comments and follows Kavita.")
    handle_user_action(pai_system, "Sravan", "POSITIVE_COMMENT", user_type="common",
                       target_user_name="Kavita", target_user_type="advertiser")
    handle_user_action(pai_system, "Sravan", "FOLLOWED_USER", user_type="common",
                       target_user_name="Kavita", target_user_type="advertiser")
    pai_system.print_user_status("Kavita")
    pai_system.print_user_status("Sravan")

    # ----------------------------
    # Scenario 4: Time passes, see how scores decay
    # ----------------------------
    print("\n[Scenario 4] Advance 35 days: How do scores decay?")
    pai_system.advance_time(35)
    pai_system.print_user_status("Sravan")
    pai_system.print_user_status("Kavita")
    pai_system.print_user_status("Sai")
    pai_system.print_user_status("Trupti")

    print("\n[Demo] Simulation complete.")

if __name__ == "__main__":
    main()
