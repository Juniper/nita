## Context

`nita-cmd` maps sub-commands to executable scripts, and existing Kubernetes
helpers in `cli_scripts/` follow a common pattern:
- detect required binaries using `command -v`
- set command text in `CMD`
- print debug command when `_CLI_RUNNER_DEBUG` is set
- execute via `eval "${CMD}"`

The requested feature adds `nita-cmd kube renew-certs` while keeping this
execution model and help-script convention.

## Goals / Non-Goals

**Goals:**
- Add a new `kube renew-certs` command following existing script conventions.
- Provide explicit help output through a paired `_help` script.
- Make failure modes explicit when certificate renewal binaries are missing.

**Non-Goals:**
- Re-architecting `nita-cmd` dispatch logic.
- Automatically restarting control-plane components beyond what the renewal
  command itself requires.
- Implementing certificate expiry monitoring/alerting.

## Decisions

### Decision 1: Implement as standalone script pair

**Choice:** Create `nita-cmd_kube_renew-certs` and
`nita-cmd_kube_renew-certs_help` in `cli_scripts/`.

**Rationale:** This matches the current extension mechanism and keeps command
registration zero-touch for the dispatcher.

### Decision 2: Prefer `kubeadm certs renew all` when available

**Choice:** Use `kubeadm certs renew all` as the primary renewal action.

**Rationale:** `kubeadm` is the standard certificate lifecycle interface for
kubeadm-managed clusters and provides a single command for renewing all control
plane certificates.

**Alternatives considered:**
- `kubectl certificate approve` flow only: handles CSRs but does not renew all
  control-plane certificates.
- Custom per-certificate renewal scripts: higher maintenance burden and less
  portability.

### Decision 3: Fail fast with actionable error when unsupported

**Choice:** If required binaries are unavailable, print a clear unsupported
message and exit non-zero.

**Rationale:** Existing scripts already perform binary detection; this preserves
predictable behavior and avoids partial/no-op execution.

## Risks / Trade-offs

- **Environment mismatch**: clusters not provisioned with kubeadm may not
  support `kubeadm certs renew all`.
- **Privileges**: renewal typically requires elevated privileges; invocation may
  fail without proper permissions.
- **Operational follow-up**: some environments require control-plane component
  restarts after renewal; this command should document, not automate, that
  workflow.

## Migration Plan

1. Add the new command and help scripts in `cli_scripts/`.
2. Update `docs/nita-cmd.md` command reference with usage and caveats.
3. Validate output in both normal and `_CLI_RUNNER_DEBUG=1` modes.
4. Run the command in an environment with and without `kubeadm` to validate
   success and failure messaging.
