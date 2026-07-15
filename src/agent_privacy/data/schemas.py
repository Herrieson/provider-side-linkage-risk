from __future__ import annotations

from dataclasses import dataclass, field


Profile = dict[str, list[str]]


@dataclass(frozen=True)
class DatasetConfig:
    seed: int = 7
    num_orgs: int = 20
    users_per_org: int = 5
    projects_per_org: int = 3
    workflows_per_user: int = 20
    turns_per_workflow: int = 8
    noise_rate: float = 0.15
    shared_template_rate: float = 0.75
    shared_repo_name_rate: float = 0.30
    shared_service_name_rate: float = 0.30
    shared_stack_rate: float = 0.60
    cross_user_same_project_rate: float = 0.45
    context_carryover_rate: float = 0.85
    time_mixing_window_minutes: int = 60
    start_time: str = "2026-01-05T09:00:00Z"


@dataclass
class OrgProfile:
    org_id: str
    industry: str
    languages: list[str]
    frameworks: list[str]
    databases: list[str]
    cloud_providers: list[str]
    ci_cd_systems: list[str]
    auth_systems: list[str]
    repo_names: list[str]
    service_names: list[str]
    internal_domains: list[str]
    business_terms: list[str]
    security_terms: list[str]


@dataclass
class ProjectProfile:
    project_id: str
    org_id: str
    repo_name: str
    service_name: str
    language: str
    framework: str
    database: str
    cloud_provider: str
    ci_cd_system: str
    auth_system: str
    internal_domain: str
    package_manager: str
    root_path_template: str


@dataclass
class UserProfile:
    user_id: str
    org_id: str
    username: str
    shell_style: str
    active_hour_offset: int
    favorite_flags: list[str] = field(default_factory=list)

