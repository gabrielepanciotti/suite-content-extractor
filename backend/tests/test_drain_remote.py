"""The drain fetches the boxes of other devices (ContentExtractor#1).

`ssh` is replaced by a stub that runs the remote command locally, and
`scripts/ingest.sh` by one that records its arguments: what is under test is the
handover — nothing lost, nothing read twice, every line stamped with its instance.
"""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _node(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    node = tmp_path / "node"
    (node / "scripts").mkdir(parents=True)
    (node / ".learn-queue").mkdir()
    shutil.copy(ROOT / "scripts" / "drain-inbox.sh", node / "scripts" / "drain-inbox.sh")
    ingest = node / "scripts" / "ingest.sh"
    ingest.write_text(
        '#!/usr/bin/env bash\nout="$(dirname "$0")/../calls.txt"\n'
        'printf "%s|" "$@" >> "$out"; echo >> "$out"\n'
    )
    ingest.chmod(0o755)
    remote = tmp_path / "minipc" / ".learn-queue"
    remote.mkdir(parents=True)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    ssh = bindir / "ssh"
    # Skip options and host, run the last argument as the remote command.
    ssh.write_text('#!/usr/bin/env bash\nfor a; do cmd="$a"; done\nexec sh -c "$cmd"\n')
    ssh.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "INGEST_REMOTE_BOXES": f"personal,remote-host,{remote}/da-ingerire.txt,personal instance",
    }
    return node, remote, env


def _drain(node: Path, env: dict[str, str]) -> None:
    subprocess.run(["bash", "scripts/drain-inbox.sh"], cwd=node, env=env, check=True)


def test_remote_links_are_ingested_with_their_instance(tmp_path: Path) -> None:
    node, remote, env = _node(tmp_path)
    (remote / "da-ingerire.txt").write_text(
        "ingest\thttps://x.com/a\t--node\tcontentExtractor\t--entita\twork instance\n"
    )
    _drain(node, env)
    calls = (node / "calls.txt").read_text().splitlines()
    # argparse keeps the last value: the instance's entita wins over the group's.
    assert calls == [
        "ingest|https://x.com/a|--node|contentExtractor|--entita|work instance"
        "|--instance|personal|--entita|personal instance|"
    ]
    assert (remote / "da-ingerire.txt").read_text() == ""
    assert not (remote / "da-ingerire.txt.transito").exists()


def test_a_box_left_in_transit_is_read_again(tmp_path: Path) -> None:
    node, remote, env = _node(tmp_path)
    (remote / "da-ingerire.txt.transito").write_text("ingest\thttps://x.com/b\n")
    _drain(node, env)
    assert (node / "calls.txt").read_text().startswith(
        "ingest|https://x.com/b|--instance|personal|"
    )


def test_unreachable_host_leaves_local_drain_working(tmp_path: Path) -> None:
    node, _remote, env = _node(tmp_path)
    (Path(env["PATH"].split(":")[0]) / "ssh").write_text("#!/usr/bin/env bash\nexit 255\n")
    (node / ".learn-queue" / "da-ingerire.txt").write_text("ingest\thttps://x.com/c\n")
    _drain(node, env)
    assert (node / "calls.txt").read_text() == "ingest|https://x.com/c|\n"
    assert "non raggiungibile" in (node / ".learn-queue" / "drain.log").read_text()
