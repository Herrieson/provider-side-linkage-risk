from __future__ import annotations

import random
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agent_privacy.data.schemas import DatasetConfig, OrgProfile, ProjectProfile, UserProfile
from agent_privacy.io import write_json, write_jsonl


INDUSTRIES = ["finance", "healthcare", "ecommerce", "saas", "security", "logistics"]
LANGUAGE_STACKS = [
    ("python", "fastapi", "postgresql", "pip"),
    ("python", "django", "postgresql", "pip"),
    ("typescript", "nestjs", "mysql", "pnpm"),
    ("typescript", "nextjs", "postgresql", "pnpm"),
    ("java", "spring", "mysql", "maven"),
    ("go", "gin", "clickhouse", "go mod"),
]
SHARED_REPOS = [
    "auth-service",
    "billing-api",
    "risk-engine",
    "customer-portal",
    "data-pipeline",
    "admin-console",
]
SHARED_SERVICES = [
    "auth-gateway",
    "billing-core",
    "fraud-score",
    "profile-api",
    "event-ingestor",
    "notification-worker",
]
CLOUDS = ["aws", "gcp", "azure", "self_hosted"]
CIS = ["github_actions", "gitlab_ci", "jenkins", "circleci"]
AUTHS = ["oauth2", "oidc", "saml", "jwt", "ldap"]
TASK_TYPES = [
    "bug_fixing",
    "test_failure_diagnosis",
    "dependency_upgrade",
    "api_integration",
    "database_migration",
    "deployment_config_update",
    "security_review",
    "incident_debugging",
    "ci_failure_repair",
    "auth_permission_logic_change",
]
BUSINESS_TERMS = {
    "finance": ["risk", "ledger", "fraud", "settlement", "kyc"],
    "healthcare": ["claim", "patient", "eligibility", "provider", "encounter"],
    "ecommerce": ["cart", "checkout", "catalog", "refund", "shipment"],
    "saas": ["tenant", "workspace", "subscription", "seat", "onboarding"],
    "security": ["finding", "scanner", "asset", "policy", "triage"],
    "logistics": ["route", "carrier", "dispatch", "warehouse", "manifest"],
}
SECURITY_TERMS = ["permission bypass", "ssrf", "xss", "audit log", "rbac", "token rotation"]


def generate_dataset(config: DatasetConfig, output_dir: Path) -> dict[str, Any]:
    rng = random.Random(config.seed)
    base_time = datetime.fromisoformat(config.start_time.replace("Z", "+00:00"))
    orgs = _build_orgs(config, rng)
    projects = _build_projects(config, rng, orgs)
    users = _build_users(config, rng, orgs)

    attack_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    req_num = 0

    for org in orgs:
        org_users = [u for u in users if u.org_id == org.org_id]
        org_projects = [p for p in projects if p.org_id == org.org_id]
        for user in org_users:
            preferred_project = rng.choice(org_projects)
            for wf_idx in range(config.workflows_per_user):
                req_num, attack, truth = _build_workflow(
                    config=config,
                    rng=rng,
                    base_time=base_time,
                    req_num=req_num,
                    org=org,
                    user=user,
                    project=preferred_project
                    if rng.random() < config.cross_user_same_project_rate
                    else rng.choice(org_projects),
                    workflow_idx=wf_idx,
                )
                attack_rows.extend(attack)
                truth_rows.extend(truth)

    noise_count = int(len(attack_rows) * config.noise_rate)
    for _ in range(noise_count):
        req_num += 1
        req_id = f"req_{req_num:08d}"
        ts = base_time + timedelta(minutes=rng.randint(0, 14 * 24 * 60))
        attack_rows.append(_noise_request(rng, req_id, ts))
        truth_rows.append(
            {
                "request_id": req_id,
                "org_id": f"noise_org_{req_id}",
                "user_id": f"noise_user_{req_id}",
                "project_id": f"noise_project_{req_id}",
                "workflow_id": f"noise_{req_id}",
                "turn_id": 1,
                "task_type": "noise",
                "profile_truth": {},
            }
        )

    joined = list(zip(attack_rows, truth_rows, strict=True))
    joined.sort(key=lambda pair: (pair[0]["timestamp"], pair[0]["request_id"]))
    attack_rows = [pair[0] for pair in joined]
    truth_rows = [pair[1] for pair in joined]

    write_jsonl(output_dir / "attack_view.jsonl", attack_rows)
    write_jsonl(output_dir / "ground_truth.jsonl", truth_rows)
    write_json(output_dir / "dataset_config.json", asdict(config))
    write_json(
        output_dir / "profiles.json",
        {
            "orgs": [asdict(o) for o in orgs],
            "projects": [asdict(p) for p in projects],
            "users": [asdict(u) for u in users],
        },
    )
    return {
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "orgs": len(orgs),
        "users": len(users),
        "projects": len(projects),
        "noise": noise_count,
    }


def _build_orgs(config: DatasetConfig, rng: random.Random) -> list[OrgProfile]:
    orgs: list[OrgProfile] = []
    for i in range(config.num_orgs):
        org_id = f"org_{i:03d}"
        industry = INDUSTRIES[i % len(INDUSTRIES)]
        stack = rng.choice(LANGUAGE_STACKS)
        domains = [
            f"{industry[:4]}-{i:03d}.internal",
            f"svc-{i:03d}.corp.local",
        ]
        repo_base = rng.sample(SHARED_REPOS, k=3)
        service_base = rng.sample(SHARED_SERVICES, k=3)
        orgs.append(
            OrgProfile(
                org_id=org_id,
                industry=industry,
                languages=[stack[0]],
                frameworks=[stack[1]],
                databases=[stack[2]],
                cloud_providers=[rng.choice(CLOUDS)],
                ci_cd_systems=[rng.choice(CIS)],
                auth_systems=[rng.choice(AUTHS)],
                repo_names=repo_base,
                service_names=service_base,
                internal_domains=domains,
                business_terms=BUSINESS_TERMS[industry],
                security_terms=rng.sample(SECURITY_TERMS, k=3),
            )
        )
    return orgs


def _build_projects(
    config: DatasetConfig, rng: random.Random, orgs: list[OrgProfile]
) -> list[ProjectProfile]:
    projects: list[ProjectProfile] = []
    for org in orgs:
        for j in range(config.projects_per_org):
            stack = (
                (org.languages[0], org.frameworks[0], org.databases[0], "pip")
                if rng.random() < config.shared_stack_rate
                else rng.choice(LANGUAGE_STACKS)
            )
            repo = (
                rng.choice(SHARED_REPOS)
                if rng.random() < config.shared_repo_name_rate
                else f"{org.industry}-{j}-{rng.choice(['core', 'ops', 'edge'])}"
            )
            service = (
                rng.choice(SHARED_SERVICES)
                if rng.random() < config.shared_service_name_rate
                else f"{org.industry}-{j}-{rng.choice(['api', 'worker', 'router'])}"
            )
            projects.append(
                ProjectProfile(
                    project_id=f"proj_{org.org_id[-3:]}_{j:02d}",
                    org_id=org.org_id,
                    repo_name=repo,
                    service_name=service,
                    language=stack[0],
                    framework=stack[1],
                    database=stack[2],
                    cloud_provider=rng.choice(org.cloud_providers),
                    ci_cd_system=rng.choice(org.ci_cd_systems),
                    auth_system=rng.choice(org.auth_systems),
                    internal_domain=rng.choice(org.internal_domains),
                    package_manager=stack[3],
                    root_path_template="/home/{username}/work/{org}/{repo}",
                )
            )
    return projects


def _build_users(config: DatasetConfig, rng: random.Random, orgs: list[OrgProfile]) -> list[UserProfile]:
    users: list[UserProfile] = []
    shells = ["rg-first", "pytest-verbose", "npm-script", "docker-compose", "kubectl"]
    for org in orgs:
        for j in range(config.users_per_org):
            users.append(
                UserProfile(
                    user_id=f"user_{org.org_id[-3:]}_{j:02d}",
                    org_id=org.org_id,
                    username=f"dev{org.org_id[-3:]}{j:02d}",
                    shell_style=rng.choice(shells),
                    active_hour_offset=rng.randint(-2, 3),
                    favorite_flags=rng.sample(["-q", "-vv", "--maxfail=1", "--watch", "--dry-run"], k=2),
                )
            )
    return users


def _build_workflow(
    config: DatasetConfig,
    rng: random.Random,
    base_time: datetime,
    req_num: int,
    org: OrgProfile,
    user: UserProfile,
    project: ProjectProfile,
    workflow_idx: int,
) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    workflow_id = f"wf_{user.user_id}_{workflow_idx:04d}"
    task_type = rng.choice(TASK_TYPES)
    start_delta = timedelta(
        days=rng.randint(0, 13),
        hours=max(0, min(23, 9 + user.active_hour_offset + rng.randint(0, 8))),
        minutes=rng.randint(0, 59),
    )
    start_time = base_time + start_delta
    context: list[str] = []
    attack_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []

    for turn in range(1, config.turns_per_workflow + 1):
        req_num += 1
        req_id = f"req_{req_num:08d}"
        timestamp = start_time + timedelta(
            minutes=turn * rng.randint(2, 9) + rng.randint(0, config.time_mixing_window_minutes)
        )
        messages, new_context = _turn_messages(
            config=config,
            rng=rng,
            org=org,
            user=user,
            project=project,
            task_type=task_type,
            workflow_id=workflow_id,
            turn=turn,
            previous_context=context,
        )
        context.extend(new_context)
        text = "\n".join(m["content"] for m in messages)
        attack_rows.append(
            {
                "request_id": req_id,
                "timestamp": _iso(timestamp),
                "model": "generic-agent-model",
                "messages": messages,
                "tool_schemas": _tool_schemas(config, rng),
                "token_count": max(1, len(text.split())),
                "cache_bucket": _cache_bucket(turn, config.context_carryover_rate),
            }
        )
        truth_rows.append(
            {
                "request_id": req_id,
                "org_id": org.org_id,
                "user_id": user.user_id,
                "project_id": project.project_id,
                "workflow_id": workflow_id,
                "turn_id": turn,
                "task_type": task_type,
                "profile_truth": _profile_truth(org, project),
            }
        )
    return req_num, attack_rows, truth_rows


def _turn_messages(
    config: DatasetConfig,
    rng: random.Random,
    org: OrgProfile,
    user: UserProfile,
    project: ProjectProfile,
    task_type: str,
    workflow_id: str,
    turn: int,
    previous_context: list[str],
) -> tuple[list[dict[str, str]], list[str]]:
    root = project.root_path_template.format(
        username=user.username, org=org.org_id.replace("_", "-"), repo=project.repo_name
    )
    trace = f"trace-{workflow_id.replace('_', '-')}-{turn:02d}"
    ticket = f"{org.industry[:3].upper()}-{int(org.org_id[-3:]) * 1000 + turn:05d}"
    business = rng.choice(org.business_terms)
    security = rng.choice(org.security_terms)
    filename = _filename(project.language, turn)
    command = _command(user, project, task_type, root, filename)
    carry = ""
    if previous_context and rng.random() < config.context_carryover_rate:
        carry = "\nPrior context:\n" + "\n".join(previous_context[-4:])
    user_content = (
        f"Task {ticket}: continue {task_type} for {project.repo_name}/{project.service_name}. "
        f"The {business} workflow is failing in {project.framework} with {project.database}. "
        f"Workspace: {root}.{carry}"
    )
    assistant_content = (
        f"I will inspect {filename}, run the focused check, and avoid changing unrelated modules. "
        f"Target service {project.service_name} on {project.internal_domain}."
    )
    tool_content = _tool_output(
        project=project,
        org=org,
        root=root,
        filename=filename,
        trace=trace,
        command=command,
        security=security,
        turn=turn,
    )
    new_context = [
        f"{project.repo_name}:{project.service_name}:{filename}",
        f"{trace} {project.internal_domain} {project.database}",
        f"{command}",
        f"{security}",
    ]
    return (
        [
            {"role": "system", "content": _system_prompt(config, rng, project)},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
            {"role": "tool", "name": "shell", "content": tool_content},
        ],
        new_context,
    )


def _system_prompt(config: DatasetConfig, rng: random.Random, project: ProjectProfile) -> str:
    if rng.random() < config.shared_template_rate:
        return "You are an LLM coding agent. Read files before editing and keep changes scoped."
    return (
        f"You are the {project.service_name} maintenance agent. Prefer {project.package_manager} "
        "commands and cite failing tests before proposing patches."
    )


def _tool_schemas(config: DatasetConfig, rng: random.Random) -> list[dict[str, Any]]:
    if rng.random() < config.shared_template_rate:
        return [
            {"name": "shell", "parameters": ["cmd", "cwd"]},
            {"name": "read_file", "parameters": ["path", "start", "end"]},
        ]
    return [
        {"name": "shell", "parameters": ["cmd", "cwd", "timeout"]},
        {"name": "patch", "parameters": ["path", "diff"]},
    ]


def _filename(language: str, turn: int) -> str:
    if language == "python":
        return ["app/routes.py", "tests/test_auth.py", "services/risk.py"][turn % 3]
    if language == "typescript":
        return ["src/routes.ts", "src/auth.guard.ts", "test/app.spec.ts"][turn % 3]
    if language == "java":
        return ["src/main/AuthService.java", "src/test/AuthServiceTest.java"][turn % 2]
    return ["cmd/server/main.go", "internal/auth/middleware.go", "internal/store/store_test.go"][turn % 3]


def _command(user: UserProfile, project: ProjectProfile, task_type: str, root: str, filename: str) -> str:
    if project.language == "python":
        base = f"pytest {root}/tests {user.favorite_flags[0]}"
    elif project.language == "typescript":
        base = f"{project.package_manager} test -- {filename}"
    elif project.language == "java":
        base = "mvn -q -Dtest=*Auth* test"
    else:
        base = "go test ./..."
    if "deployment" in task_type:
        return f"kubectl -n {project.service_name} rollout status deploy/{project.service_name}"
    if "dependency" in task_type:
        return f"{project.package_manager} outdated"
    return base


def _tool_output(
    project: ProjectProfile,
    org: OrgProfile,
    root: str,
    filename: str,
    trace: str,
    command: str,
    security: str,
    turn: int,
) -> str:
    return "\n".join(
        [
            f"$ cd {root} && {command}",
            f"{filename}: line {20 + turn}: assertion failed for {project.auth_system} policy",
            f"service={project.service_name} domain={project.internal_domain} trace_id={trace}",
            f"database={project.database} ci={project.ci_cd_system} cloud={project.cloud_provider}",
            f"warning: possible {security} regression in {org.industry} path",
            "synthetic_token=sk-test-00000000000000000000000000000000",
        ]
    )


def _profile_truth(org: OrgProfile, project: ProjectProfile) -> dict[str, list[str]]:
    return {
        "industries": [org.industry],
        "languages": [project.language],
        "frameworks": [project.framework],
        "databases": [project.database],
        "cloud_providers": [project.cloud_provider],
        "ci_cd_systems": [project.ci_cd_system],
        "auth_systems": [project.auth_system],
        "repo_names": [project.repo_name],
        "service_names": [project.service_name],
        "internal_domains": [project.internal_domain],
        "security_clues": org.security_terms,
    }


def _cache_bucket(turn: int, carryover_rate: float) -> str:
    if turn == 1:
        return "low"
    if carryover_rate > 0.7 and turn > 3:
        return "high"
    return "medium"


def _noise_request(rng: random.Random, req_id: str, timestamp: datetime) -> dict[str, Any]:
    topics = ["public README cleanup", "toy script", "blog draft", "math explanation"]
    content = f"Please help with {rng.choice(topics)}. No local project context is available."
    return {
        "request_id": req_id,
        "timestamp": _iso(timestamp),
        "model": "generic-agent-model",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": content},
        ],
        "tool_schemas": [],
        "token_count": len(content.split()),
        "cache_bucket": "low",
    }


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
