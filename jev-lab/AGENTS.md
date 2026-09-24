# jev-lab agent instructions

Status: **canonical project instructions**. Read this file before working in `jev-lab/`.

## Mission and current state

`jev-lab` is an independent trading-automation research track. Its goal is to find out whether Jev, used within a rule-based trading system that a person can operate from home, improves **repeatable net performance after all costs** enough to justify paper and eventually live trading. Jev is a candidate decision component, not an assumed source of trading edge.

As of 2026-09-24 this lab is a scaffold only. No market, venue, data source, strategy, Jev prompt, model version, baseline, capital amount, or execution mode has been selected. No experiment has run and no result or profitability claim exists. Do not borrow XAUUSD parameters or results from `xau-lab` as if they apply here.

## Recovery sequence

At the start of a new task:

1. Read `AGENTS.md`, `STRUCTURE.md`, and `README.md`.
2. Check Git status and preserve unrelated work.
3. Read the relevant indexes under `docs/`, then the latest applicable algorithm and experiment records.
4. Read the matching data manifest, frozen config, and result bundle before citing a result or changing a strategy.
5. Prefer committed evidence over chat memory. Record any correction to a prior conclusion instead of silently replacing it.

## Research principles

- Choose a specific market, venue, data feed, trading cadence, and account constraints before designing a trade policy. Validate that the setup is practical on a home connection and supported by the venue's terms and APIs.
- Begin with a deterministic, no-Jev baseline and a no-trade baseline. Add Jev only where it can make a narrow, testable decision; give the policy an explicit `SKIP`/no-trade outcome.
- Keep arithmetic, feature generation, sizing, position limits, stops, accounting, and order validation in code. Treat model probabilities as unvalidated for the chosen market until measured on that market.
- Pin the exact model version and freeze the state schema, question wording, options, thresholds, and policy before each evaluation period. Cache request/response pairs with timestamps and hashes so a replay does not change when the remote model changes.
- Use only information available at each decision time. Preserve chronological splits; tune on development data, evaluate once on later data, and keep a declared final holdout sealed until an explicit milestone. Do not use future prices, eventual fills, hindsight labels, or revised market data as live inputs.
- Compare every candidate with the same data, clock, fill model, capital, and risk constraints as its baselines. Include spread, fees, slippage, funding/borrow costs where relevant, rejected orders, latency, API cost, and adverse execution scenarios.
- Report net P&L, drawdown, expectancy, turnover, trade and fill counts, exposure time, regime/period breakdowns, model coverage, and failure modes. Separate simulated, paper, and actual live fills. A short positive run is not evidence of stable income.
- Keep failed experiments and negative findings. Do not repeatedly tune against evaluation segments to rescue a candidate.

## Execution boundary

The default is **offline research and paper trading**. A request to build a bot, run a simulation, or test an API does not imply permission to place real orders. Live trading requires an explicit user-directed milestone and a separately documented execution design with venue contract checks, minimum-size feasibility, position and loss caps, spread/slippage bounds, duplicate-order protection, reconnect behavior, kill switch, audit trail, and paper/live separation. Never put API keys, private keys, seed phrases, or account identifiers in Git or tool output.

Network errors, malformed model responses, stale data, or missed deadlines must produce a recorded no-decision. Emergency exits and account protection must not wait for a remote model call. Do not enable high leverage or a rapid-fire maker loop simply because an online Jev demonstration does so.

## Experiment workflow

For each material experiment:

1. Write a dated experiment record in `docs/experiments/` with hypothesis, market/venue, baseline, allowed changes, data IDs and hashes, split, costs, risk limits, metrics, and success/failure criteria **before** inspecting evaluation outcomes.
2. Implement reusable logic in `src/jev_lab/`, runnable entry points in `scripts/`, frozen settings in `configs/`, and focused checks in `tests/` where they verify consequential behavior.
3. Write a durable result bundle under the corresponding `results/` mode using the same experiment ID. Include machine-readable config/summary and a short `README.md` explaining provenance, limitations, and the decision.
4. Update `docs/experiments/README.md`, the relevant algorithm document, and `README.md` when status materially changes. Update `STRUCTURE.md` if paths or naming rules change.
5. State whether the candidate was rejected, remains provisional, or was locked. A locked configuration is immutable; new ideas get a new version or candidate ID.

## Git workflow and atomic pushes

After each coherent update to local code, configuration, documentation, or durable results, verify the affected files, create one focused commit, and push that commit to the current remote branch before starting the next independent update. Keep a script, its necessary documentation, and its matching result evidence together when they form one reproducible change. Do not accumulate unrelated changes in one commit or postpone several completed updates for a single push.

Stage only files belonging to the update; inspect `git status` and the staged diff before committing. Leave unrelated or user-owned changes untouched. Run the relevant checks and `git diff --check` before the commit. Never commit secrets, raw private data, or generated noise. Do not force-push or rewrite shared history. If a push fails, report the unpushed commit and the blocking reason; do not describe it as published.

Research work can proceed on the current checkout, normally `main`. Do not create a branch, PR, or GitHub Actions workflow unless the user requests one or the work genuinely requires isolation.

## Canonical source hierarchy

Use `AGENTS.md` for project behavior, `STRUCTURE.md` for placement/naming, data manifests for source facts, frozen configs and algorithm records for policy, experiment records for protocol, then machine-readable results for measured outcomes. If these disagree, investigate and document the correction. Never rewrite a historical result to make a later story cleaner.
