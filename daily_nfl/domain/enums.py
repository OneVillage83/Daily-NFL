"""Canonical enum vocabulary for Daily NFL domain contracts."""

from enum import StrEnum


class SeasonPhase(StrEnum):
    PRESEASON = "PRESEASON"
    REGULAR = "REGULAR"
    POSTSEASON = "POSTSEASON"


class GameStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    IN_PROGRESS = "IN_PROGRESS"
    FINAL = "FINAL"


class GameResultType(StrEnum):
    HOME_WIN = "HOME_WIN"
    AWAY_WIN = "AWAY_WIN"
    TIE = "TIE"


class PlayType(StrEnum):
    PASS = "PASS"
    RUSH = "RUSH"
    SCRAMBLE = "SCRAMBLE"
    SACK = "SACK"
    KNEEL = "KNEEL"
    SPIKE = "SPIKE"
    PUNT = "PUNT"
    FIELD_GOAL = "FIELD_GOAL"
    KICKOFF = "KICKOFF"
    EXTRA_POINT = "EXTRA_POINT"
    TWO_POINT = "TWO_POINT"
    PENALTY_ONLY = "PENALTY_ONLY"
    TIMEOUT = "TIMEOUT"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    OTHER = "OTHER"


class PlayDesignModifier(StrEnum):
    """Play-design mechanics layered on top of the primary play family.

    PLAY_ACTION intentionally refers only to the real football concept. The
    containing domain object is named PlayExecution, never PlayAction.
    """

    PLAY_ACTION = "PLAY_ACTION"
    RPO = "RPO"
    SCREEN = "SCREEN"
    BOOT = "BOOT"
    NAKED_BOOT = "NAKED_BOOT"
    DRAW = "DRAW"
    READ_OPTION = "READ_OPTION"
    SPEED_OPTION = "SPEED_OPTION"
    DESIGNED_QB_RUN = "DESIGNED_QB_RUN"
    DROPBACK = "DROPBACK"
    QUICK_GAME = "QUICK_GAME"
    EMPTY = "EMPTY"
    MOTION = "MOTION"
    SHIFT = "SHIFT"
    UNDER_CENTER = "UNDER_CENTER"
    SHOTGUN = "SHOTGUN"
    NO_HUDDLE = "NO_HUDDLE"


class PlayEventType(StrEnum):
    SNAP = "SNAP"
    DROPBACK = "DROPBACK"
    HANDOFF = "HANDOFF"
    PRESSURE = "PRESSURE"
    THROW = "THROW"
    TARGET = "TARGET"
    CATCH = "CATCH"
    TACKLE = "TACKLE"
    SACK = "SACK"
    FUMBLE = "FUMBLE"
    RECOVERY = "RECOVERY"
    INTERCEPTION = "INTERCEPTION"
    RETURN = "RETURN"
    KICK = "KICK"
    PENALTY = "PENALTY"
    SCORE = "SCORE"
    OTHER = "OTHER"


class ParticipationSide(StrEnum):
    OFFENSE = "OFFENSE"
    DEFENSE = "DEFENSE"
    SPECIAL_TEAMS = "SPECIAL_TEAMS"


class PenaltyDisposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    OFFSETTING = "OFFSETTING"


class AvailabilityMethod(StrEnum):
    SOURCE_TIMESTAMP = "SOURCE_TIMESTAMP"
    ARCHIVED_RELEASE_TIME = "ARCHIVED_RELEASE_TIME"
    OUR_OBSERVATION_TIME = "OUR_OBSERVATION_TIME"
    INFERRED_REPORT_DATE = "INFERRED_REPORT_DATE"
    UNKNOWN = "UNKNOWN"


class AvailabilityConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
