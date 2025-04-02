from typing import List, Optional

from pydantic import (BaseModel, Field, StrictInt, ValidationInfo,
                      field_validator)


class AWXConfigModel(BaseModel):
    endpoint: str
    username: str = Field(default="admin")
    password: str


class GitConfigModel(BaseModel):
    it_automation_bench_local_path: str
    deploy_key_it_automation_bench_private_ssh_key_path: str
    deploy_key_agent_private_ssh_key_path: str
    deploy_key_agent_analytics_sdk_private_ssh_key_path: Optional[str] = None
    deploy_key_agent_analytics_sdk_ssh_key_passphrase: Optional[str] = None


class LLMConfigModel(BaseModel):
    provider: str
    model: str
    url: str
    api_key: str # pragma: allowlist secret
    api_version: str
    seed: int
    top_p: float
    temperature: float
    reasoning_effort: str
    thinking: str
    thinking_budget: int
    max_tokens: int


class LLMConfigModelAgent(LLMConfigModel):
    god_mode: bool = Field(default=True)
    model_embedding: str = Field(default="")
    url_embedding: str = Field(default="")
    api_version_embedding: str = Field(default="")


class WatsonXConfig(BaseModel):
    wx_project_id: str


class AgentAnalyticsSDKModel(BaseModel):
    git_token: str
    git_username: str


class AgentConfigModel(BaseModel):
    agents_config: LLMConfigModelAgent
    tools_config: LLMConfigModel
    watsonx_config: WatsonXConfig
    agent_analytics_sdk: AgentAnalyticsSDKModel


class AWSConfigModel(BaseModel):
    access_key_id: str
    secret_access_key: str


class KOpsConfigModel(BaseModel):
    s3_bucket_name: str


class ExperimentModel(BaseModel):
    awx_kubeconfig: str
    awx_chart_version: Optional[str] = None
    aws: AWSConfigModel
    git: GitConfigModel
    kops: KOpsConfigModel
    scenarios: List[int]
    number_of_runs: int = Field(default=20)
    data_modalities: List[str] = Field(default=["metrics", "logs", "traces"])
    agent_configuration: AgentConfigModel
    controller_host: Optional[str] = None
    controller_username: Optional[str] = None
    controller_password: Optional[str] = None
    s3_endpoint_url: str
    s3_bucket_name_for_results: str
