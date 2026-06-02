"""
episodes_per_entity.py
EpisodesPerEntity — a specialized Episodes subclass that enforces
one row per entity.
"""
from __future__ import annotations
import pandas as pd
from .episodes import Episodes
from eventus.semantics.episode_semantics import EpisodeSemantics

_ERROR_PREFIX = "[EpisodesPerEntity] Error"


class EpisodesPerEntity(Episodes):
    """
    An Episodes collection where each entity appears exactly once.

    Inherits all validation from Episodes. Adds one additional
    constraint: entity_id_col must be unique across all rows.

    Useful for observation period data, membership tables, or any
    dataset where one row per entity is a structural requirement.

    Raises
    ------
    ValueError
        If any entity appears more than once in .data.
    """

    # ── Attributes ───────────────────────────────────────────────────────
    # Inherited from Episodes
    data:      pd.DataFrame      # validated episode rows, index reset
    semantics: EpisodeSemantics  # column mappings and identity label
    # Own — none beyond inherited

    def __init__(
        self,
        data:      pd.DataFrame,
        semantics: EpisodeSemantics,
    ) -> None:
        super().__init__(data, semantics)
        self._validate_one_row_per_entity()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate_one_row_per_entity(self) -> None:
        """Raise if any entity appears more than once in .data."""
        col        = self.semantics.entity_id_col
        duplicated = self.data[self.data[col].duplicated(keep=False)]
        if not duplicated.empty:
            dupes = duplicated[col].unique().tolist()
            raise ValueError(
                f"{_ERROR_PREFIX}: entity_id_col '{col}' must be unique "
                f"across all rows. Duplicate entities found: {dupes[:5]}"
                f"{'...' if len(dupes) > 5 else ''}"
            )

    # ------------------------------------------------------------------ #
    # Public methods — override to return EpisodesPerEntity not Episodes
    # ------------------------------------------------------------------ #

    def copy(self) -> "EpisodesPerEntity":
        """Return a copy of this EpisodesPerEntity."""
        return EpisodesPerEntity._construct_from_cleaned(
            self.data.copy(),
            self.semantics,
        )

    def return_as_obs_period(
        self,
        identity: str | None = None,
    ) -> "ObsPeriodPerEntity":
        """
        Promote this EpisodesPerEntity to an ObsPeriodPerEntity.

        Use when you already have an EpisodesPerEntity and need to pass
        it to an analyzer that requires an ObsPeriodPerEntity.

        Parameters
        ----------
        identity : str | None
            Identity label for the observation period.
            Default 'general_entity'.

        Returns
        -------
        ObsPeriodPerEntity
        """
        from .obs_period_per_entity import ObsPeriodPerEntity
        return ObsPeriodPerEntity._construct_from_cleaned(
            self.data.copy(),
            self.semantics,
            identity=identity,
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EpisodesPerEntity(\n"
            f"  entities   : {len(self):,}\n"
            f"  entity_col : '{self.semantics.entity_id_col}'\n"
            f"  start_col  : '{self.semantics.start_time_col}'\n"
            f"  end_col    : '{self.semantics.end_time_col}'\n"
            f")"
        )
