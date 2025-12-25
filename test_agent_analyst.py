import unittest
from unittest.mock import patch, MagicMock

import requests
from agent2_analyst import ResearchAnalystAgent

class TestResearchAnalystAgent(unittest.TestCase):

    def setUp(self):
        """Runs before every test. Sets up a basic agent instance."""
        self.agent = ResearchAnalystAgent(semanticscholar_api_key="dummy_key")
        
        # Sample input data consistent with Agent 1's output
        self.input_data = {
            "professor_name": "Dr. Test",
            "authorId": "12345",
            "student_interests": ["Deep Learning", "NLP"],
            "student_skills": ["Python", "Transformers"]
        }

        # Sample raw papers to test the ranking logic
        self.mock_papers = [
            {
                "title": "Deep Learning with Transformers",
                "abstract": "A study on NLP using Python and Transformers.",
                "year": 2023,
                "citationCount": 50,
                "url": "http://paper1.com"
            },
            {
                "title": "Old History of AI",
                "abstract": "Deep Learning concepts from the past.",
                "year": 2010, # Too old (should be filtered)
                "citationCount": 100,
                "url": "http://paper2.com"
            },
            {
                "title": "Irrelevant Biology Study",
                "abstract": "Cells and mitochondria analysis.",
                "year": 2022,
                "citationCount": 5,
                "url": "http://paper3.com"
            }
        ]

    # --- TEST 1: LOGIC & RANKING ---
    def test_rank_papers_logic(self):
        """Test if the agent correctly filters and ranks papers."""
        ranked = self.agent._rank_papers(
            self.mock_papers, 
            self.input_data["student_interests"], 
            self.input_data["student_skills"]
        )

        # Assertion 1: Old paper (2010) should be removed
        years = [p['year'] for p in ranked]
        self.assertNotIn(2010, years)

        # Assertion 2: The "Deep Learning" paper should be #1
        self.assertEqual(ranked[0]['title'], "Deep Learning with Transformers")

        # Assertion 3: Verify keyword matching
        self.assertIn("transformers", ranked[0]['matched_keywords'])
        self.assertIn("python", ranked[0]['matched_keywords'])

    # --- TEST 2: API MOCKING (Success Case) ---
    @patch('agent2_analyst.requests.get')
    def test_run_success(self, mock_get):
        """Test the full flow with a mocked successful API response."""
        
        # Configure the mock to return our sample papers
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': self.mock_papers}
        mock_get.return_value = mock_response

        # Run the agent
        result = self.agent.run(self.input_data)

        # Check that the output structure is correct for Agent 3
        self.assertIn("recommended_papers", result)
        self.assertEqual(len(result["recommended_papers"]), 2) # 3 total - 1 old = 2 left
        self.assertEqual(result["professor_name"], "Dr. Test")

     # --- TEST 3: API MOCKING (Empty/Error Case) ---
    @patch('agent2_analyst.requests.get') # Make sure this matches your filename!
    def test_run_api_failure(self, mock_get):
        """Test how the agent handles API errors."""
        
        # Simulate a RequestException (what requests actually throws)
        mock_response = MagicMock()
        # FIX: Change 'Exception' to 'requests.exceptions.RequestException'
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("API Error")
        mock_get.return_value = mock_response

        result = self.agent.run(self.input_data)

        # Should return an error dict, not crash
        self.assertIn("error", result)
        self.assertEqual(result["error"], "No papers found or API error.")


    # --- TEST 4: EDGE CASE (No Abstract) ---
    def test_filter_no_abstract(self):
        """Ensure papers without abstracts are skipped."""
        bad_paper = [{
            "title": "Ghost Paper",
            "abstract": None, # Missing abstract
            "year": 2023
        }]
        ranked = self.agent._rank_papers(bad_paper, ["AI"], ["Python"])
        self.assertEqual(len(ranked), 0)

if __name__ == '__main__':
    unittest.main()