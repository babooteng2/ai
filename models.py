from pydantic import BaseModel


class USerAccountContext(BaseModel):

    customer_id: int
    name: str
    tier: str = "basic"  # premium enterpirse
