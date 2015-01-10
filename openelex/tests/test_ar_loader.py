from unittest import TestCase, skipUnless

from mock import patch

from openelex.tests import (cache_file_exists, CACHED_FILE_MISSING_MSG,
    LoaderPrepMixin)

from openelex.us.ar.load import ClarityLoader

class TestClarityLoader(LoaderPrepMixin, TestCase):
    def setUp(self):
        self.loader = ClarityLoader()

    def test_parse_contest(self):
        test_data = [
            ("State Representative District 66 - REP", "State Representative",
             "66", "REP"),
        ]
        for s, expected_office, expected_district, expected_party in test_data:
            self._test_parse_contest(s, expected_office, expected_district,
                                     expected_party)

    def _test_parse_contest(self, s, expected_office, expected_district,
            expected_party):
        office, district, party = self.loader._parse_contest(s)
        self.assertEqual(office, expected_office)
        self.assertEqual(district, expected_district)
        self.assertEqual(party, expected_party)

    @skipUnless(cache_file_exists('ar',
        '20120522__ar__primary__van_buren__precinct.xml'), CACHED_FILE_MISSING_MSG)
    # TODO: What's the correct way to do multiple patches?
    @patch('openelex.base.load.BaseLoader._build_common_election_kwargs')
    @patch('openelex.us.ar.datasource.Datasource.mapping_for_file')
    def test_results(self, mock_mapping_for_file,
                     mock_build_common_election_kwargs):
        filename = '20120522__ar__primary__van_buren__precinct.xml'

        # Mock Datasource.mapping_for_file() so we don't have to hit the real API
        # TODO: Valid mapping dict here.  I'm just trying to include enough
        # to write these tests
        mock_mapping_for_file.return_value = {
            'generated_filename': filename, 
            'election': 'ia-2012-05-22-primary',
        }

        # Mock BaseLoader._build_common_election_kwargs so we don't have to
        # hit the real API.
        # TODO: Valid dict here.  I'm just trying to include enough detail to
        # make the calling code work without hitting the API
        mock_build_common_election_kwargs.return_value = {}

        mapping = self._get_mapping(filename)
        self._prep_loader_attrs(mapping)

        # Some metadata about this election, used for calculating
        # expected number of results
        num_precincts = 9
        num_rep_candidates = 2 # There are only Republicans in this contest
        # Overvotes and undervotes
        num_pseudo_candidates = 2
        # There should be one result per precinct for every candidate and
        # every pseudo candidate, plus for one county-level result for each
        # pseudo-candidate
        num_results_expected = ((num_rep_candidates + num_pseudo_candidates) *
            (num_precincts + 1))

        # Get all results for the State Representative, district
        # 66 race
        results = [r for r in self.loader._results(mapping)
            if r.office == "State Representative" and r.district == "66"]
        self.assertEqual(len(results), num_results_expected)
