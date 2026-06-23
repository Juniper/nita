## 1. CLI Script

- [x] 1.1 Add `cli_scripts/nita-cmd_kube_renew-certs` with project header and
      the same command-selection/debug pattern used by existing kube scripts
- [x] 1.2 Implement primary command execution for certificate renewal via
      `kubeadm certs renew all` when available
- [x] 1.3 Return a clear non-zero error and message when certificate renewal is
      unsupported in the current environment

## 2. Help Script

- [x] 2.1 Add `cli_scripts/nita-cmd_kube_renew-certs_help` with one-line usage
      text consistent with existing `_help` scripts

## 3. Documentation

- [x] 3.1 Update `docs/nita-cmd.md` to include `nita-cmd kube renew-certs`
- [x] 3.2 Document prerequisites and operational caveats (permissions,
      kubeadm-managed clusters, post-renewal restart expectations)

## 4. Verification

- [ ] 4.1 Confirm the new command appears in `nita-cmd kube help`
- [ ] 4.2 Run `nita-cmd kube renew-certs` where `kubeadm` exists and confirm
      renewal command execution
- [ ] 4.3 Run `nita-cmd kube renew-certs` where `kubeadm` is absent and confirm
      expected error behavior and non-zero exit code
- [ ] 4.4 Run with `_CLI_RUNNER_DEBUG=1` and confirm the underlying command is
      printed to stderr before execution
