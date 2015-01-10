"""Load Arkansas results"""
import logging
import re

import clarify

from openelex.base.load import BaseLoader
from openelex.lib.text import ocd_type_id
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

    CONTEST_RE = re.compile('(?P<office>{offices})'
        '(\s+District\s+(?P<district>\d+)){{0,1}}'
        '(\s+-\s+(?P<party>[A-Z]+)){{0,1}}'.format(offices='|'.join(OFFICES)),
        re.IGNORECASE
    )

    VOTE_TYPE_LOOKUP = {
        'Early Vote': 'early',
        'Absentee': 'absentee',
        'Election Day': 'election_day',
    }
    """
    Map of vote type identifiers found in the results files to the canonical
    identifiers in models.VOTES_TYPE_CHOICES.
    """

    def load(self):
        RawResult.objects.insert(self._results(self.mapping))

    def _results(self, mapping):
        base_kwargs = self._build_common_election_kwargs()
        results = []

        with self._file_handle as inputfile:
            parser = clarify.Parser()
            parser.parse(inputfile)
            county_ocd_id = ('ocd-division/country:us/state:ar/county:' +
                             ocd_type_id(parser.region))
            for parsed_result in parser.results:
                reporting_level, jurisdiction, ocd_id = self._parse_jurisdiction_info(
                    parsed_result.jurisdiction, parser.region, county_ocd_id)
                office, district, primary_party = self._parse_contest(parsed_result.contest.text)
                results.append(RawResult(
                    primary_party=primary_party,
                    office=office,
                    district=district,
                    full_name=parsed_result.choice.text,
                    party=parsed_result.choice.name,
                    reporting_level=reporting_level,
                    jurisdiction=jurisdiction,
                    ocd_id=ocd_id,
                    votes=parsed_result.votes,
                    votes_type=self._parse_votes_type(parsed_result.vote_type),
                    **base_kwargs
                ))

        return results

    @classmethod
    def _parse_jurisdiction_info(cls, jurisdiction, county_name, county_ocd_id):
        """
        Parse the reporting level, jurisdiction string and ocd_id for the
        jurisdiction.

        Args:
            jurisdiction (obj): Jurisdiction object representing the result's
                                jurisdiction.
            county_name (string): Name of the county.
            county_ocd_id (string): OCD ID for the county.

        Returns:
            Tuple where the first item is a string identifying the reporting 
            level (either 'precinct' or 'county'), the second item is the
            jurisdiction string and the third item is the OCD ID string. 
           
        """
        if jurisdiction is None:
            # The jurisdiction attribute of the result object is None.
            # This means that the reporting level and the name of the
            # jurisdiction is that of the whole file, in this case,
            # the county.
            reporting_level = 'county'
            jurisdiction_name = county_name
            ocd_id = county_ocd_id
        else:
            reporting_level = jurisdiction.level
            jurisdiction_name = jurisdiction.name
            ocd_id = (county_ocd_id + '/precinct:' +
                      ocd_type_id(jurisdiction_name))

        return reporting_level, jurisdiction_name, ocd_id

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
        m = cls.CONTEST_RE.match(s)
        if m is not None:
            office = m.group('office')
            district = m.group('district')
            party = m.group('party')

        return office, district, party

    @classmethod
    def _parse_votes_type(cls, s):
        """
        Convert vote type in XML file to value in models.VOTES_TYPE_CHOICES
        """
        try:
            return cls.VOTE_TYPE_LOOKUP[s]
        except KeyError:
            return None
