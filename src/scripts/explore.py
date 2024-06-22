from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

import rich_click as click
from git import Repo
from git.remote import RemoteProgress
from rich.console import Console
from rich.progress import BarColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskProgressColumn
from rich.progress import TextColumn

# git clone --depth 1 URL TEMPDIR
# nvim TEMPDIR
# rm -rf TEMPDIR


@click.command()
@click.argument("repo", type=str)
@click.option("--depth", "-d", default=1, type=int)
def command(repo: str, depth: int | None) -> None:
    url = parse_repo_url(repo)
    with tempfile.TemporaryDirectory() as tmpdirname:
        if depth == 0:
            depth = None
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=Console(),
        ) as progress:
            clone_task = progress.add_task("Cloning...", total=None)
            Repo().clone_from(
                url,
                tmpdirname,
                depth=depth,
                progress=CloneProgress(progress, clone_task),
            )
        editor = shutil.which("nvim")
        nvim_config = os.path.expanduser("~/.config/nvim/init.lua")
        subprocess.run([editor, "-u", nvim_config, tmpdirname])
    # https://github.com/ajeetdsouza/zoxide
    # https://github.com/ajeetdsouza/zoxide.git
    # gh:ajeetdsouza/zoxide
    # ajeetdsouza/zoxide
    # https://github.com/ajeetdsouza/zoxide/tree/warp (branch)


def parse_repo_url(url: str) -> str:
    # GitHub shorthand (user/repo or gh:user/repo)
    if re.match(r"^(gh:)?[\w-]+/[\w.-]+$", url):
        user_repo = url.split(":")[-1]
        return f"https://github.com/{user_repo}"

    # Full GitHub URL
    if url.startswith(("http://", "https://")):
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        if len(path_parts) >= 2:
            user, repo = path_parts[:2]
            repo = repo.rstrip(".git")

            return f"https://{parsed.netloc}/{user}/{repo}"

    # If no match, return the original URL
    return url


class CloneProgress(RemoteProgress):
    def __init__(self, progress: Progress, task_id: int):
        super().__init__()
        self.progress = progress
        self.task_id = task_id

    def update(
        self,
        op_code: int,
        cur_count: str | float,
        max_count: str | float | None = None,
        message: str = "",
    ):
        # Determine the current stage
        stage = op_code & RemoteProgress.STAGE_MASK
        stage_name = self.get_stage_name(stage)

        # Update progress based on the current stage
        if op_code & RemoteProgress.BEGIN:
            self.progress.update(self.task_id, description=f"Starting {stage_name}")
        elif op_code & RemoteProgress.END:
            self.progress.update(self.task_id, description=f"Finished {stage_name}")
        else:
            self.progress.update(self.task_id, description=f"{stage_name} in progress")

        # Update progress count
        if max_count is not None:
            self.progress.update(self.task_id, total=max_count, completed=cur_count)
        elif cur_count is not None:
            self.progress.update(
                self.task_id,
                advance=cur_count - self.progress.tasks[self.task_id].completed,
            )

        # Print additional messages
        if message:
            self.progress.console.print(self._cur_line)

    def get_stage_name(self, stage: int) -> str:
        match stage:
            case RemoteProgress.COUNTING:
                return "Counting"
            case RemoteProgress.COMPRESSING:
                return "Compressing"
            case RemoteProgress.WRITING:
                return "Writing"
            case RemoteProgress.RECEIVING:
                return "Receiving"
            case RemoteProgress.RESOLVING:
                return "Resolving deltas"
            case _:
                return "Processing"
