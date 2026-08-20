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
    """Play-design concepts layered on top of the primary play type.

    PLAY_ACTION intentionally refers only to the football concept. The
    containing domain object is named PlayExecution, never PlayAction.
    """

    PLAY_ACTION = "PLAY_ACTION"
    RPO = "RPO"
    SCREEN = "SCREEN"
    SHOTGUN = "SHOTGUN"
    UNDER_CENTER = "UNDER_CENTER"
    MOTION = "MOTION"
    SHIFT = "SHIFT"
    NO_HUDDLE = "NO_HUDDLE"
    DESIGNED_QB_RUN = "DESIGNED_QB_RUN"


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
