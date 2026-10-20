#!/usr/bin/env bash
set -euo pipefail
skill_repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if ! git -C "$skill_repo_dir" rev-parse --verify HEAD >/dev/null 2>&1; then
  echo '当前目录不是已克隆的版本仓库。请由Agent使用具备该私有仓库权限的Git登录，将仓库克隆到固定目录，再运行install.sh。' >&2
  exit 1
fi
skill_repo_top="$(git -C "$skill_repo_dir" rev-parse --show-toplevel)"
if [[ "$skill_repo_top" != "$skill_repo_dir" ]]; then echo '仓库根目录不一致，停止更新。' >&2; exit 1; fi
skill_origin="$(git -C "$skill_repo_dir" remote get-url origin)"
case "$skill_origin" in
  https://github.com/WayneArchi/wenyu-koubo-jianying|https://github.com/WayneArchi/wenyu-koubo-jianying.git|git@github.com:WayneArchi/wenyu-koubo-jianying.git) ;;
  *) echo '远端不是本Skill仓库，停止更新。' >&2; exit 1 ;;
esac
if [[ "$(git -C "$skill_repo_dir" symbolic-ref --quiet --short HEAD)" != main ]]; then echo '当前不是main分支，停止自动更新。' >&2; exit 1; fi
if [[ -n "$(git -C "$skill_repo_dir" status --porcelain --untracked-files=all)" ]]; then echo '有本地修改或未跟踪文件，已保留；请先由Agent检查，不自动覆盖。' >&2; exit 1; fi
GIT_TERMINAL_PROMPT=0 git -C "$skill_repo_dir" pull --ff-only origin main
bash "$skill_repo_dir/install.sh"
