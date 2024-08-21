from typing import Optional
from sqlmodel import Field
from app.database.base.model import BaseModel, CreatedAtOnlyTimeStampMixin


class TenantModel(BaseModel, CreatedAtOnlyTimeStampMixin, table=True):
    """
    Represents a tenant in the database.

    Attributes:

        uuid (UUID): The unique identifier for the tenant.

        name (Optional[str]): The name of the tenant.

        email (Optional[str]): The email address of the tenant.

        phone (Optional[str]): The phone number of the tenant.

        org_info (Optional[str]): Organization information related to the tenant.

        logo (Optional[str]): URL or reference to the organization's logo.

        support_email (Optional[str]): Support email address.

        website (Optional[str]): Website URL of the tenant or their organization.

        ai_search_index_name (Optional[str]): AI search index name for the tenant.

        ai_search_service_name (Optional[str]): AI search service name for the tenant.

        created_at (datetime): Timestamp of when the tenant was created.

    """

    __tablename__: str = "core_tenant"  # Setting the table name

    name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    org_info: Optional[str] = Field(default=None)
    logo: Optional[str] = Field(default=None)
    support_email: Optional[str] = Field(default=None)
    website: Optional[str] = Field(default=None)
    ai_search_index_name: Optional[str] = Field(default=None)
    ai_search_service_name: Optional[str] = Field(default=None)
