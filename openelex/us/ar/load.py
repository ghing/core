"""Load Arkansas results"""
import logging

import clarify

from openelex.base.load import BaseLoader
from openelex.models import RawResult

from openelex.us.ar.datasource import Datasource


class LoadResults(object):
    """
    Entry point for Arkansas data loading.

    Determines appropriate loader class for a results file and triggers load
    process.

    """
    def run(self, mapping):
        loader = self._get_loader(mapping)
        loader.run(mapping)

    def _get_loader(self, mapping):
        if self._is_clarity(mapping):
            return ClarityLoader()
        else:
            return SkipLoader()

    @classmethod
    def _is_clarity(cls, mapping):
        try:
            return 'results.enr.clarityelections.com' in mapping['raw_url']
        except KeyError:
            # No 'raw_url' key in mapping.  It's not a Clarity result
            return False


# TODO: Actually implement loaders for all our files and remove this
class SkipLoader(BaseLoader):
    """
    Temporary no-op loader for result files that lack real loader classes

    This pattern helps us avoid lots of branching or lookups when picking
    a loader class.
    """
    def run(self, mapping):
        logging.warn("Skipping file {}".format(mapping['generated_filename']))


# TODO: Factor this out of Arkansas' module because there shouldn't be
# any differences in this implementation from state-to-state
class ClarityLoader(BaseLoader):
    """
    Load results from XML report files from clarity based systems.
    """
    datasource = Datasource()

    OFFICES = [
        "State Senate",
        "U.S. President",
        "State Representative",
        # TODO: Add to offices
    ]

    def load(self):
        RawResult.objects.insert(self._results(self.mapping))

    def _results(self, mapping):
        base_kwargs = self._build_common_election_kwargs()
        results = []

        with self._file_handle as inputfile:
            parser = clarify.Parser()
            parser.parse(inputfile)
            for parsed_result in parser.results:
                reporting_level = parsed_result.jurisdiction.level
                # TODO: calculate ocd_id
                ocd_id = None
                office, district, primary_party = self._parse_contest(parsed_result.contest.text)
                results.append(RawResult(
                    primary_party=primary_party,
                    office=office,
                    district=district,
                    full_name=parsed_result.choice.text,
                    party=parsed_result.choice.name,
                    reporting_level=reporting_level,
                    jurisdiction=parsed_result.jurisdiction.name,
                    ocd_id=ocd_id,
                    votes=parsed_result.votes,
                    votes_type=self._parse_votes_type(parsed_result.vote_type),
                    **base_kwargs
                ))

        return results

    @classmethod
    def _parse_contest(cls, s):
        """
        Parse office and party information
        
        Args:
            contest: clarify.Contest object

        Returns:
            Tuple where the first value is a string containing the name of the
            office and the second value is the district, if applicable and
            the third string contains the party if it's a primary.
        """
        office = None
        district = None
        party = None
        # TODO: Implement this

        return office, district, party

    @classmethod
    def _parse_votes_type(cls, s):
        # TODO: Implement this
        return None
