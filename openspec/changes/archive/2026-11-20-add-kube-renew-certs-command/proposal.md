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

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `cli`: Add a Kubernetes certificate renewal sub-command under
  `nita-cmd kube`.

## Impact

- CLI scripts: two new scripts in `cli_scripts/`
- Documentation: one update in `docs/nita-cmd.md`
- Runtime dependency: the command path relies on `kubeadm` availability for
  direct certificate renewal, and should fail with a clear message when
  unsupported
