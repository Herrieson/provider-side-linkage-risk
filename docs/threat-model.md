# Threat Model

## Entities

- User or enterprise `A`: operates LLM Agents for development, operations, data, security, or office workflows.
- Broker `B`: authenticates users, bills usage, routes requests, and maps responses back to users.
- Model provider `C`: performs inference and sees plaintext prompts, responses, tool outputs, and common inference metadata.
- Attacker: `C` itself or an attacker with offline access to `C` inference logs.

## Deployment

The core deployment is an anonymous broker setup:

1. `A` sends an authorized request through `B`.
2. `B` hides explicit user, organization, network, and billing identifiers from `C`.
3. `C` receives mixed traffic from many users and organizations.
4. `C` still sees plaintext Agent context because it must run inference.

The broker is not the object of study. The question is whether hiding explicit identity is enough when content remains visible to the provider.

## Provider Capabilities

The primary provider is passive:

- keeps request logs;
- reads plaintext prompts, responses, and tool result text;
- observes timestamps and token counts;
- performs offline analysis;
- does not alter responses;
- does not ask the Agent to inspect extra files;
- does not use API keys, IP addresses, billing ids, or account ids.

## Non-Goals

This project does not study:

- model training leakage;
- model memorization of prompts;
- network traffic analysis;
- active compromise of user devices;
- malicious broker behavior;
- explicit identity linkage through API keys or billing records.

## Sensitive Data Policy

Experiments should not use real company data, real secrets, private logs, or private repositories. Synthetic secrets may be generated only to test filtering and must be marked as synthetic.

