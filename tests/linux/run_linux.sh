#!/usr/bin/env bash
# Build the disposable Linux lab, run the deterministic proofs, copy the evidence out.
# Needs Docker. No host folder is mounted into the container; the only network is
# an internal Docker network shared with a small HTTP receiver (no internet).
set -euo pipefail
LAB="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$LAB/evidence/linux"
TAG="cscart-lab-$(date +%Y%m%d%H%M%S)"
NET="$TAG-net"
WEAKER="${LAB_WEAKER_NESTED:-1}"

docker build -q -t cscart-lab:latest -f "$LAB/tests/linux/Dockerfile" "$LAB" > /dev/null
docker network create --internal "$NET" > /dev/null
docker run -d --name "$TAG-receiver" --network "$NET" --network-alias receiver \
  --cap-drop ALL --security-opt no-new-privileges --read-only cscart-lab:latest \
  python3 -u -c "
import http.server, sys
class H(http.server.BaseHTTPRequestHandler):
    def _r(self):
        n = int(self.headers.get('Content-Length') or 0); self.rfile.read(n)
        print('RECEIVED', self.command, self.path, flush=True)
        self.send_response(200); self.end_headers(); self.wfile.write(b'received')
    do_GET = do_POST = _r
    def log_message(self, *a): pass
http.server.HTTPServer(('0.0.0.0', 8080), H).serve_forever()" > /dev/null

# Capabilities: everything dropped, then only what the root evidence collector needs
# (switch to devuser/produser, start MariaDB as mysql, read root-only folders).
# Nested-sandbox workarounds, recorded here on purpose (see evidence/linux/README.md):
#  - seccomp=unconfined and apparmor=unconfined: Docker's default profiles refuse the
#    user namespace and mount calls that bubblewrap needs inside a container;
#  - LAB_WEAKER_NESTED=1 sets the sandbox runtime's enableWeakerNestedSandbox, because an
#    unprivileged container cannot mount a fresh /proc (documented by Anthropic for Docker);
#  - the Docker host must allow unprivileged user namespaces (Ubuntu 24.04+:
#    kernel.apparmor_restrict_unprivileged_userns=0). Its value is recorded below.
set +e
docker run --name "$TAG-proofs" --network "$NET" \
  --cap-drop ALL --cap-add SETUID --cap-add SETGID --cap-add CHOWN --cap-add DAC_OVERRIDE \
  --cap-add FOWNER --cap-add SETFCAP \
  --security-opt seccomp=unconfined --security-opt apparmor=unconfined --security-opt no-new-privileges \
  -e LAB_WEAKER_NESTED="$WEAKER" cscart-lab:latest > "$OUT.console.txt" 2>&1
CODE=$?
set -e
STAGE="$(mktemp -d)"
docker cp "$TAG-proofs:/evidence/." "$STAGE/"
docker logs "$TAG-receiver" > "$STAGE/receiver.log" 2>&1
mv "$OUT.console.txt" "$STAGE/console.txt"
docker inspect "$TAG-proofs" --format '{{json .HostConfig}}' > "$STAGE/container-hostconfig.json"
docker inspect "$TAG-proofs" --format '{{json .Mounts}}' > "$STAGE/container-mounts.json"
docker image inspect cscart-lab:latest --format '{{.Id}} {{json .RepoDigests}}' > "$STAGE/image.txt"
docker info --format '{{.Name}} | {{.OperatingSystem}} | kernel {{.KernelVersion}} | {{json .SecurityOptions}}' > "$STAGE/docker-host.txt"
docker run --rm cscart-lab:latest cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns >> "$STAGE/docker-host.txt" 2>&1 || true
docker network inspect "$NET" --format '{{json .Internal}}' > "$STAGE/network-internal.txt"
docker rm -f "$TAG-proofs" "$TAG-receiver" > /dev/null
docker network rm "$NET" > /dev/null
# previous evidence is moved aside to a temporary folder, never deleted
if [ -d "$OUT" ]; then mv "$OUT" "$(mktemp -d)/"; fi
mv "$STAGE" "$OUT"
if grep -q "RECEIVED .*/sandboxed-" "$OUT/receiver.log"; then
  echo "FAILED: the receiver logged a request sent from inside the sandbox"; CODE=1
fi
grep -q "RECEIVED .*/witness-unsandboxed" "$OUT/receiver.log" || { echo "FAILED: receiver witness missing"; CODE=1; }
echo "proofs exit code: $CODE, evidence in evidence/linux/"
exit $CODE
