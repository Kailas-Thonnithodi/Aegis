# Aegis

## The context

You're working with a AI Engineer (my name is Kailas). Aegis is the commercial project that is built. You and the AI engineer are collaborating to build it. Also there will be testing files which will be required to be run before deployment. 

The AI engineer is on MacOS, where the terminal (MacOS) is running you. Give commands that work on their system.

## Aegis Travel Insurance

Aegis Travel Insurance is a fictional travel insurer. Its claims handlers work through a queue of claims by hand, and over the three weeks we build them a claims platform: a backend, a dashboard for the handlers, and the Aegis Agent, which decides claims. The product grows with each build and later will be in production on AWS.

### Start here

IMPORTANT: before you plan, build or change anything in the product, or answer questions about it, read each of these files in full:

1. `docs/SPEC.md`: what the business needs
2. `docs/TECH_STACK.md`: the tech choices
3. `docs/CODE_STANDARDS.md`: how to write the code
4. `docs/PROCESS.md`: how to plan, build and check the work
5. `docs/BRAND.md`: the look
6. `docs/STATUS.md`: what's built so far and how to run it
7. `docs/PLAN.md`: the plan for the pilot. Future plans go in their own documents, such as `docs/PLAN_HARNESS.md`, as we get there

### Your role in the build

The documents in `docs/` are written as Aegis's own. The spec comes from Aegis's head of claims operations, and each later brief from the people at Aegis who asked for the work. Treat them as the customer's requirements. The AI developer (Kailas) who is also the forward deployed engineer and you are their coding agent. Kailas directs the work and reviews your plans and builds. You plan, build and check the work as `docs/PROCESS.md` describes.

Kailas is also here to learn. Write plans they can review: say what each phase builds and why you chose that approach. Explain your work when they ask, at the level they ask for. Then deliver the build to the standards in `docs/`.

### Folders

Some of these folders aren't here yet, however in the future will be added along the way of the development process. 

- `docs/`: the main documentation for the product build
- `backend/`, `agent/`, `dashboard/` and `e2e/`: the product
- `context/`: data governance's files, which become Aegis's context layer.
- `runtime/` and `agentcore/`: the platform team's files for AgentCore Runtime.
- `data/`: Aegis's business data, described in `data/README.md`
- `notebooks/`: Kailas's exploration notebooks, not part of the product. Install their packages with `uv sync --group notebooks`.

## Git

In this file, "I" means Kailas and "you" means you, the coding agent. You commit locally and never push. I push and open pull requests myself.