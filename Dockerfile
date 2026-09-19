# Current immutable Plow Hermes base. The tag names the source commit and the
# digest prevents registry-side substitution.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-ef0019372ff8bca593611b31ebd2e08f9f1458ff@sha256:a8a2f97ad78b8192d80a984dce81d3bf5a9a883d18cb7b677704913a09b56aee

# plow-init composes this variant persona after the protected base persona on
# every boot. Never copy identity into the mutable Hermes home.
COPY --chown=0:0 runtime/persona.md /opt/hermes/plow-seed/persona.md
RUN chmod 0644 /opt/hermes/plow-seed/persona.md

# Keep the immutable bundled source outside the writable Hermes home. The base
# reconciles it into an empty or unmodified persistent home on boot.
COPY --chown=0:0 skills/scout/ /opt/hermes/skills/scout/
RUN find /opt/hermes/skills/scout -type d -exec chmod 0755 {} + \
 && find /opt/hermes/skills/scout -type f -name '*.py' -exec chmod 0755 {} + \
 && find /opt/hermes/skills/scout -type f ! -name '*.py' -exec chmod 0644 {} + \
 && /opt/hermes/.venv/bin/python3 -m compileall -q /opt/hermes/skills/scout/scripts

# The base image includes general-purpose productivity skills. Scout is a
# reconnaissance-only agent, so remove them from both the initial home and the
# bundled reconciliation source; Latch browser tools remain supplied by Hermes.
RUN rm -rf /var/lib/hermes/skills/growth /var/lib/hermes/skills/productivity \
 && rm -rf /opt/hermes/skills/growth /opt/hermes/skills/productivity

COPY image/s6-overlay/ /etc/s6-overlay/
