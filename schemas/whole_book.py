from pydantic import BaseModel


class DriveBook(BaseModel):
    id: str
    name: str
    has_been_renamed: bool = False
    categories: list[str] = []
    is_available: bool = False


class PageContent(BaseModel):
    page: int
    text: str


class Book(BaseModel):
    pages: list[PageContent]


class ExcerptRequest(BaseModel):
    start: int
    end: int


class ExcerptResponse(BaseModel):
    job_id: str
    book_name: str
    status: str
    status_url: str
    download_url: str
    file_url: str
    email_sent: bool
    email_error: str | None = None