import requests
import json
from datetime import datetime
from typing import List, Dict, Any

class ResearchAnalystAgent:
    """
    Agent 2: The Analyst
    Responsibilities:
    1. Fetch papers for a specific author via Semantic Scholar API.
    2. Filter papers by recency and completeness.
    3. Score papers against student interests (Semantic/Keyword matching).
    4. Output a structured JSON payload for Agent 3.
    """

    def __init__(self, semanticscholar_api_key: str = None):
        # Public API is free but rate-limited. Add key if high volume needed.
        self.headers = {}
        if semanticscholar_api_key:
            self.headers = {'x-api-key': semanticscholar_api_key}
        
        self.base_url = "https://api.semanticscholar.org/graph/v1"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution entry point.
        Expects input_data to contain: 'authorId', 'student_skills', 'student_interests'
        """
        print(f"🕵️  Agent 2 Analysis started for Author ID: {input_data.get('authorId')}...")

        # 1. FETCH
        raw_papers = self._fetch_papers(input_data['authorId'])
        if not raw_papers:
            return {"error": "No papers found or API error."}

        # 2. ANALYZE & RANK
        scored_papers = self._rank_papers(
            raw_papers, 
            input_data['student_interests'], 
            input_data['student_skills']
        )

        # 3. SELECT (Top 3)
        top_papers = scored_papers[:3]

        # 4. FORMAT OUTPUT (for Agent 3)
        output_payload = {
            "professor_name": input_data.get('professor_name', 'Unknown'),
            "analysis_timestamp": datetime.now().isoformat(),
            "student_profile_used": {
                "skills": input_data['student_skills'],
                "interests": input_data['student_interests']
            },
            "recommended_papers": top_papers
        }
        
        return output_payload

    def _fetch_papers(self, author_id: str, limit: int = 50) -> List[Dict]:
        """
        Fetches the most recent papers with abstracts.
        """
        endpoint = f"{self.base_url}/author/{author_id}/papers"
        
        # We request specific fields to minimize payload size
        params = {
            "fields": "title,abstract,year,citationCount,url,isOpenAccess",
            "limit": limit
        }

        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching papers: {e}")
            return []

    def _rank_papers(self, papers: List[Dict], interests: List[str], skills: List[str]) -> List[Dict]:
        """
        The 'Brain' of the agent.
        Scores papers based on keyword overlap with student profile.
        """
        ranked = []
        
        # Combine lists and normalize to lowercase for matching
        target_keywords = set([k.lower() for k in interests + skills])
        
        for paper in papers:
            # FILTER: Skip if no abstract or too old (e.g., older than 2018)
            if not paper.get('abstract') or paper.get('year') is None:
                continue
            if paper['year'] < 2018: 
                continue

            # PREPARE TEXT
            # We weight the title more heavily (2x) than the abstract
            text_content = (paper['title'] + " ") * 2 + paper['abstract']
            text_content = text_content.lower()

            # SCORING LOGIC
            score = 0
            matches = []
            
            for keyword in target_keywords:
                if keyword in text_content:
                    score += 1
                    matches.append(keyword)
            
            # Simple heuristic: Bonus points for high citation count (validation)
            # Logarithmic scale would be better, but linear / 100 is fine for simple logic
            citation_boost = min(paper.get('citationCount', 0) / 100.0, 2.0)
            
            final_score = score + citation_boost

            if final_score > 0:
                ranked.append({
                    "title": paper['title'],
                    "year": paper['year'],
                    "url": paper['url'],
                    "relevance_score": round(final_score, 2),
                    "matched_keywords": matches,
                    "abstract_snippet": paper['abstract'][:200] + "..." # Truncate for cleaner output
                })

        # Sort by score descending
        return sorted(ranked, key=lambda x: x['relevance_score'], reverse=True)

# --- EXAMPLE USAGE ---

if __name__ == "__main__":
    # Mock Data typically coming from Agent 1
    # Example: Dr. Fei-Fei Li (Stanford), Semantic Scholar ID: 1741101
    input_from_agent_1 = {
        "professor_name": "Dr. Fei-Fei Li",
        "authorId": "1741101", 
        "student_interests": ["Computer Vision", "Deep Learning", "Healthcare"],
        "student_skills": ["Python", "PyTorch", "Image Segmentation"]
    }

    # Initialize Agent
    agent_2 = ResearchAnalystAgent() 
    
    # Run Agent
    result = agent_2.run(input_from_agent_1)

    # Print Result (simulating Output to Agent 3)
    print("\n--- OUTPUT FOR AGENT 3 ---")
    print(json.dumps(result, indent=2))