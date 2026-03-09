from pydantic import BaseModel


class DriveBook(BaseModel):
    id: str
    name: str
    folder: str | None = None
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

class SaveExcerptRequest(BaseModel):
    book_id: str
    start_page: int
    end_page: int
    has_been_studied: bool = False
    resource_link: str | None = None
    how_many_times_reviewd: int = 0


class ExcerptRecord(BaseModel):
    id: int
    google_drive_file_id: str
    start_page: int
    end_page: int
    has_been_studied: bool
    how_many_times_reviewd: int = 0
    resource_link: str | None = None
    summary: str | None = None
    created_at: str
    updated_at: str

