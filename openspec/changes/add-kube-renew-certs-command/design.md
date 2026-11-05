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
- Clearly explain that renewal is local to the host and requires a manual
  control-plane Pod restart afterward.

**Non-Goals:**
- Re-architecting `nita-cmd` dispatch logic.
- Automatically restarting kubelet or control-plane components.
- Implementing certificate expiry monitoring/alerting.

## Decisions

### Decision 1: Implement as standalone script pair

**Choice:** Create `nita-cmd_kube_renew-certs` and
`nita-cmd_kube_renew-certs_help` in `cli_scripts/`.

**Rationale:** This matches the current extension mechanism and keeps command
registration zero-touch for the dispatcher.

### Decision 2: Prefer `kubeadm certs renew all` when available

**Choice:** Run `kubeadm certs renew all` on the local host, without restarting
kubelet or control-plane Pods.

**Rationale:** `kubeadm` is the standard certificate lifecycle interface for
kubeadm-managed clusters and provides a single command for renewing all control
plane certificates.

The command does not renew certificates on other control-plane nodes. In a
replicated control plane, operators must run it on every control-plane node.
After renewal, operators must restart the control-plane static Pods using the
procedure documented by kubeadm. Restarting kubelet alone is not sufficient.

**Alternatives considered:**
- `kubectl certificate approve` flow only: handles CSRs but does not renew all
  control-plane certificates.
- Custom per-certificate renewal scripts: higher maintenance burden and less
  portability.

### Decision 3: Leave component restarts to the operator

**Choice:** Do not restart kubelet or static Pods automatically. On success,
print a reminder that the control-plane static Pods must be restarted and that
the command must be run on every control-plane node in a replicated cluster.

**Rationale:** Static Pod restarts are disruptive and require an ordered,
host-local procedure. Restarting the kubelet service does not itself perform
the required control-plane Pod restart, so the command must not imply that
certificates are fully active after only a kubelet restart.

### Decision 4: Fail fast with actionable error when unsupported

**Choice:** If required binaries are unavailable, print a clear unsupported
message and exit non-zero.

**Rationale:** Existing scripts already perform binary detection; this preserves
predictable behavior and avoids partial/no-op execution.

## Risks / Trade-offs

- **Environment mismatch**: clusters not provisioned with kubeadm may not
  support `kubeadm certs renew all`.
- **External CA**: kubeadm cannot renew externally managed certificates; the
  documentation must make this limitation explicit.
- **Privileges**: renewal typically requires elevated privileges; invocation may
  fail without proper permissions.
- **Operational follow-up**: control-plane static Pods must be restarted after
  renewal, and replicated control planes require the command on every
  control-plane node. The command documents these steps but does not automate
  them.

## Migration Plan

1. Add the new command and help scripts in `cli_scripts/`.
2. Update `docs/nita-cmd.md` and `docs/certificates.md` with usage, host scope,
  external-CA limitations, and required post-renewal steps.
3. Validate output in both normal and `_CLI_RUNNER_DEBUG=1` modes.
4. Test command selection with mocked binaries so no real certificate renewal
  runs during validation; separately verify the procedure in a disposable
  kubeadm cluster before release.
