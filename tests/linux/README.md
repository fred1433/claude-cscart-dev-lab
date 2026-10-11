# Linux proofs: how the container is set up, and what that weakens

`run_linux.sh` builds `cscart-lab:latest` (Debian 12 with Node 22, bubblewrap,
socat, ripgrep, MariaDB, the sandbox runtime `@anthropic-ai/sandbox-runtime@0.0.77`
and the Claude Code CLI `2.1.296`) and runs `proofs.py` inside it.

Isolation of the run itself:
- no host folder mounted (`container-mounts.json` is `[]`), no Docker socket,
  no SSH agent, no model credentials; `proofs.py` refuses to start otherwise
  (`environment.json` > `checks`);
- network: an `--internal` Docker network shared only with a small HTTP
  receiver; no internet (case F11-container-no-internet);
- all capabilities dropped, then only what the root evidence collector needs
  (switching to `devuser`/`produser`, starting MariaDB); `no-new-privileges`;
  `devuser` processes run with an empty effective capability set;
- evidence is written to `/evidence` (root, mode 700) and copied out with
  `docker cp` after the run.

Nested-sandbox workarounds (bubblewrap inside Docker):
- `--security-opt seccomp=unconfined` and `apparmor=unconfined` on the
  container: Docker's default profiles refuse the namespace and mount calls
  bubblewrap needs;
- `enableWeakerNestedSandbox: true` in the sandbox runtime settings: an
  unprivileged container cannot mount a fresh `/proc` for the sandbox
  (Anthropic documents this flag for Docker and warns it weakens the sandbox);
- the Docker host must allow unprivileged user namespaces. On our machine the
  default Docker VM is Ubuntu 24.04 with
  `kernel.apparmor_restrict_unprivileged_userns=1`, and the first run failed
  there (`evidence/attempts/linux-run1-default-vm-apparmor/console.txt`). The
  proofs then ran in a separate, dedicated VM with that sysctl set to `0`
  (`docker-host.txt` records the value seen by the container).

So these results show what the sandbox runtime's filesystem, network and
socket rules do on Linux, with a weaker `/proc` isolation than a bare-metal
server would have. On a real VPS none of the container workarounds apply; only
the bubblewrap/socat/AppArmor prerequisites of the developer guide do.

The sandbox settings used (`environment.json` > `srt_settings`) are written by
`proofs.py` from the same `policy.json` as the kit: protected paths become
`denyWrite`, `config.local.php` and `~/.ssh` become `denyRead`, the dev copy is
the only `allowWrite`, and no network domain is allowed. Claude Code merges
its permission rules into its own sandbox configuration; these tests exercise
the runtime directly, without a model.
Raw files write the long dash character of tool output as `--`.

Known gap of these settings: on Linux the runtime expands `denyWrite` to the
paths that exist when a command starts. A new file matching a protected
pattern (for example a new `.sql` file, or anything under
`templates/views/orders/`, which the fixture does not contain) is not covered
by the sandbox here; the guard and the permission deny rules still name those
patterns for Claude's file tools.
