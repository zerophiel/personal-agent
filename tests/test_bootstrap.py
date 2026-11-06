"""make bootstrap (scripts/bootstrap.sh, scripts/bootstrap-host.sh) and make preflight (scripts/preflight.sh) against a fake host:
fake commands note their arguments, and the host's paths live under a temp folder. A real run happens only at a real move."""
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PACKAGES = os.path.join(ROOT, "config", "host-packages.txt")
DROP_IN = "etc/ssh/sshd_config.d/00-hardening.conf"
SUDOERS = "etc/sudoers.d/90-personal-agent-login"
KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIkunciUjiSaja pemilik@laptop"
GB4 = 4 * 1024 * 1024 * 1024

NOTE = 'printf \'%s\\n\' "$(basename "$0") $*" >> "$CALLS"\n'
HOST_FAKES = {
    "apt-get": NOTE + '[ -z "${APT_FAIL:-}" ] || { echo "apt gagal di sini"; exit 100; }\n',
    "chown": NOTE,
    "cloud-init": NOTE,
    "docker": NOTE + 'if [ "$1" = ps ]; then printf "%s" "${CONTAINERS:-}"; fi\n',
    "dpkg": 'echo "${ARCH:-amd64}"\n',
    "dpkg-query": ('name="${@: -1}"\n'
                   'if [ "$name" = "${DIFFERENT:-}" ]; then printf 9.9; else awk -v n="$name" \'$1 == n {printf "%s", $2}\' "$PACKAGES"; fi\n'),
    "fallocate": NOTE + 'touch "${@: -1}"\n',
    "getent": 'echo "$2:x:1000:1000::/home/$2:/bin/bash"\n',
    "id": ('case "$1" in\n'
           '  -u) [ -e "$ACCOUNTS/$2" ] && echo 1000 ;;\n'
           '  -gn) echo "$2" ;;\n'
           'esac\n'),
    "install": (NOTE + 'args=()\nwhile [ $# -gt 0 ]; do\n  case "$1" in\n    -o|-g) shift 2 ;;\n    *) args+=("$1"); shift ;;\n'
                '  esac\ndone\nexec "$REAL_INSTALL" "${args[@]}"\n'),
    "mkswap": NOTE,
    "sshd": NOTE + 'exit "${SSHD_RC:-0}"\n',
    "swapoff": NOTE,
    "swapon": ('case "$1" in\n  --show*) printf "%s" "${SWAP_SIZES:-}" ;;\n'
               '  *) printf \'%s\\n\' "swapon $*" >> "$CALLS" ;;\nesac\n'),
    "sysctl": NOTE,
    "systemctl": NOTE,
    "timedatectl": NOTE,
    "ufw": NOTE,
    "useradd": NOTE + 'touch "$ACCOUNTS/${@: -1}"\n',
    "visudo": NOTE + 'cp "${@: -1}" "$SUDOERS_SEEN"\nexit "${VISUDO_RC:-0}"\n',
}
# Runs the remote command here. It notes who logged in and with which options, and can fail the proof or keep the upload.
FAKE_SSH = r"""#!/bin/bash
opts=""
while [ "$1" = "-o" ]; do opts="$opts $2"; shift 2; done
to=$1
shift
cmd="$*"
case "$cmd" in
  *.bootstrap-proof*) kind=proof ;;
  *bootstrap-host.sh*first*) kind=first ;;
  *bootstrap-host.sh*second*) kind=second ;;
esac
printf '%s %s %s\n' "$kind" "$to" "$opts" >> "$SSH_LOG"
case "$cmd" in
  "sudo -n "*) printf 'with-sudo\n' >> "$SSH_LOG" ;;
esac
[ "$kind" != proof ] || [ -z "${PROOF_FAIL:-}" ] || exit 255
[ "$kind" != "${SSH_REFUSE:-none}" ] || exit 255
cmd=${cmd//sudo -n /}
cmd=${cmd//\/opt\//$BOOTSTRAP_ROOT\/opt\/}
if [ "$kind" = first ]; then
  tee "$UPLOAD_COPY" | bash -c "$cmd"
  exit "${PIPESTATUS[1]}"
fi
exec bash -c "$cmd"
"""


def write(path, body, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    if mode is not None:
        os.chmod(path, mode)
    return path


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def package_rows():
    return [line.split() for line in read(PACKAGES).splitlines() if not line.startswith("#")]


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.rootfs = os.path.join(self.d, "rootfs")
        write(os.path.join(self.rootfs, "etc", "os-release"), 'ID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04.4 LTS"\n')
        write(os.path.join(self.rootfs, "etc", "fstab"), "UUID=abc / ext4 defaults 0 1\n")
        os.makedirs(os.path.join(self.rootfs, "var", "log"))
        self.up = os.path.join(self.d, "upload")
        shutil.copytree(os.path.join(ROOT, "host", "etc"), os.path.join(self.up, "host", "etc"))
        os.makedirs(os.path.join(self.up, "config"))
        shutil.copy(PACKAGES, os.path.join(self.up, "config"))
        os.makedirs(os.path.join(self.up, "scripts"))
        shutil.copy(os.path.join(ROOT, "scripts", "bootstrap-host.sh"), os.path.join(self.up, "scripts"))
        write(os.path.join(self.up, "login.pub"), KEY + "\n")
        self.bin = os.path.join(self.d, "bin")
        for name, body in HOST_FAKES.items():
            write(os.path.join(self.bin, name), "#!/bin/bash\n" + body, stat.S_IRWXU)
        self.accounts = os.path.join(self.d, "accounts")
        os.mkdir(self.accounts)
        self.calls_file = os.path.join(self.d, "calls")
        self.seen = os.path.join(self.d, "sudoers-seen")
        self.env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], BOOTSTRAP_ROOT=self.rootfs, CALLS=self.calls_file,
                        ACCOUNTS=self.accounts, SUDOERS_SEEN=self.seen, PACKAGES=PACKAGES, REAL_INSTALL=shutil.which("install"))

    def run_host(self, part="first", login="pemilik", **env):
        return subprocess.run(["bash", os.path.join(self.up, "scripts", "bootstrap-host.sh"), part, self.up, login],
                              env=dict(self.env, **env), capture_output=True, text=True, timeout=60)

    def good(self, part="first", **env):
        done = self.run_host(part, **env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done

    def calls(self):
        return read(self.calls_file).splitlines() if os.path.exists(self.calls_file) else []

    def at(self, text, start=0):
        """The first call at or after start that holds this text."""
        for i, call in enumerate(self.calls()):
            if i >= start and text in call:
                return i
        self.fail(f"no call with {text!r}: {self.calls()}")

    def host_path(self, rel):
        return os.path.join(self.rootfs, rel)


class FirstPart(Base):
    def test_the_doors_stay_as_they_are(self):
        self.good()
        self.assertFalse(os.path.exists(self.host_path(DROP_IN)))
        for call in self.calls():
            self.assertFalse(call.startswith(("ufw", "sshd")), call)
            self.assertNotIn("restart ssh", call)
            self.assertNotIn("reload-or-restart", call)

    def test_docker_finds_its_config_and_apt_its_source_before_they_are_used(self):
        self.good()
        update = self.at("apt-get")
        self.assertIn(" update", self.calls()[update])
        for name in ("etc/docker/daemon.json", "etc/apt/sources.list.d/docker.list", "etc/apt/keyrings/docker.asc"):
            self.assertLess(self.at(name), update)

    def test_only_docker_is_pinned_and_all_listed_packages_come(self):
        self.good()
        installs = [c for c in self.calls() if c.startswith("apt-get") and " install " in c]
        self.assertEqual(len(installs), 2)
        rows = package_rows()
        named, pinned = installs
        for name, version, how in rows:
            if how == "pin":
                self.assertIn(f" {name}={version}", pinned)
            else:
                self.assertIn(f" {name}", named)
                self.assertNotIn(f"{name}=", named)
        self.assertEqual(sorted(r[0] for r in rows if r[2] == "pin"),
                         sorted(["docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"]))

    def test_apt_waits_for_a_held_lock_and_keeps_the_recipe_files(self):
        self.good()
        for call in self.calls():
            if call.startswith("apt-get"):
                self.assertIn("DPkg::Lock::Timeout=600", call)
                self.assertIn("--force-confold", call)

    def test_the_recipe_wins_over_what_a_package_wrote(self):
        self.good()
        last_install = max(i for i, c in enumerate(self.calls()) if c.startswith("apt-get") and " install " in c)
        self.at("etc/apt/apt.conf.d/20auto-upgrades", last_install)

    def test_limits_time_and_docker_take_effect(self):
        self.good()
        calls = self.calls()
        self.assertIn("sysctl --system", calls)
        self.assertIn("systemctl restart systemd-journald", calls)
        self.assertIn("systemctl restart docker", calls)
        self.assertIn("timedatectl set-timezone Asia/Jakarta", calls)
        self.assertLess(self.at("etc/docker/daemon.json"), self.at("systemctl restart docker"))

    def test_the_data_and_secrets_folders_stay_absent(self):
        self.good()
        self.assertFalse(os.path.exists(self.host_path("opt/personal-agent-data")))
        self.assertFalse(os.path.exists(self.host_path("opt/personal-agent-secrets")))
        self.assertTrue(os.path.isdir(self.host_path("opt/personal-agent")))
        self.at(f"-o pemilik -g pemilik {self.host_path('opt/personal-agent')}")

    def test_it_waits_for_cloud_init_when_the_host_has_it(self):
        self.good()
        self.assertLess(self.at("cloud-init status --wait"), self.at("apt-get"))

    def test_a_host_without_cloud_init_is_fine(self):
        os.unlink(os.path.join(self.bin, "cloud-init"))
        self.good()

    def test_a_failed_apt_stops_and_shows_the_end_of_its_log(self):
        done = self.run_host(APT_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.assertIn("apt gagal di sini", done.stderr)
        self.assertNotIn("timedatectl set-timezone Asia/Jakarta", self.calls())

    def test_a_different_version_is_reported_and_is_not_a_failure(self):
        done = self.good(DIFFERENT="restic")
        version = next(r[1] for r in package_rows() if r[0] == "restic")
        self.assertIn(f"restic is 9.9 here, {version} on the old host", done.stdout)
        self.assertIn("packages: 1 differ", done.stdout)
        self.assertIn("packages: 0 differ", self.good().stdout)

    def test_running_twice_is_fine(self):
        self.good()
        self.good()
        self.assertEqual(read(self.host_path("home/pemilik/.ssh/authorized_keys")), KEY + "\n")
        self.assertEqual(sum("/swapfile" in line for line in read(self.host_path("etc/fstab")).splitlines()), 1)

    def test_every_file_of_the_recipe_arrives(self):
        self.good()
        self.good("second")
        recipe = os.path.join(ROOT, "host")
        for folder, _, names in os.walk(os.path.join(recipe, "etc")):
            for name in names:
                rel = os.path.relpath(os.path.join(folder, name), recipe)
                if rel == SUDOERS:
                    continue
                with self.subTest(rel=rel):
                    self.assertEqual(read(os.path.join(recipe, rel)), read(self.host_path(rel)))


class Swap(Base):
    def test_a_host_without_swap_gets_four_gigabytes(self):
        self.good()
        self.at(f"fallocate -l {GB4} ")
        self.assertIn("/swapfile none swap sw 0 0\n", read(self.host_path("etc/fstab")))
        self.assertEqual(stat.S_IMODE(os.stat(self.host_path("swapfile")).st_mode), 0o600)
        self.assertLess(self.at("mkswap"), self.at("swapon "))

    def test_the_providers_swap_counts(self):
        self.good(SWAP_SIZES="2084564992\n")
        self.at(f"fallocate -l {GB4 - 2084564992} ")

    def test_enough_swap_adds_nothing(self):
        self.good(SWAP_SIZES=f"{GB4}\n")
        self.assertFalse(any(c.startswith("fallocate") for c in self.calls()))
        self.assertNotIn("swapfile", read(self.host_path("etc/fstab")))

    def test_a_listed_swapfile_is_left_alone(self):
        write(self.host_path("etc/fstab"), "/swapfile none swap sw 0 0\n")
        self.good()
        self.assertFalse(any(c.startswith(("fallocate", "swapoff")) for c in self.calls()))

    def test_a_file_left_by_a_stopped_run_is_made_again(self):
        write(self.host_path("swapfile"), "potongan")
        self.good()
        self.assertLess(self.at("swapoff"), self.at("fallocate"))
        self.assertEqual(os.path.getsize(self.host_path("swapfile")), 0)


class Account(Base):
    def keys(self):
        return read(self.host_path("home/pemilik/.ssh/authorized_keys"))

    def test_a_new_account_gets_the_key_with_tight_modes(self):
        self.good()
        self.at("useradd --create-home --shell /bin/bash pemilik")
        self.assertEqual(self.keys(), KEY + "\n")
        self.assertEqual(stat.S_IMODE(os.stat(self.host_path("home/pemilik/.ssh/authorized_keys")).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.host_path("home/pemilik/.ssh")).st_mode), 0o700)
        self.at("chown pemilik:pemilik ")

    def test_an_existing_account_keeps_its_keys(self):
        write(os.path.join(self.accounts, "pemilik"), "")
        write(self.host_path("home/pemilik/.ssh/authorized_keys"), "ssh-rsa KUNCILAMA provider")   # no newline at the end
        self.good()
        self.assertFalse(any(c.startswith("useradd") for c in self.calls()))
        self.assertEqual(self.keys(), f"ssh-rsa KUNCILAMA provider\n{KEY}\n")

    def test_sudo_comes_from_a_checked_file_with_the_account_filled_in(self):
        self.good()
        rule = read(self.host_path(SUDOERS))
        self.assertIn("pemilik ALL=(ALL) NOPASSWD:ALL\n", rule)
        self.assertNotIn("@LOGIN@", rule)
        self.assertEqual(read(self.seen), rule)
        self.assertEqual(stat.S_IMODE(os.stat(self.host_path(SUDOERS)).st_mode), 0o440)
        self.assertLess(self.at("visudo -cf"), self.at(SUDOERS))

    def test_a_rule_visudo_rejects_is_not_installed(self):
        done = self.run_host(VISUDO_RC="1")
        self.assertEqual(done.returncode, 1)
        self.assertIn("visudo", done.stderr)
        self.assertFalse(os.path.exists(self.host_path(SUDOERS)))


class Refusals(Base):
    def assert_refused(self, done, text):
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn(text, done.stderr)
        self.assertEqual(self.calls(), [c for c in self.calls() if c.startswith("docker ps")])
        self.assertEqual(sorted(os.listdir(self.rootfs)), ["etc", "var"])

    def test_another_ubuntu_or_another_system(self):
        for body in ('ID=ubuntu\nVERSION_ID="22.04"\nPRETTY_NAME="Ubuntu 22.04"\n', 'ID=debian\nVERSION_ID="24.04"\n'):
            with self.subTest(body=body):
                write(self.host_path("etc/os-release"), body)
                for part in ("first", "second"):
                    self.assert_refused(self.run_host(part), "Ubuntu 24.04")

    def test_another_architecture(self):
        self.assert_refused(self.run_host(ARCH="arm64"), "amd64")

    def test_a_host_with_the_projects_containers(self):
        for part in ("first", "second"):
            self.assert_refused(self.run_host(part, CONTAINERS="abc123\n"), "containers")

    def test_a_host_holding_a_ledger(self):
        write(self.host_path("opt/personal-agent-data/vault-tools/ledger.db"), "x")
        done = self.run_host()
        self.assertEqual(done.returncode, 1)
        self.assertIn("ledger", done.stderr)
        self.assertEqual([c for c in self.calls() if not c.startswith("docker ps")], [])

    def test_root_as_the_login(self):
        self.assert_refused(self.run_host(login="root"), "root")

    def test_a_login_that_could_change_the_sudo_rule(self):
        self.assert_refused(self.run_host(login="a ALL=(ALL) NOPASSWD:ALL\nb"), "plain account name")

    def test_an_upload_without_a_key(self):
        os.unlink(os.path.join(self.up, "login.pub"))
        self.assert_refused(self.run_host(), "public key")


class SecondPart(Base):
    def test_sshd_checks_the_drop_in_before_it_reloads(self):
        self.good("second")
        self.assertEqual(read(self.host_path(DROP_IN)), read(os.path.join(ROOT, "host", DROP_IN)))
        self.assertLess(self.at(DROP_IN), self.at("sshd -t"))
        self.assertLess(self.at("sshd -t"), self.at("systemctl reload-or-restart ssh"))

    def test_the_firewall_opens_ssh_before_it_goes_on(self):
        self.good("second")
        self.assertLess(self.at("ufw allow 22/tcp"), self.at("ufw --force enable"))
        self.assertLess(self.at("ufw default deny incoming"), self.at("ufw --force enable"))
        for call in ("ufw default allow outgoing", "ufw default deny routed", "ufw logging low"):
            self.assertIn(call, self.calls())

    def test_a_drop_in_sshd_rejects_goes_away_and_the_firewall_stays_off(self):
        done = self.run_host("second", SSHD_RC="255")
        self.assertEqual(done.returncode, 1)
        self.assertFalse(os.path.exists(self.host_path(DROP_IN)))
        self.assertFalse(any(c.startswith("ufw") or "reload-or-restart" in c for c in self.calls()))

    def test_it_leaves_packages_and_the_account_alone(self):
        self.good("second")
        self.assertFalse(any(c.startswith(("apt-get", "useradd", "fallocate")) for c in self.calls()))


class Driver(Base):
    def setUp(self):
        super().setUp()
        write(os.path.join(self.bin, "ssh"), FAKE_SSH, stat.S_IRWXU)
        self.ssh_log = os.path.join(self.d, "ssh.log")
        self.copy = os.path.join(self.d, "upload-copy.tgz")
        self.key = write(os.path.join(self.d, "kunci.pub"), KEY + "\n")
        self.temp = os.path.join(self.d, "temp")
        os.mkdir(self.temp)
        self.env.update(SSH_LOG=self.ssh_log, UPLOAD_COPY=self.copy, BOOTSTRAP_KEY=self.key, TMPDIR=self.temp)

    def run_driver(self, first="ubuntu", target="pemilik@alamat", **env):
        return subprocess.run(["bash", os.path.join(ROOT, "scripts", "bootstrap.sh"), first, target], env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=60)

    def logged(self):
        return read(self.ssh_log).splitlines() if os.path.exists(self.ssh_log) else []

    def test_the_order_and_who_logs_in(self):
        done = self.run_driver()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        steps = [line for line in self.logged() if line != "with-sudo"]
        self.assertEqual([line.split()[:2] for line in steps], [["first", "ubuntu@alamat"], ["proof", "pemilik@alamat"],
                                                                ["second", "pemilik@alamat"], ["proof", "pemilik@alamat"]])
        self.assertIn("make preflight", done.stdout)
        self.assertTrue(os.path.isdir(self.host_path("opt/personal-agent")))
        self.assertTrue(os.path.exists(self.host_path(DROP_IN)))

    def test_only_the_first_login_may_ask_for_a_password(self):
        self.assertEqual(self.run_driver().returncode, 0)
        steps = [line for line in self.logged() if line != "with-sudo"]
        self.assertNotIn("BatchMode", steps[0])
        for line in steps[1:]:
            self.assertIn("BatchMode=yes", line)
        for line in steps:
            self.assertIn("StrictHostKeyChecking=accept-new", line)

    def test_root_needs_no_sudo_and_another_account_does(self):
        self.assertEqual(self.run_driver(first="root").returncode, 0)
        self.assertEqual(self.logged()[1].split()[0], "proof")   # the root login's line is not followed by with-sudo
        os.unlink(self.ssh_log)
        self.assertEqual(self.run_driver(first="ubuntu").returncode, 0)
        self.assertEqual(self.logged()[1], "with-sudo")

    def test_no_proof_no_hardening(self):
        done = self.run_driver(PROOF_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.assertIn("doors are still open", done.stderr)
        self.assertFalse(any(line.startswith("second") for line in self.logged()))
        self.assertFalse(os.path.exists(self.host_path(DROP_IN)))
        self.assertFalse(any(c.startswith("ufw") for c in self.calls()))

    def test_a_failed_first_part_says_how_to_log_in_again(self):
        done = self.run_driver(first="root", SSH_REFUSE="first")
        self.assertEqual(done.returncode, 1)
        self.assertIn("BOOTSTRAP_USER=pemilik", done.stderr)
        self.assertFalse(any(line.startswith("proof") for line in self.logged()))

    def test_the_upload_holds_the_recipe_and_only_the_public_key(self):
        self.assertEqual(self.run_driver().returncode, 0)
        with tarfile.open(self.copy) as tar:
            names = [m.name for m in tar.getmembers() if m.isfile()]
            self.assertEqual(tar.extractfile("login.pub").read().decode().strip(), KEY)
        self.assertIn("scripts/bootstrap-host.sh", names)
        self.assertIn("config/host-packages.txt", names)
        self.assertIn(SUDOERS.replace("etc/", "host/etc/", 1), names)
        for name in names:
            self.assertTrue(name in ("login.pub", "scripts/bootstrap-host.sh", "config/host-packages.txt") or name.startswith("host/etc/"), name)

    def test_nothing_stays_behind_in_a_temp_folder(self):
        self.assertEqual(self.run_driver().returncode, 0)
        self.assertEqual(os.listdir(self.temp), [])

    def test_a_private_key_or_a_missing_one_never_leaves(self):
        private = write(os.path.join(self.d, "rahasia"), "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n")
        renamed = write(os.path.join(self.d, "rahasia.pub"), read(private))
        empty = write(os.path.join(self.d, "kosong.pub"), "")
        for key in (private, renamed, empty, os.path.join(self.d, "tidak-ada.pub")):
            with self.subTest(key=os.path.basename(key)):
                done = self.run_driver(BOOTSTRAP_KEY=key)
                self.assertEqual(done.returncode, 2)
                self.assertIn("not one public key", done.stderr)
                self.assertEqual(self.logged(), [])

    def test_no_first_login_given(self):
        done = self.run_driver(first="")
        self.assertEqual(done.returncode, 2)
        self.assertIn("BOOTSTRAP_USER=", done.stderr)
        self.assertEqual(self.logged(), [])


PREFLIGHT_FAKES = {
    "curl": ('url="${@: -1}"\nhost=${url#https://}\nhost=${host%%/*}\n'
             'code=$(awk -v h="$host" \'$1 == h {print $2}\' "$CURL_CODES")\nprintf \'%s\' "${code:-200}"\n'
             '[ "${code:-200}" != 000 ]\n'),
    "df": 'printf \'Avail\\n %sG\\n\' "${DISK_GB:-78}"\n',
    "docker": ('case "$1" in\n  --version) echo "Docker version 29.9.2" ;;\n'
               '  compose) [ -z "${NO_COMPOSE:-}" ] || exit 1; echo "Docker Compose version v5.6.1" ;;\n'
               '  info) echo "${DOCKER_INFO:-overlayfs 2 json-file}" ;;\nesac\n'),
    "dpkg": 'echo "${ARCH:-amd64}"\n',
    "free": 'printf \'  total\\nMem: %s 1 1\\nSwap: %s 1 1\\n\' "${MEM_MB:-7623}" "${SWAP_MB:-5983}"\n',
    "nproc": 'cat > /dev/null\necho "${CPUS:-2}"\n',   # eats stdin: over ssh that would be the rest of the script
    "python3": 'exit "${PYTHON_RC:-0}"\n',
    "restic": 'echo "restic 0.16.4"\nexit "${RESTIC_RC:-0}"\n',
    "rsync": 'echo "rsync version 3.2.7"\n',
    "ss": 'echo "LISTEN 0 4096 port:22"\n',
    "sshd": 'printf \'permitrootlogin %s\\nport 22\\npasswordauthentication %s\\n\' "${ROOT_LOGIN:-no}" "${PASSWORDS:-no}"\n',
    "sudo": '[ -z "${SUDO_FAIL:-}" ] || exit 1\n[ "$1" != -n ] || shift\nexec "$@"\n',
    "systemd-detect-virt": ('if [ "${1:-}" = --container ]; then echo "${CONTAINER:-none}"; [ -n "${CONTAINER:-}" ]; else echo kvm; fi\n'),
    "timedatectl": 'case "$*" in\n  *Timezone*) echo "${ZONE:-Asia/Jakarta}" ;;\n  *) echo yes ;;\nesac\n',
    "top": 'echo "%Cpu(s): 0.1 st"\n',
    "ufw": 'printf \'Status: %s\\n\\n%s  ALLOW IN  Anywhere\\n\' "${UFW:-active}" "${SSH_RULE:-22/tcp}"\n',
}


class Preflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = self.tmp.name
        self.bin = os.path.join(d, "bin")
        for name, body in PREFLIGHT_FAKES.items():
            write(os.path.join(self.bin, name), "#!/bin/bash\n" + body, stat.S_IRWXU)
        self.codes = write(os.path.join(d, "codes"), "")
        self.release = write(os.path.join(d, "os-release"), 'ID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04.4 LTS"\n')
        self.env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], CURL_CODES=self.codes, PREFLIGHT_OS_RELEASE=self.release)

    def run_check(self, **env):
        with open(os.path.join(ROOT, "scripts", "preflight.sh"), encoding="utf-8") as script:   # as make preflight does: bash -s over ssh
            return subprocess.run(["bash", "-s"], stdin=script, env=dict(self.env, **env), capture_output=True, text=True, timeout=60)

    def assert_fails(self, label, **env):
        done = self.run_check(**env)
        self.assertEqual(done.returncode, 1, done.stdout)
        failing = [line for line in done.stdout.splitlines() if line.startswith("FAIL")]
        self.assertEqual(len(failing), 1, done.stdout)
        self.assertIn(f"FAIL  {label}", failing[0])
        self.assertIn("preflight: 1 failed", done.stdout)

    def test_a_good_host_passes_and_the_whole_script_ran(self):
        done = self.run_check()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertNotIn("FAIL", done.stdout)
        self.assertIn("preflight: all checks passed", done.stdout)
        self.assertIn("note  cpu steal", done.stdout)

    def test_each_requirement_can_fail_alone(self):
        for label, env in (("machine", {"CONTAINER": "lxc"}), ("architecture", {"ARCH": "arm64"}), ("cpus", {"CPUS": "1"}),
                           ("memory", {"MEM_MB": "3900"}), ("swap", {"SWAP_MB": "0"}), ("free disk", {"DISK_GB": "12"}),
                           ("compose", {"NO_COMPOSE": "1"}), ("docker setup", {"DOCKER_INFO": "overlay2 1 json-file"}),
                           ("docker setup", {"DOCKER_INFO": "overlayfs 2 local"}), ("python", {"PYTHON_RC": "1"}),
                           ("restic", {"RESTIC_RC": "1"}), ("ssh", {"ROOT_LOGIN": "yes"}), ("ssh", {"PASSWORDS": "yes"}),
                           ("firewall:", {"UFW": "inactive"}), ("firewall port", {"SSH_RULE": "80/tcp"}),
                           ("time zone", {"ZONE": "Asia/Shanghai"})):
            with self.subTest(label=label, env=env):
                self.assert_fails(label, **env)

    def test_another_system(self):
        write(self.release, 'ID=ubuntu\nVERSION_ID="22.04"\nPRETTY_NAME="Ubuntu 22.04"\n')
        self.assert_fails("os")

    def test_without_sudo_everything_behind_it_fails_and_the_exit_says_so(self):
        done = self.run_check(SUDO_FAIL="1")
        self.assertEqual(done.returncode, 1)
        for label in ("sudo", "docker", "compose", "ssh", "firewall"):
            self.assertIn(f"FAIL  {label}", done.stdout)

    def test_no_way_out_fails(self):
        for host in ("api.telegram.org", "registry-1.docker.io", "pypi.org", "download.docker.com", "oauth2.googleapis.com"):
            with self.subTest(host=host):
                write(self.codes, f"{host} 000\n")
                self.assert_fails("reach", )

    def test_any_answer_shows_the_way_is_open(self):
        write(self.codes, "api.anthropic.com 405\napi.telegram.org 302\napi.notion.com 401\ngmail.googleapis.com 404\n"
                          "production.cloudflare.docker.com 403\n")
        self.assertEqual(self.run_check().returncode, 0)

    def test_anthropic_refusing_this_region_fails(self):
        for code in ("403", "451", "000"):
            with self.subTest(code=code):
                write(self.codes, f"api.anthropic.com {code}\n")
                self.assert_fails("reach")


class Target(unittest.TestCase):
    def test_make_passes_the_first_login_and_the_account(self):
        done = subprocess.run(["make", "-n", "--no-print-directory", "-C", ROOT, "bootstrap", "BOOTSTRAP_USER=awal", "VPS_HOST=alamat",
                               "VPS_USER=pemilik"], capture_output=True, text=True, timeout=30, check=True)
        self.assertEqual(done.stdout.strip(), 'bash scripts/bootstrap.sh "awal" pemilik@alamat')


class Sudoers(unittest.TestCase):
    def test_the_template_is_one_rule_for_the_login(self):
        rules = [line for line in read(os.path.join(ROOT, "host", SUDOERS)).splitlines() if not line.startswith("#")]
        self.assertEqual(rules, ["@LOGIN@ ALL=(ALL) NOPASSWD:ALL"])


if __name__ == "__main__":
    unittest.main()
