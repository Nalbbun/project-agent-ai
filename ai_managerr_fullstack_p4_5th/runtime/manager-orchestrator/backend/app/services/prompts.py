from __future__ import annotations

import json
from typing import Any

PROMPT_SPECS = {
    "manager": {
        "instruction": "당신은 Manager / Orchestrator 이다. 실행 순서 정의, 부족 정보 식별, 결과 병합을 담당한다.",
        "required_keys": ["execution_plan", "missing_info_questions", "merge_strategy", "final_summary"],
        "forbidden": ["markdown", "설명만 있는 응답"],
    },
    "pm": {
        "instruction": "당신은 PM 에이전트다. 사용자 요구를 기능/비기능/질문/수용기준으로 구조화한다.",
        "required_keys": ["summary", "functional_requirements", "non_functional_requirements", "questions", "acceptance_criteria"],
        "forbidden": ["markdown", "자유서술만 있는 응답"],
    },
    "architect": {
        "instruction": "당신은 Architect 에이전트다. 요구사항을 시스템 구성, API, DB, 시퀀스, ADR로 구조화한다.",
        "required_keys": ["architecture_style", "components", "apis", "database", "sequence", "adrs"],
        "forbidden": ["markdown", "JSON 외 설명"],
    },
    "dev_fe": {
        "instruction": "당신은 Frontend Developer 에이전트다. 설계 결과를 기반으로 화면/컴포넌트/API 연동 결과를 구조화한다.",
        "required_keys": ["deliverables", "files"],
        "forbidden": ["markdown"],
    },
    "dev_be": {
        "instruction": "당신은 Backend Developer 에이전트다. 설계 결과를 기반으로 API/서비스/도메인 구현 계획을 구조화한다.",
        "required_keys": ["deliverables", "files"],
        "forbidden": ["markdown"],
    },
    "dev_db": {
        "instruction": "당신은 Database Developer 에이전트다. 설계 결과를 기반으로 DDL, 인덱스, migration 계획을 JSON으로 제시한다.",
        "required_keys": ["ddl", "indexes", "migration"],
        "forbidden": ["markdown"],
    },
    "qa": {
        "instruction": "당신은 QA 에이전트다. 현재 산출물에 대한 test_cases, gaps, verdict를 JSON으로 반환한다.",
        "required_keys": ["verdict", "test_cases"],
        "forbidden": ["markdown"],
    },
    "secops": {
        "instruction": "당신은 SecOps 에이전트다. 구성/코드/배포를 검토하고 findings, hardening_actions, verdict를 JSON으로 반환한다.",
        "required_keys": ["verdict", "findings", "hardening_actions"],
        "forbidden": ["markdown"],
    },
}


def build_prompt(role: str, user_request: str, context: dict[str, Any], rag_context: list[dict[str, Any]] | None = None) -> str:
    spec = PROMPT_SPECS.get(
        role,
        {
            "instruction": "항상 JSON으로 응답하라.",
            "required_keys": [],
            "forbidden": ["markdown"],
        },
    )
    payload = {
        "user_request": user_request,
        "context": context,
        "rag_context": rag_context or [],
    }
    contract = {
        "required_keys": spec["required_keys"],
        "forbidden": spec["forbidden"],
    }
    return (
        f"{spec['instruction']}\n"
        "반드시 단일 JSON object 로만 응답하라.\n"
        f"출력 계약:\n{json.dumps(contract, ensure_ascii=False, indent=2)}\n\n"
        f"입력:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
