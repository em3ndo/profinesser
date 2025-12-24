import requests
from typing import List, Optional
from BaseStorage import BaseStorage
from DataTypes import Faculty


class FacultyAgent:
    def __init__(self, storage: BaseStorage, email: Optional[str] = None):
        self.storage = storage
        self.base_url = "https://api.openalex.org"
        # Flexible User-Agent: Uses Polite Pool if email provided, otherwise standard
        agent_str = f"FacultyAgent/1.0 (mailto:{email})" if email else "FacultyAgent/1.0"
        self.headers = {"User-Agent": agent_str}

    def get_experts(self, school_name: str, skill_keyword: str, limit: int = 10) -> List[Faculty]:
        # 1. Try Local Cache Search (The "Keyword Retrieval" goal)
        cached = self.storage.search_cache(skill_keyword)
        if cached:
            # Filter by institution name locally to ensure school relevance
            school_matches = [f for f in cached if school_name.lower() in f.last_known_institution.lower()]
            if school_matches:
                print(f"DEBUG: Found {len(school_matches)} experts in local cache.")
                return sorted(school_matches, key=lambda x: x.h_index, reverse=True)[:limit]

        print(f"DEBUG: Cache miss. Fetching {skill_keyword} experts from OpenAlex...")
        
        # 2. Get School ID
        inst_res = requests.get(f"{self.base_url}/institutions", params={"search": school_name}, headers=self.headers).json()
        if not inst_res['results']: return []
        school_id = inst_res['results'][0]['id']
        school_display = inst_res['results'][0]['display_name']

        # 3. Find Works & Map Authors
        works_params = {
            "filter": f"institutions.id:{school_id},title_and_abstract.search:{skill_keyword},publication_year:>2021",
            "per_page": 50
        }
        works_data = requests.get(f"{self.base_url}/works", params=works_params, headers=self.headers).json()
        
        potential_map = {}
        for work in works_data.get('results', []):
            for authorship in work.get('authorships', []):
                if any(inst.get('id') == school_id for inst in authorship.get('institutions', [])):
                    auth_id = authorship.get('author', {}).get('id')
                    if auth_id:
                        potential_map[auth_id] = work.get('title')

        # 4. Hydrate, Filter for 'Computer Science', and Verify Affiliation
        verified_list = []
        auth_ids = list(potential_map.keys())
        for i in range(0, len(auth_ids), 50):
            batch = "|".join(auth_ids[i:i+50])
            author_res = requests.get(
                f"{self.base_url}/authors", 
                params={"filter": f"id:{batch}", "select": "id,display_name,summary_stats,topics,last_known_institutions"},
                headers=self.headers
            ).json()
            
            for author in author_res.get('results', []):
                a_id = author.get('id')
                last_insts = author.get('last_known_institutions') or []
                
                is_at_school = any(inst.get('id') == school_id for inst in last_insts)
                topics = author.get('topics') or []
                is_cs = any(t.get('field', {}).get('display_name') == "Computer Science" for t in topics[:3])
                
                if is_at_school and is_cs and a_id in potential_map:
                    verified_list.append(Faculty(
                        name=author.get('display_name'),
                        id=a_id,
                        h_index=(author.get('summary_stats') or {}).get('h_index', 0),
                        specialty=topics[0].get('display_name') if topics else "AI",
                        top_paper=potential_map[a_id],
                        last_known_institution=school_display
                    ))

        final_results = sorted(verified_list, key=lambda x: x.h_index, reverse=True)
        
        # 5. Commit to Cache
        self.storage.save_faculty(final_results)
        return final_results[:limit]
    
