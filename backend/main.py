from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import numpy as np

app = FastAPI(title="Helpdesk Ticket System", version="1.0.0")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (change in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize models
skill_model = SentenceTransformer('all-MiniLM-L6-v2')
priority_classifier = pipeline("zero-shot-classification", 
                              model="facebook/bart-large-mnli")

# Data models
class Employer(BaseModel):
    id: str
    name: str
    skills: List[str]

class TicketCreate(BaseModel):
    user_id: str
    title: str
    description: str

class TicketResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    status: str
    priority: Optional[str] = None
    priority_score: Optional[float] = None
    rationale: Optional[str] = None
    assignee: Optional[str] = None
    assignee_reason: Optional[str] = None
    first_reply: Optional[str] = None
    created_at: str
    updated_at: str

class TriageResult(BaseModel):
    priority: str
    priority_score: float
    rationale: str
    assignee: str
    assignee_reason: str
    first_reply: str

# Employers data
employers = [
    {"id": "emp1", "name": "Alice", "skills": ["Python", "Machine Learning", "Flask"]},
    {"id": "emp2", "name": "Bob", "skills": ["Java", "Spring Boot", "Microservices"]},
    {"id": "emp3", "name": "Charlie", "skills": ["JavaScript", "React", "Node.js"]},
    {"id": "emp4", "name": "Diana", "skills": ["SQL", "PostgreSQL", "Data Modeling"]},
    {"id": "emp5", "name": "Ethan", "skills": ["AWS", "Docker", "Kubernetes"]},
    {"id": "emp6", "name": "Fiona", "skills": ["TensorFlow", "Deep Learning", "NLP"]},
    {"id": "emp7", "name": "George", "skills": ["C++", "Linux", "Embedded Systems"]},
    {"id": "emp8", "name": "Hannah", "skills": ["Cybersecurity", "Networking", "Firewalls"]},
    {"id": "emp9", "name": "Ian", "skills": ["Data Engineering", "Airflow", "ETL"]},
    {"id": "emp10", "name": "Jane", "skills": ["UI/UX", "Figma", "Frontend Design"]},
]

# In-memory storage for tickets
tickets_db = []

# Precompute employer skill embeddings
employer_skill_embeddings = {}
all_skills = set()

for employer in employers:
    employer_skills = employer["skills"]
    all_skills.update(employer_skills)
    skill_text = ", ".join(employer_skills)
    employer_skill_embeddings[employer["id"]] = {
        "skills": employer_skills,
        "embedding": skill_model.encode(skill_text, convert_to_tensor=True)
    }

# Helper functions
def get_current_time():
    return datetime.now().isoformat()

def find_best_employer_embeddings(ticket_text):
    ticket_embedding = skill_model.encode(ticket_text, convert_to_tensor=True)
    
    best_match_id = None
    best_score = -1
    best_skills = []
    
    for emp_id, emp_data in employer_skill_embeddings.items():
        similarity = util.pytorch_cos_sim(ticket_embedding, emp_data["embedding"]).item()
        
        if similarity > best_score:
            best_score = similarity
            best_match_id = emp_id
            best_skills = emp_data["skills"]
    
    for employer in employers:
        if employer["id"] == best_match_id:
            return employer, best_score, best_skills
    
    return None, 0, []

def determine_priority_zero_shot(title, description):
    text = f"{title}: {description}"
    
    candidate_labels = ["urgent critical", "high priority", "medium priority", "low priority"]
    
    result = priority_classifier(text, candidate_labels)
    
    highest_idx = np.argmax(result['scores'])
    priority_label = result['labels'][highest_idx]
    priority_score = result['scores'][highest_idx] * 100
    
    priority_map = {
        "urgent critical": "P0",
        "high priority": "P1", 
        "medium priority": "P2",
        "low priority": "P3"
    }
    
    return priority_map.get(priority_label, "P3"), priority_score

def generate_first_reply(ticket, priority, priority_score, assignee, matched_skills):
    greetings = "Thank you for reporting this issue."
    
    urgency_map = {
        "P0": f"We've identified this as a critical issue (priority score: {priority_score:.1f}/100) and are addressing it immediately.",
        "P1": f"We've identified this as a high-priority issue (priority score: {priority_score:.1f}/100) and will address it promptly.",
        "P2": f"We've identified this as a medium-priority issue (priority score: {priority_score:.1f}/100) and will address it soon.",
        "P3": f"We've identified this as a low-priority issue (priority score: {priority_score:.1f}/100) and will address it in due course."
    }
    
    skill_match = f"Our specialist {assignee} has been assigned because of their expertise in {', '.join(matched_skills[:3])}."
    
    closing = "We'll provide updates as we investigate further. Please feel free to add any additional details that might help us resolve this faster."
    
    return f"{greetings} {urgency_map[priority]} {skill_match} {closing}"

# API endpoints
@app.get("/")
async def root():
    return {"message": "Helpdesk Ticket System API with AI-powered triage"}

@app.get("/employers", response_model=List[Employer])
async def get_employers():
    return employers

@app.get("/tickets", response_model=List[TicketResponse])
async def get_tickets():
    return tickets_db

@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str):
    for ticket in tickets_db:
        if ticket["id"] == ticket_id:
            return ticket
    raise HTTPException(status_code=404, detail="Ticket not found")

@app.post("/tickets", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate):
    new_ticket = {
        "id": str(uuid.uuid4()),
        "user_id": ticket.user_id,
        "title": ticket.title,
        "description": ticket.description,
        "status": "open",
        "priority": None,
        "priority_score": None,
        "rationale": None,
        "assignee": None,
        "assignee_reason": None,
        "first_reply": None,
        "created_at": get_current_time(),
        "updated_at": get_current_time()
    }
    
    tickets_db.append(new_ticket)
    return new_ticket

@app.post("/tickets/{ticket_id}/triage", response_model=TriageResult)
async def triage_ticket(ticket_id: str):
    ticket = None
    for t in tickets_db:
        if t["id"] == ticket_id:
            ticket = t
            break
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    title = ticket["title"]
    description = ticket["description"]
    ticket_text = f"{title}: {description}"
    
    priority, priority_score = determine_priority_zero_shot(title, description)
    best_employer, similarity_score, matched_skills = find_best_employer_embeddings(ticket_text)
    
    if not best_employer:
        raise HTTPException(status_code=500, detail="No suitable employer found")
    
    first_reply = generate_first_reply(ticket, priority, priority_score, best_employer["name"], matched_skills)
    
    triage_result = {
        "priority": priority,
        "priority_score": priority_score,
        "rationale": f"Priority classification confidence: {priority_score:.1f}/100. Ticket content suggests skills needed: {', '.join(matched_skills) if matched_skills else 'General technical support'}",
        "assignee": best_employer["id"],
        "assignee_reason": f"Best skills match (similarity score: {similarity_score:.2f}): {best_employer['name']} has expertise in {', '.join(matched_skills)}",
        "first_reply": first_reply
    }
    
    ticket["priority"] = priority
    ticket["priority_score"] = priority_score
    ticket["rationale"] = triage_result["rationale"]
    ticket["assignee"] = best_employer["id"]
    ticket["assignee_reason"] = triage_result["assignee_reason"]
    ticket["first_reply"] = first_reply
    ticket["updated_at"] = get_current_time()
    
    return triage_result

@app.post("/tickets-with-triage", response_model=dict)
async def create_and_triage_ticket(ticket: TicketCreate):
    """Create a ticket and immediately perform triage on it"""
    # Create the ticket
    new_ticket = {
        "id": str(uuid.uuid4()),
        "user_id": ticket.user_id,
        "title": ticket.title,
        "description": ticket.description,
        "status": "open",
        "priority": None,
        "priority_score": None,
        "rationale": None,
        "assignee": None,
        "assignee_reason": None,
        "first_reply": None,
        "created_at": get_current_time(),
        "updated_at": get_current_time()
    }
    
    tickets_db.append(new_ticket)
    
    # Perform triage
    title = ticket.title
    description = ticket.description
    ticket_text = f"{title}: {description}"
    
    priority, priority_score = determine_priority_zero_shot(title, description)
    best_employer, similarity_score, matched_skills = find_best_employer_embeddings(ticket_text)
    
    if not best_employer:
        raise HTTPException(status_code=500, detail="No suitable employer found")
    
    first_reply = generate_first_reply(new_ticket, priority, priority_score, best_employer["name"], matched_skills)
    
    # Update the ticket with triage results
    new_ticket["priority"] = priority
    new_ticket["priority_score"] = priority_score
    new_ticket["rationale"] = f"Priority classification confidence: {priority_score:.1f}/100. Ticket content suggests skills needed: {', '.join(matched_skills) if matched_skills else 'General technical support'}"
    new_ticket["assignee"] = best_employer["id"]
    new_ticket["assignee_reason"] = f"Best skills match (similarity score: {similarity_score:.2f}): {best_employer['name']} has expertise in {', '.join(matched_skills)}"
    new_ticket["first_reply"] = first_reply
    new_ticket["updated_at"] = get_current_time()
    
    return {
        "ticket": new_ticket,
        "triage_result": {
            "priority": priority,
            "priority_score": priority_score,
            "rationale": new_ticket["rationale"],
            "assignee": best_employer["id"],
            "assignee_reason": new_ticket["assignee_reason"],
            "first_reply": first_reply
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)