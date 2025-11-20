"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class VideoJob(BaseModel):
    """
    Video generation jobs schema
    Collection name: "videojob"
    """
    provider: Literal[
        "gemini",
        "wan2_1",
        "grok",
        "hailuo",
        "sora2",
    ] = Field(..., description="Which AI provider to use")
    # Generation mode
    mode: Literal[
        "text_to_video",
        "image_sequence_to_video",
        "multi_image_guided",
    ] = Field("text_to_video", description="Type of generation workflow")

    prompt: str = Field(..., min_length=3, max_length=2000, description="Text prompt to generate video")
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3"] = Field("16:9", description="Aspect ratio")
    duration: int = Field(5, ge=1, le=60, description="Duration in seconds")

    # Multi-frame / multi-image support
    image_urls: Optional[List[str]] = Field(None, description="Ordered list of image URLs for image-sequence or guidance")
    fps: Optional[int] = Field(24, ge=1, le=60, description="Frames per second for video output")

    status: Literal["queued", "processing", "completed", "failed"] = Field("queued", description="Job status")
    result_url: Optional[str] = Field(None, description="URL to the generated video")
    error: Optional[str] = Field(None, description="Error message if failed")

# Example schemas (kept for reference)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    in_stock: bool = True
