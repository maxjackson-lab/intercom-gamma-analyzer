from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.services.admin_profile_cache import AdminProfileCache
from src.services.intercom_service_v2 import IntercomServiceV2
from src.services.duckdb_storage import DuckDBStorage
import httpx
import logging
from typing import Optional


class AdminProfileLookupTool(BaseTool):
    """Tool for looking up admin/agent profiles from Intercom API with vendor detection.
    
    Return Payload Fields:
        - admin_id (str): CANONICAL identifier for the admin. Use this field.
        - id (str): DEPRECATED. Included only for backward compatibility. Same value as admin_id.
        - name (str): Admin's display name
        - email (str): Admin's work email address
        - vendor (str): Vendor affiliation (horatio, boldr, gamma, or None)
        - public_email (str): Publicly visible email if available
        - active (bool): Whether the admin is currently active
    
    Deprecation Notice:
        The 'id' field is deprecated and will be removed in a future release (tentatively Q2 2026).
        All consumers should migrate to using 'admin_id' instead. The 'id' field is maintained
        solely for backward compatibility with existing code during the transition period.
        Update your code to reference 'admin_id' to ensure compatibility with future versions.
    """

    def __init__(self):
        super().__init__(
            name="lookup_admin_profile",
            description="Look up admin/agent profile from Intercom API including email and vendor affiliation (horatio, boldr, gamma). Uses cached data when available. Returns 'admin_id' as canonical identifier; 'id' field is deprecated but included for backward compatibility."
        )
        self.intercom_service = IntercomServiceV2()
        
        # Initialize storage with graceful fallback
        try:
            self.storage = DuckDBStorage()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize DuckDB storage: {e}. Tool will operate without persistence.")
            self.storage = None
            
        self.cache = AdminProfileCache(self.intercom_service, self.storage)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="admin_id",
                    type="string",
                    description="Intercom admin ID to look up (e.g., '7890123')",
                    required=True
                ),
                ToolParameter(
                    name="public_email",
                    type="string",
                    description="Optional email from conversation_parts for fallback vendor detection if API returns no work email",
                    required=False
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        admin_id = str(kwargs.get('admin_id', '')).strip()
        public_email = kwargs.get('public_email')
        
        if not admin_id:
            return ToolResult(success=False, data=None, error_message="admin_id is required")

        try:
            async with httpx.AsyncClient(timeout=self.intercom_service.timeout) as client:
                profile = await self.cache.get_admin_profile(admin_id, client, public_email)

            result_dict = {
                "admin_id": profile.id,  # CANONICAL: Use this field for all new code
                "id": profile.id,  # DEPRECATED: Backward compatibility only, will be removed in future
                "name": profile.name,
                "email": profile.email,
                "vendor": profile.vendor,
                "public_email": profile.public_email,
                "active": profile.active
            }

            return ToolResult(success=True, data=result_dict)

        except Exception as e:
            self.logger.error(f"Failed to lookup admin {admin_id}: {e}")
            return ToolResult(success=False, data=None, error_message=f"Failed to lookup admin {admin_id}: {str(e)}")