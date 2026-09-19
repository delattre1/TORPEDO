import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "image" / "s6-overlay" / "s6-rc.d" / "agent-index"
SCOUT_SCOPE = ROOT / "image" / "s6-overlay" / "s6-rc.d" / "scout-scope"
SCOUT_SCOPE_SCRIPT = ROOT / "image" / "s6-overlay" / "scripts" / "scout-scope.sh"
VERIFY_WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"


class TestPackaging(unittest.TestCase):
    def test_hackathon_license_is_mit(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Permission is hereby granted", license_text)

    def test_usage_reporter_is_the_base_images_own(self):
        # A same-named service here would replace the base's at COPY image/s6-overlay/.
        self.assertFalse(SERVICE.exists())
        self.assertFalse((ROOT / "image" / "s6-overlay" / "s6-rc.d" / "user" / "contents.d" / "agent-index").exists())
        self.assertNotIn("client.pin", (ROOT / "Dockerfile").read_text())

    def test_ci_actions_are_immutable_and_container_boot_is_smoke_tested(self):
        workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")
        action_uses = re.findall(r"(?m)^\s*- uses:\s*([^\s#]+)", workflow)
        self.assertGreaterEqual(len(action_uses), 2)
        for action in action_uses:
            with self.subTest(action=action):
                self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")
        self.assertIn("docker run --detach", workflow)
        self.assertIn("service scout-scope successfully started", workflow)
        self.assertIn("service dashboard successfully started", workflow)
        self.assertIn("unable to start service", workflow)
        self.assertIn("agent-index-client.py --self-check", workflow)

    def test_base_is_immutable(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertRegex(dockerfile, r"(?m)^FROM .*:base-[0-9a-f]{40}@sha256:[0-9a-f]{64}$")
        self.assertNotRegex(dockerfile, r"COPY[^\n]*/var/lib/hermes/skills")

    def test_compose_preserves_home_and_mounts_credentials_read_only(self):
        compose = (ROOT / "compose.yml").read_text()
        self.assertIn("agent-home:/var/lib/hermes", compose)
        self.assertIn("credentials.host:ro", compose)
        self.assertIn("AGENT_ID", compose)
        self.assertIn("AGENT_ID: ${AGENT_ID:-scout}", compose)

    def test_scout_persona_is_installed_after_base_bootstrap(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("runtime/persona.md /opt/hermes/plow-seed/persona.md", dockerfile)
        self.assertNotIn("/var/lib/hermes/SOUL.md", dockerfile)

    def test_generic_productivity_skills_are_excluded_from_scout_image(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        for path in (
            "/var/lib/hermes/skills/growth",
            "/var/lib/hermes/skills/productivity",
            "/opt/hermes/skills/growth",
            "/opt/hermes/skills/productivity",
        ):
            with self.subTest(path=path):
                self.assertIn(path, dockerfile)

    def test_existing_homes_are_stripped_of_generic_productivity_skills_before_gateway(self):
        self.assertEqual("oneshot", (SCOUT_SCOPE / "type").read_text().strip())
        cleanup = (SCOUT_SCOPE / "up").read_text().strip()
        self.assertEqual("/bin/sh /etc/s6-overlay/scripts/scout-scope.sh", cleanup)
        scope_script = SCOUT_SCOPE_SCRIPT.read_text()
        self.assertIn("/var/lib/hermes/skills/scout", scope_script)
        self.assertIn("/opt/hermes/skills/scout", scope_script)
        self.assertIn("/var/lib/hermes/skills/growth", scope_script)
        self.assertIn("/var/lib/hermes/skills/productivity", scope_script)
        subprocess.run(["sh", "-n", str(SCOUT_SCOPE_SCRIPT)], check=True)
        self.assertTrue(
            (ROOT / "image" / "s6-overlay" / "s6-rc.d" / "hermes-gateway" / "dependencies.d" / "scout-scope").exists()
        )
        self.assertTrue(
            (ROOT / "image" / "s6-overlay" / "s6-rc.d" / "user" / "contents.d" / "scout-scope").exists()
        )

    def test_persona_limits_scout_to_reconnaissance(self):
        persona = " ".join((ROOT / "runtime" / "persona.md").read_text(encoding="utf-8").split())
        self.assertIn("only product purpose is digital-process reconnaissance", persona)
        self.assertIn("Do not present yourself as a general digital assistant", persona)
        for unsupported_capability in (
            "email", "calendar", "files", "price monitoring", "documents", "spreadsheets",
        ):
            with self.subTest(unsupported_capability=unsupported_capability):
                self.assertIn(unsupported_capability, persona)
        self.assertIn("Ask them to send a link or name a specific process to scout", persona)
        self.assertIn("Olá, sou o Scout.", persona)
        self.assertIn("Envie um link ou diga qual processo quer que eu investigue.", persona)


if __name__ == "__main__":
    unittest.main()
