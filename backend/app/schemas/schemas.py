from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

class EmailIn(BaseModel):
    message_id: str
    thread_id: str
    subject: str
    body: str
    sender: str
    recipients: List[str]
    date: datetime.datetime
    labels: List[str]

class EmailOut(EmailIn):
    id: str
    summary: Optional[str] = None
    category: Optional[str] = None
