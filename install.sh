#!/usr/bin/env bash
set -euo pipefail
skill_repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
bash "$skill_repo_dir/tools/dbs-install-skill/scripts/install-skill.sh" link "$skill_repo_dir/skills/wenyu-koubo-jianying"
bash "$skill_repo_dir/tools/dbs-install-skill/scripts/install-skill.sh" status "$skill_repo_dir/skills/wenyu-koubo-jianying"
