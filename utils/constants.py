class Choices:
    @classmethod
    def choices(cls):
        d = cls.__dict__
        return [d[item] for item in d.keys() if not item.startswith("__")]


class ContestType:
    PUBLIC_CONTEST = "Public"
    PASSWORD_PROTECTED_CONTEST = "Password Protected"


class ContestStatus:
    CONTEST_NOT_START = "1"
    CONTEST_ENDED = "-1"
    CONTEST_UNDERWAY = "0"


class ContestRuleType(Choices):
    ACM = "ACM"
    OI = "OI"


class CacheKey:
    waiting_queue = "waiting_queue"
    contest_rank_cache = "contest_rank_cache"
    website_config = "website_config"


class Difficulty(Choices):
    E1 = "E1"
    M1 = "M1"
    H1 = "H1"
    E2 = "E2"
    M2 = "M2"
    H2 = "H2"
    E3 = "E3"
    M3 = "M3"
    H3 = "H3"
    E4 = "E4"
    M4 = "M4"
    H4 = "H4"
    E5 = "E5"
    M5 = "M5"
    H5 = "H5"

CONTEST_PASSWORD_SESSION_KEY = "contest_password"
