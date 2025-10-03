from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    env: str = Field(default="development", alias="ENV")
    port: int = Field(default=4000, alias="PORT")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Anthropic
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", alias="ANTHROPIC_MODEL")

    # WEG proxy (optional)
    weg_base_url: str = Field(default="https://ai-server.enuygun.tech", alias="WEG_BASE_URL")
    weg_api_key: str = Field(default="", alias="WEG_API_KEY")

    # MCP / Enuygun endpoints
    mcp_base_url: str = Field(default="https://mcp.enuygun.com", alias="MCP_BASE_URL")
    mcp_api_key: str = Field(default="", alias="MCP_API_KEY")
    mcp_flights_path: str = Field(default="/flights/search", alias="MCP_FLIGHTS_PATH")
    mcp_hotels_path: str = Field(default="/hotels/search", alias="MCP_HOTELS_PATH")
    mcp_activities_path: str = Field(default="/activities/search", alias="MCP_ACTIVITIES_PATH")
    mcp_transport_intercity_path: str = Field(default="/transport/intercity", alias="MCP_TRANSPORT_INTERCITY_PATH")
    mcp_transport_localpasses_path: str = Field(default="/transport/localpasses", alias="MCP_TRANSPORT_LOCALPASSES_PATH")
    mcp_weather_path: str = Field(default="/weather/forecast", alias="MCP_WEATHER_PATH")
    mcp_geo_path: str = Field(default="/geo/resolveCity", alias="MCP_GEO_PATH")

    # Database (Supabase placeholders)
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    class Config:
        env_file = ".env"
        extra = "ignore"

    def cors_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
