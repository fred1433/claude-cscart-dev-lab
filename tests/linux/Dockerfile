# Disposable Linux lab for the deterministic proofs. No host folder is mounted;
# results are copied out with `docker cp` after the run.
FROM node:22-bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 git bubblewrap socat ripgrep curl ca-certificates \
      mariadb-server mariadb-client procps libcap2-bin util-linux \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/sandbox-runtime@0.0.77 @anthropic-ai/claude-code@2.1.296 >/tmp/npm.log 2>&1 \
 && rm -f /tmp/npm.log
COPY fixture /lab/fixture
COPY kit /lab/kit
COPY tools /lab/tools
COPY tests /lab/tests
RUN useradd -m -u 1001 devuser && useradd -m -u 1002 produser \
 && chown -R root:root /lab && chmod -R a+rX,go-w /lab \
 # synthetic production copy, owned by another account
 && mkdir -p /srv/prod && cp -r /lab/fixture/shop /srv/prod/shop && chown -R produser:produser /srv/prod \
 && chmod -R u+rwX,go+rX,go-w /srv/prod \
 # dev copy, owned by the account Claude Code would run as
 && mkdir -p /srv/dev && chown devuser:devuser /srv/dev \
 && su devuser -c "python3 /lab/tools/make_workspace.py /srv/dev/shop" \
 # admin-installed policy: readable by devuser, not writable
 && mkdir -p /opt/claude-cscart-guard /etc/claude-code \
 && cp /lab/kit/.claude/guard/guard.py /opt/claude-cscart-guard/ \
 && python3 -c "import json; p=json.load(open('/lab/kit/.claude/guard/policy.json')); p['project_root']='/srv/dev/shop'; p['production_roots']=['/srv/prod']; json.dump(p, open('/opt/claude-cscart-guard/policy.json','w'), indent=2)" \
 && python3 /lab/kit/admin/build_settings.py --managed /srv/dev/shop /opt/claude-cscart-guard > /etc/claude-code/managed-settings.json \
 && chmod 755 /opt/claude-cscart-guard /etc/claude-code && chmod 644 /opt/claude-cscart-guard/* /etc/claude-code/managed-settings.json \
 # a fake SSH key in the dev account, to test secret reads
 && mkdir -p /home/devuser/.ssh && echo "CANARY_SSH_KEY_d34db33f" > /home/devuser/.ssh/id_lab \
 && chown -R devuser:devuser /home/devuser/.ssh && chmod 700 /home/devuser/.ssh && chmod 600 /home/devuser/.ssh/id_lab \
 && mkdir -p /evidence && chmod 700 /evidence
CMD ["python3", "/lab/tests/linux/proofs.py"]
