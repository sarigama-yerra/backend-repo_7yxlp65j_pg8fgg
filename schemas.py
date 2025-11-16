"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogpost" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# --- Portfolio App Schemas ---

class Skill(BaseModel):
    """
    Skills collection schema
    Collection name: "skill"
    """
    title: str = Field(..., description="Skill title e.g., React, FastAPI")
    slug: str = Field(..., description="URL-friendly slug")
    icon: Optional[str] = Field(None, description="Icon name or image URL")
    summary: Optional[str] = Field(None, description="1-2 line description")
    link: Optional[str] = Field(None, description="Link to blog post or docs")
    tags: List[str] = Field(default_factory=list, description="Tags for filtering")
    order: int = Field(0, description="Order for sorting in UI")

class Experience(BaseModel):
    """
    Experiences collection schema
    Collection name: "experience"
    """
    company: str
    role: str
    startDate: date
    endDate: Optional[date] = None
    summary: Optional[str] = None
    image: Optional[str] = None
    order: int = 0

class BlogPost(BaseModel):
    """
    Blog posts collection schema
    Collection name: "blogpost"
    """
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str = Field("", description="Markdown content")
    coverImage: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    published: bool = True

# Example schemas left for reference (not used by app but helpful in DB viewer)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
