## Why

Kubernetes certificate expiration can cause disruptive control-plane or node
authentication failures. NITA already provides `nita-cmd kube` operational
helpers, but it does not provide a guided command for certificate renewal.
Adding `nita-cmd kube renew-certs` gives operators a single, documented entry
point for this maintenance task and keeps command behavior consistent with the
existing `cli_scripts` model.

## What Changes

- **New** `cli_scripts/nita-cmd_kube_renew-certs`: Adds the
  `nita-cmd kube renew-certs` sub-command.
- **New** `cli_scripts/nita-cmd_kube_renew-certs_help`: Adds help text for the
  new sub-command.
- **Modified** `docs/nita-cmd.md`: Documents the new command and expected
  behavior.
- **Modified** `docs/certificates.md`: Explains the required control-plane
  Pod restart, per-node execution for replicated control planes, and the
  limitation for certificates managed by an external CA.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `cli`: Add a Kubernetes certificate renewal sub-command under
  `nita-cmd kube`.

## Impact

- CLI scripts: two new scripts in `cli_scripts/`
- Documentation: updates to `docs/nita-cmd.md` and `docs/certificates.md`
- Runtime dependency: the command path relies on `kubeadm` availability for
  renewal on the local host. It does not restart control-plane Pods; operators
  must follow the documented post-renewal procedure. Externally managed
  certificates are outside the command's scope.
