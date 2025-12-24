from dataclasses import dataclass


@dataclass
class Faculty:
    name: str
    id: str
    h_index: int
    specialty: str
    top_paper: str
    last_known_institution: str
    
    def __repr__(self):
        return f"<Faculty: {self.name} | h-index: {self.h_index} | Focus: {self.specialty}>"
